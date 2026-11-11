from decimal import Decimal

import pytest

from orcamento_pecas.dominio.alertas import CodigoAlerta
from orcamento_pecas.dominio.modelos import Fonte, ParametroEcoado
from orcamento_pecas.servicos.pecas import ServicoPecas
from orcamento_pecas.servicos.veiculos import ServicoVeiculos

FONTE = Fonte(banco="base_teste.db", sha256="0" * 64)
# Ordem: grupo, descrição normalizada ("+0,25" < "+0,50" < "STD"), código.
BRONZINAS_35368_ORDENADAS = [6810, 11838, 6811, 11839, 6809, 11837]


@pytest.fixture
def servico(repo) -> ServicoPecas:
    return ServicoPecas(repo, ServicoVeiculos(repo, FONTE), FONTE)


def alerta(resposta, codigo):
    return next(a for a in resposta.alertas if a.codigo == codigo)


def codigos(resposta) -> list[int]:
    return [p.codigo_produto for p in resposta.dados]


def test_pecas_da_aplicacao_sem_preco_geram_revisao(servico):
    r = servico.da_aplicacao(35368, grupo=39)
    assert codigos(r) == BRONZINAS_35368_ORDENADAS
    assert all(p.preco.normalizado is None and p.preco.original is None for p in r.dados)
    assert alerta(r, CodigoAlerta.PRECO_AUSENTE).contexto["codigos_produto"] == BRONZINAS_35368_ORDENADAS
    assert CodigoAlerta.PRECO_AUSENTE in r.revisao_humana.motivos
    assert r.total == 6


def test_possivel_duplicidade_nac_sinalizada_sem_mesclar(servico):
    r = servico.da_aplicacao(35368, grupo=39)
    assert len(r.dados) == 6
    duplicidade = alerta(r, CodigoAlerta.POSSIVEL_PRODUTO_DUPLICADO)
    assert duplicidade.contexto["grupos_duplicidade"] == [[6810, 11838], [6811, 11839], [6809, 11837]]
    numeros = {e.valor_original for e in duplicidade.evidencias}
    assert {"55.455.007", "#NAC_55.455.007"} <= numeros


def test_filtro_grupo_bronzina_exclui_guia_de_valvula_bronze(servico):
    assert 3118 in codigos(servico.da_aplicacao(35368))
    assert 3118 not in codigos(servico.da_aplicacao(35368, grupo=39))


@pytest.mark.parametrize(
    ("texto", "esperado"),
    # 3118 = "GUIA DE VALVULA TEMPRA 16V BRONZE STD" (grupo GUIAS DE VALVULA, depois de BRONZINA)
    [("std", [6809, 11837, 3118]), ("mancal +0,25", [6810, 11838]), ("bronz", []), ("bronze", [3118])],
)
def test_filtro_por_texto_usa_palavras_inteiras(servico, texto, esperado):
    assert codigos(servico.da_aplicacao(35368, texto=texto)) == esperado


def test_da_aplicacao_inexistente(servico):
    assert servico.da_aplicacao(999999) is None


def test_produto_com_preco_e_grupo_rastreados(servico):
    r = servico.da_aplicacao(15365)
    assert codigos(r) == [5581, 5580]
    produto = r.dados[0]
    assert produto.preco.normalizado == Decimal("11.1")
    assert produto.grupo.normalizado == "GUIAS DE VALVULA"
    assert produto.grupo.evidencia.model_dump() == {
        "tabela": "GRUPOPRODUTO", "chave": {"CodigoGrupoProduto": 7}, "coluna": "DescricaoGrupoProduto", "valor_original": "GUIAS DE VÁLVULA",
    }
    assert produto.codigos_aplicacao == [15365]
    assert CodigoAlerta.PRECO_AUSENTE not in {a.codigo for a in r.alertas}


def test_por_veiculo_sem_chave_motor_com_varios_motores_exige_revisao(servico):
    r = servico.por_veiculo("frontier", 2008, grupo=39)
    assert codigos(r) == [6656, 11758] + BRONZINAS_35368_ORDENADAS
    motor = alerta(r, CodigoAlerta.MOTOR_NAO_IDENTIFICADO)
    assert motor.severidade == "revisao"
    assert len(motor.contexto["chaves_candidatas"]) == 6
    assert r.revisao_humana.necessaria is True
    assert next(p for p in r.dados if p.codigo_produto == 6809).codigos_aplicacao == [35368, 35369]


def test_por_veiculo_com_chave_motor_restringe_aplicacoes(servico):
    r = servico.por_veiculo("frontier", 2008, chave_motor="YD25ETI|2.5|16V|L4|DOHC", grupo=39)
    assert codigos(r) == BRONZINAS_35368_ORDENADAS
    assert CodigoAlerta.MOTOR_NAO_IDENTIFICADO not in {a.codigo for a in r.alertas}
    assert r.consulta["chave_motor"] == ParametroEcoado(original="YD25ETI|2.5|16V|L4|DOHC", normalizado="YD25ETI|2.5|16V|L4|DOHC")
    assert r.consulta["grupo"] == ParametroEcoado(original=39, normalizado=39)


def test_por_veiculo_traz_alertas_das_aplicacoes(servico):
    r = servico.por_veiculo("frontier", 2008)
    assert CodigoAlerta.ANO_FIM_AUSENTE in {a.codigo for a in r.alertas}


def test_por_veiculo_chave_motor_inexistente(servico):
    r = servico.por_veiculo("frontier", 2008, chave_motor="X")
    assert r.dados == [] and r.total == 0
    assert CodigoAlerta.MOTOR_NAO_ENCONTRADO in {a.codigo for a in r.alertas}


def test_paginacao_deterministica(servico):
    r = servico.por_veiculo("frontier", 2008, grupo=39, pagina=2, limite=3)
    assert r.total == 8
    assert codigos(r) == [11838, 6811, 11839]
    assert [6656, 11758] in alerta(r, CodigoAlerta.POSSIVEL_PRODUTO_DUPLICADO).contexto["grupos_duplicidade"]


def test_detalhe_lista_vinculos_orfaos_e_campos_nao_interpretados(servico):
    r = servico.obter(1946)
    assert r.dados.codigos_aplicacao == []
    assert r.dados.vinculos_orfaos == [15098]
    orfao = alerta(r, CodigoAlerta.VINCULO_ORFAO)
    assert orfao.evidencias[0].model_dump() == {
        "tabela": "PRODUTO_APLICACAO", "chave": {"CodigoProduto": 1946, "CodigoAplicacao": 15098},
        "coluna": "CodigoAplicacao", "valor_original": 15098,
    }
    assert set(r.dados.campos_nao_interpretados) == {"CodigoSimilar", "CpoAuxProd5", "CpoAuxProd25", "PCs", "NumeroProdutoPesq"}


def test_detalhe_traz_todas_as_aplicacoes_existentes(servico):
    assert servico.obter(6809).dados.codigos_aplicacao == [35368, 35369, 35374]
    assert servico.obter(999999) is None


def test_qtd_embalagem_ausente_gera_dado_ausente(servico):
    r = servico.obter(6238)
    assert r.dados.qtd_embalagem.normalizado is None
    ausente = alerta(r, CodigoAlerta.DADO_AUSENTE)
    assert any(e.coluna == "QtdEmbalagem" for e in ausente.evidencias)


# --- regressões da revisão final -------------------------------------------------------


def test_por_veiculo_com_combustivel_mantem_conflito(servico):
    """C1: o filtro de combustível não esconde o conflito do motor."""
    r = servico.por_veiculo("kicks", 2018, combustivel="gasolina")
    assert CodigoAlerta.COMBUSTIVEL_CONFLITANTE in r.revisao_humana.motivos


def test_pecas_nao_encontradas_exigem_revisao(servico):
    """I1: veículo encontrado, mas nenhuma peça com os filtros: alerta com as aplicações consultadas."""
    r = servico.por_veiculo("sentra", 2015, grupo=39)
    assert r.total == 0
    vazio = alerta(r, CodigoAlerta.PECAS_NAO_ENCONTRADAS)
    assert vazio.contexto["codigos_aplicacao"] == [34568, 34569]
    assert vazio.contexto["grupo"] == 39
    assert r.revisao_humana.necessaria is True


def test_aplicacao_sem_pecas_exige_revisao(servico):
    r = servico.da_aplicacao(34568)
    assert r.dados == []
    assert alerta(r, CodigoAlerta.PECAS_NAO_ENCONTRADAS).contexto["codigos_aplicacao"] == [34568]


def test_preco_zerado_ou_negativo_e_suspeito(criar_banco):
    """I3: preço ≤ 0 não é preço válido: alerta de revisão, sem PRECO_AUSENTE."""
    from orcamento_pecas.dados.conexao import abrir_somente_leitura
    from orcamento_pecas.dados.repositorio import Repositorio

    banco = criar_banco(
        "UPDATE PRODUTO SET PrecoProduto = 0 WHERE CodigoProduto = 5580;"
        "UPDATE PRODUTO SET PrecoProduto = -1.5 WHERE CodigoProduto = 5581;"
    )
    conexao = abrir_somente_leitura(banco)
    try:
        repo = Repositorio(conexao)
        r = ServicoPecas(repo, ServicoVeiculos(repo, FONTE), FONTE).da_aplicacao(15365)
    finally:
        conexao.close()
    suspeito = alerta(r, CodigoAlerta.PRECO_SUSPEITO)
    assert {(e.chave["CodigoProduto"], e.valor_original) for e in suspeito.evidencias} == {(5580, 0.0), (5581, -1.5)}
    assert CodigoAlerta.PRECO_AUSENTE not in {a.codigo for a in r.alertas}
    assert CodigoAlerta.PRECO_SUSPEITO in r.revisao_humana.motivos
