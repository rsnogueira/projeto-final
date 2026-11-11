import pytest

from orcamento_pecas.auditoria.verificacoes import auditar_base, auditar_resposta
from orcamento_pecas.dados.conexao import abrir_somente_leitura
from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.alertas import CodigoAlerta
from orcamento_pecas.dominio.modelos import Evidencia, Fonte
from orcamento_pecas.servicos.pecas import ServicoPecas
from orcamento_pecas.servicos.veiculos import ServicoVeiculos

FONTE = Fonte(banco="base_teste.db", sha256="0" * 64)


@pytest.fixture
def veiculos(repo):
    return ServicoVeiculos(repo, FONTE)


@pytest.fixture
def pecas(repo, veiculos):
    return ServicoPecas(repo, veiculos, FONTE)


def invariantes(falhas) -> set[str]:
    return {f.invariante for f in falhas}


def test_auditoria_base_detecta_anomalias_semeadas(criar_banco):
    banco = criar_banco("INSERT INTO APLICACAO VALUES (1, 999, 1, '2000-2001', 'X 1.0', 'FLEX', 'TESTE', 2000, 2001);")
    conexao = abrir_somente_leitura(banco)
    try:
        repo = Repositorio(conexao)
        veiculos = ServicoVeiculos(repo, FONTE)
        alertas = auditar_base(repo, veiculos, ServicoPecas(repo, veiculos, FONTE))
    finally:
        conexao.close()
    por_codigo = {a.codigo: a for a in alertas}
    assert {
        CodigoAlerta.REFERENCIA_INEXISTENTE, CodigoAlerta.VINCULO_ORFAO, CodigoAlerta.ANO_FIM_AUSENTE,
        CodigoAlerta.FAIXA_ANO_DIVERGENTE, CodigoAlerta.MOTORIZACAO_COMPOSTA, CodigoAlerta.MOTORIZACAO_SEM_CODIGO,
        CodigoAlerta.PRECO_AUSENTE, CodigoAlerta.POSSIVEL_PRODUTO_DUPLICADO, CodigoAlerta.COMBUSTIVEL_CONFLITANTE,
    } <= set(por_codigo)
    assert Evidencia(
        tabela="PRODUTO_APLICACAO", chave={"CodigoProduto": 1946, "CodigoAplicacao": 15098}, coluna="CodigoAplicacao", valor_original=15098
    ) in por_codigo[CodigoAlerta.VINCULO_ORFAO].evidencias
    conflito = por_codigo[CodigoAlerta.COMBUSTIVEL_CONFLITANTE].contexto
    assert "HR16DE|1.6|16V|L4|DOHC" in conflito["chaves_motor"]
    assert "KICKS" in conflito["modelos"]
    assert {31383, 15365} <= set(conflito["codigos_aplicacao"])
    assert any(e.chave == {"CodigoAplicacao": 1} for e in por_codigo[CodigoAlerta.REFERENCIA_INEXISTENTE].evidencias)


def test_respostas_validas_nao_tem_falhas(repo, veiculos, pecas):
    assert auditar_resposta(veiculos.motorizacoes("frontier", 2008), repo, {"modelo": "frontier", "ano": 2008}) == []
    assert auditar_resposta(veiculos.combustiveis("kicks", 2018), repo, {"modelo": "kicks", "ano": 2018}) == []
    assert auditar_resposta(pecas.da_aplicacao(35368), repo) == []
    assert auditar_resposta(pecas.obter(1946), repo) == []


def test_evidencia_adulterada_vira_falha_I1(repo, veiculos):
    resposta = veiculos.obter(35368)
    resposta.dados.motorizacao.original = "XXX"
    assert "I1" in invariantes(auditar_resposta(resposta, repo))


def test_evidencia_para_registro_inexistente_vira_falha_I1(repo, veiculos):
    resposta = veiculos.obter(35368)
    resposta.dados.combustivel.evidencia = resposta.dados.combustivel.evidencia.model_copy(update={"chave": {"CodigoAplicacao": 1}})
    assert "I1" in invariantes(auditar_resposta(resposta, repo))


def test_ausente_sem_alerta_vira_falha_I2(repo, veiculos):
    resposta = veiculos.obter(31393)
    resposta.alertas = [a for a in resposta.alertas if a.codigo != CodigoAlerta.ANO_FIM_AUSENTE]
    assert "I2" in invariantes(auditar_resposta(resposta, repo))


def test_revisao_inconsistente_vira_falha_I3(repo, veiculos):
    resposta = veiculos.obter(31393)
    resposta.revisao_humana.necessaria = False
    assert "I3" in invariantes(auditar_resposta(resposta, repo))


def test_identificado_inconsistente_vira_falha_I4(repo, veiculos):
    resposta = veiculos.motorizacoes("frontier", 2008)
    resposta.dados.identificado = True
    assert "I4" in invariantes(auditar_resposta(resposta, repo))


def test_aplicacao_fora_do_filtro_vira_falha_I5(repo, veiculos):
    resposta = veiculos.motorizacoes("frontier", 2008)
    assert "I5" in invariantes(auditar_resposta(resposta, repo, {"modelo": "kicks", "ano": 2008}))
    assert "I5" in invariantes(auditar_resposta(resposta, repo, {"modelo": "frontier", "ano": 2030}))


def test_produto_repetido_vira_falha_I6(repo, pecas):
    resposta = pecas.da_aplicacao(35368)
    resposta.dados.append(resposta.dados[0])
    assert "I6" in invariantes(auditar_resposta(resposta, repo))
