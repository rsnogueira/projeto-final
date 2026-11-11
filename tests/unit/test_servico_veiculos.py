import pytest

from orcamento_pecas.dominio.alertas import CodigoAlerta
from orcamento_pecas.dominio.modelos import Fonte, ParametroEcoado
from orcamento_pecas.servicos.veiculos import ServicoVeiculos

FONTE = Fonte(banco="base_teste.db", sha256="0" * 64)
CHAVES_FRONTIER_2008 = {
    "4.07 TCE SPRINT|2.8|12V|L4|SOHC",
    "SPRINT EURO 3|2.8|12V|L4|SOHC",
    "YD25ETI|2.5|16V|L4|DOHC",
    "YD25 SELL|2.5|16V|?|?",
    "YD25DDTI+YD25ETI|2.5|16V|L4|DOHC",
    "M9T|2.3|16V|L4|DOHC",
}


@pytest.fixture
def servico(repo) -> ServicoVeiculos:
    return ServicoVeiculos(repo, FONTE)


def codigos_alerta(resposta) -> set[CodigoAlerta]:
    return {a.codigo for a in resposta.alertas}


def alerta(resposta, codigo):
    return next(a for a in resposta.alertas if a.codigo == codigo)


# --- motorizações (endpoint obrigatório) -----------------------------------------------


def test_frontier_2008_nao_identificado_com_atributos_distintivos(servico):
    r = servico.motorizacoes("frontier", 2008)
    assert len(r.dados.aplicacoes) == 14
    assert r.dados.identificado is False
    assert r.dados.motor_identificado is None
    assert {c.chave_motor for c in r.dados.candidatos} == CHAVES_FRONTIER_2008
    assert r.total == 6
    assert r.dados.atributos_distintivos["cilindrada_l"] == ["2.3", "2.5", "2.8"]
    assert "combustivel" not in r.dados.atributos_distintivos  # todos DIESEL
    assert {CodigoAlerta.MOTOR_NAO_IDENTIFICADO, CodigoAlerta.ANO_FIM_AUSENTE, CodigoAlerta.MOTORIZACAO_COMPOSTA} <= codigos_alerta(r)
    assert r.revisao_humana.necessaria is True


def test_candidato_agrupa_aplicacoes_do_mesmo_motor(servico):
    r = servico.motorizacoes("frontier", 2008)
    yd25eti = next(c for c in r.dados.candidatos if c.chave_motor == "YD25ETI|2.5|16V|L4|DOHC")
    assert yd25eti.codigos_aplicacao == [13823, 13824, 13979, 35368, 35369]
    assert {v.original for v in yd25eti.motorizacoes_originais} == {"YD25ETI 2.5 16V L4 DOHC", "YD25ETI 2.5 L 16V DOHC L4"}
    assert yd25eti.combustiveis == ["DIESEL"]


def test_ano_na_borda_da_faixa_e_compativel(servico):
    codigos = {a.codigo_aplicacao for a in servico.motorizacoes("frontier", 2008).dados.aplicacoes}
    assert {13760, 13823} <= codigos  # 2006-2008 e 2008-2013
    assert 36312 not in codigos       # 2012-...


def test_faixa_aberta_entra_com_alerta_ano_fim_ausente_e_revisao(servico):
    r = servico.motorizacoes("frontier", 2008)
    aplicacao = next(a for a in r.dados.aplicacoes if a.codigo_aplicacao == 31393)
    assert aplicacao.ano_fim.original == ""
    assert aplicacao.ano_fim.normalizado is None
    evidencias = alerta(r, CodigoAlerta.ANO_FIM_AUSENTE).evidencias
    assert any(e.chave == {"CodigoAplicacao": 31393} and e.coluna == "AnoFimFabricacao" for e in evidencias)
    assert CodigoAlerta.ANO_FIM_AUSENTE in r.revisao_humana.motivos


def test_filtro_por_combustivel(servico):
    gasolina = servico.motorizacoes("kicks", 2018, combustivel="gasolina")
    flex = servico.motorizacoes("kicks", 2018, combustivel="Flex")
    assert [a.codigo_aplicacao for a in gasolina.dados.aplicacoes] == [15365, 15366]
    assert [a.codigo_aplicacao for a in flex.dados.aplicacoes] == [31383, 31483, 32111]


def test_combustivel_sem_aplicacao_lista_disponiveis(servico):
    r = servico.motorizacoes("frontier", 2008, combustivel="gasolina")
    assert r.dados.aplicacoes == []
    assert alerta(r, CodigoAlerta.COMBUSTIVEL_NAO_ENCONTRADO).contexto["combustiveis_disponiveis"] == ["DIESEL"]


def test_motor_unico_identificado(servico):
    r = servico.motorizacoes("sentra", 2015)
    assert r.dados.identificado is True
    assert r.dados.motor_identificado.chave_motor == "CVVTCS|2.0|16V|L4|DOHC"
    assert r.dados.motor_identificado.codigos_aplicacao == [34568, 34569]
    assert r.dados.atributos_distintivos == {}
    assert CodigoAlerta.MOTOR_NAO_IDENTIFICADO not in codigos_alerta(r)
    assert r.revisao_humana.necessaria is False


def test_motor_unico_com_conflito_de_combustivel_exige_revisao(servico):
    r = servico.motorizacoes("kicks", 2018)
    assert r.dados.identificado is True
    assert r.dados.motor_identificado.combustiveis == ["FLEX", "GASOLINA"]
    assert CodigoAlerta.COMBUSTIVEL_CONFLITANTE in r.revisao_humana.motivos


def test_modelo_inexistente_lista_modelos_disponiveis(servico):
    r = servico.motorizacoes("xyz", 2008)
    assert r.dados.aplicacoes == [] and r.dados.candidatos == []
    assert r.dados.identificado is False
    assert alerta(r, CodigoAlerta.MODELO_NAO_ENCONTRADO).contexto["modelos_disponiveis"] == [
        "FRONTIER", "KICKS", "LIVINA", "MARCH", "PATHFINDER", "SENTRA", "VERSA",
    ]
    assert CodigoAlerta.MOTOR_NAO_IDENTIFICADO not in codigos_alerta(r)


def test_ano_fora_lista_faixas(servico):
    r = servico.motorizacoes("sentra", 2010)
    assert r.dados.aplicacoes == []
    assert alerta(r, CodigoAlerta.ANO_FORA_DO_INTERVALO).contexto["faixas_disponiveis"] == ["2013-2016", "2014-2016"]


def test_fabricante_sem_veiculos(servico):
    r = servico.motorizacoes("uno", 2010, fabricante="fiat")
    assert codigos_alerta(r) == {CodigoAlerta.FABRICANTE_SEM_VEICULOS}
    assert r.dados.aplicacoes == []


def test_fabricante_inexistente(servico):
    r = servico.motorizacoes("frontier", 2008, fabricante="xpto")
    assert alerta(r, CodigoAlerta.FABRICANTE_NAO_ENCONTRADO).contexto["fabricantes_disponiveis"] == ["FIAT", "FORD", "NISSAN"]
    assert r.dados.aplicacoes == []


def test_fabricante_existente_filtra(servico):
    assert len(servico.motorizacoes("frontier", 2008, fabricante="Nissan").dados.aplicacoes) == 14


def test_descricao_composta_e_correspondencia_parcial(servico):
    pathfinder = servico.motorizacoes("pathfinder", 2008)
    assert [a.codigo_aplicacao for a in pathfinder.dados.aplicacoes] == [32415, 36311]
    assert CodigoAlerta.DESCRICAO_COMPOSTA in codigos_alerta(pathfinder)
    parcial = servico.motorizacoes("SE", 2008)
    assert all(a.correspondencia.confianca == "baixa" for a in parcial.dados.aplicacoes)
    assert CodigoAlerta.CORRESPONDENCIA_PARCIAL_MODELO in codigos_alerta(parcial)


def test_motor_sem_codigo_e_faixa_divergente(servico):
    r = servico.motorizacoes("livina", 2014)
    assert [a.codigo_aplicacao for a in r.dados.aplicacoes] == [32452]
    assert {CodigoAlerta.MOTORIZACAO_SEM_CODIGO, CodigoAlerta.FAIXA_ANO_DIVERGENTE} <= codigos_alerta(r)


def test_alertas_consolidados_por_codigo(servico):
    r = servico.motorizacoes("frontier", 2008)
    assert len([a for a in r.alertas if a.codigo == CodigoAlerta.MOTORIZACAO_COMPOSTA]) == 1


def test_consulta_ecoada_e_fonte(servico):
    r = servico.motorizacoes("frontier ", 2008, combustivel="diesel")
    assert r.consulta["modelo"] == ParametroEcoado(original="frontier ", normalizado="FRONTIER")
    assert r.consulta["ano"] == ParametroEcoado(original=2008, normalizado=2008)
    assert r.consulta["combustivel"] == ParametroEcoado(original="diesel", normalizado="DIESEL")
    assert r.consulta["fabricante"] == ParametroEcoado(original=None, normalizado=None)
    assert r.fonte == FONTE


def test_evidencias_da_aplicacao(servico):
    aplicacao = servico.obter(35368).dados
    assert aplicacao.fabricante.evidencia.model_dump() == {
        "tabela": "FABRICANTE", "chave": {"CodigoFabricante": 73}, "coluna": "DescricaoFabricante", "valor_original": "NISSAN",
    }
    assert aplicacao.tipo_aplicacao.normalizado == "UTILITARIOS"
    assert aplicacao.motorizacao.normalizado.chave == "YD25ETI|2.5|16V|L4|DOHC"
    assert aplicacao.motorizacao.evidencia.chave == {"CodigoAplicacao": 35368}
    assert aplicacao.faixa_ano.normalizado.model_dump() == {"inicio": 2007, "fim": 2012, "interpretada": True}


def test_obter_inexistente(servico):
    assert servico.obter(999999) is None


# --- combustíveis (endpoint obrigatório) -----------------------------------------------


def test_kicks_2018_conflito_de_combustivel(servico):
    r = servico.combustiveis("kicks", 2018)
    assert r.dados.unico is False
    assert [(c.combustivel, c.codigos_aplicacao) for c in r.dados.combustiveis] == [
        ("FLEX", [31383, 31483, 32111]),
        ("GASOLINA", [15365, 15366]),
    ]
    assert r.total == 2
    assert alerta(r, CodigoAlerta.COMBUSTIVEL_CONFLITANTE).contexto["chaves_motor"] == ["HR16DE|1.6|16V|L4|DOHC"]
    assert CodigoAlerta.MULTIPLOS_COMBUSTIVEIS in codigos_alerta(r)


def test_frontier_2008_combustivel_unico(servico):
    r = servico.combustiveis("frontier", 2008)
    assert r.dados.unico is True
    assert [c.combustivel for c in r.dados.combustiveis] == ["DIESEL"]
    assert len(r.dados.combustiveis[0].valores) == 14


def test_combustiveis_modelo_inexistente(servico):
    r = servico.combustiveis("xyz", 2018)
    assert r.dados.combustiveis == [] and r.dados.unico is False
    assert CodigoAlerta.MODELO_NAO_ENCONTRADO in codigos_alerta(r)


# --- busca geral -----------------------------------------------------------------------


def test_buscar_sem_filtros(servico):
    r = servico.buscar()
    assert r.total == 27
    assert len(r.dados) == 27


def test_buscar_paginacao_deterministica(servico):
    r = servico.buscar(modelo="frontier", pagina=2, limite=5)
    assert r.total == 17
    assert (r.pagina, r.limite) == (2, 5)
    assert [a.codigo_aplicacao for a in r.dados] == [13823, 13824, 13979, 31393, 32415]


# --- regressões da revisão final -------------------------------------------------------


def test_filtro_de_combustivel_nao_esconde_conflito(servico):
    """C1: o combustível informado não pode resolver em silêncio o conflito FLEX × GASOLINA do mesmo motor."""
    r = servico.motorizacoes("kicks", 2018, combustivel="gasolina")
    assert r.dados.identificado is True
    conflito = alerta(r, CodigoAlerta.COMBUSTIVEL_CONFLITANTE)
    assert any(e.chave == {"CodigoAplicacao": 31383} and e.valor_original == "FLEX" for e in conflito.evidencias)
    assert CodigoAlerta.COMBUSTIVEL_CONFLITANTE in r.revisao_humana.motivos


def test_correspondencia_parcial_exige_revisao(servico):
    """I2: baixa confiança exige revisão humana (CLAUDE.md)."""
    r = servico.motorizacoes("SE", 2008)
    assert CodigoAlerta.CORRESPONDENCIA_PARCIAL_MODELO in r.revisao_humana.motivos
