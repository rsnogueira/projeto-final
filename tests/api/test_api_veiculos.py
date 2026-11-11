import pytest

from orcamento_pecas.dados.conexao import abrir_somente_leitura
from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.servicos.veiculos import ServicoVeiculos


def test_motorizacoes(cliente):
    resposta = cliente.get("/v1/veiculos/motorizacoes", params={"modelo": "frontier", "ano": 2008})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["dados"]["identificado"] is False
    assert len(corpo["dados"]["candidatos"]) == 6
    assert len(corpo["dados"]["aplicacoes"]) == 14
    assert corpo["revisao_humana"]["necessaria"] is True


def test_resposta_http_igual_a_do_servico(cliente, app, banco_teste):
    conexao = abrir_somente_leitura(banco_teste)
    try:
        esperado = ServicoVeiculos(Repositorio(conexao), app.state.fonte).motorizacoes("frontier", 2008).model_dump(mode="json")
    finally:
        conexao.close()
    assert cliente.get("/v1/veiculos/motorizacoes", params={"modelo": "frontier", "ano": 2008}).json() == esperado


def test_combustiveis(cliente):
    corpo = cliente.get("/v1/veiculos/combustiveis", params={"modelo": "kicks", "ano": 2018}).json()
    assert corpo["dados"]["unico"] is False
    assert [c["combustivel"] for c in corpo["dados"]["combustiveis"]] == ["FLEX", "GASOLINA"]


def test_rotas_fixas_nao_capturadas_por_codigo(cliente):
    assert cliente.get("/v1/veiculos/combustiveis", params={"modelo": "kicks", "ano": 2018}).status_code == 200
    sem_parametros = cliente.get("/v1/veiculos/motorizacoes")
    assert sem_parametros.status_code == 422
    locais = {tuple(erro["loc"]) for erro in sem_parametros.json()["detail"]}
    assert ("query", "modelo") in locais
    assert not any("codigo_aplicacao" in local for local in locais)


@pytest.mark.parametrize(
    "parametros",
    [
        {"modelo": "frontier", "ano": "abc"},
        {"modelo": "frontier", "ano": 99},
        {"modelo": "", "ano": 2008},
        {"modelo": "   ", "ano": 2008},
        {"ano": 2008},
    ],
)
def test_parametros_invalidos_retornam_422(cliente, parametros):
    assert cliente.get("/v1/veiculos/motorizacoes", params=parametros).status_code == 422


def test_limite_acima_do_maximo_retorna_422(cliente):
    assert cliente.get("/v1/veiculos", params={"limite": 500}).status_code == 422
    assert cliente.get("/v1/pecas", params={"modelo": "frontier", "ano": 2008, "limite": 201}).status_code == 422


@pytest.mark.parametrize("modelo", ["' OR 1=1 --", "%", "_", "frontier'; DROP TABLE APLICACAO; --"])
def test_parametro_malicioso_na_api_retorna_vazio(cliente, modelo):
    resposta = cliente.get("/v1/veiculos/motorizacoes", params={"modelo": modelo, "ano": 2008})
    assert resposta.status_code == 200
    assert resposta.json()["dados"]["aplicacoes"] == []
    assert cliente.get("/v1/saude").json()["contagens"]["APLICACAO"] == 27


def test_modelo_com_espaco_no_inicio_e_aceito(cliente):
    assert cliente.get("/v1/veiculos/motorizacoes", params={"modelo": "  frontier", "ano": 2008}).status_code == 200


def test_busca_paginada_e_detalhe(cliente):
    busca = cliente.get("/v1/veiculos", params={"modelo": "frontier", "pagina": 2, "limite": 5}).json()
    assert busca["total"] == 17
    assert [a["codigo_aplicacao"] for a in busca["dados"]] == [13823, 13824, 13979, 31393, 32415]
    detalhe = cliente.get("/v1/veiculos/35368")
    assert detalhe.status_code == 200
    assert detalhe.json()["dados"]["motorizacao"]["normalizado"]["chave"] == "YD25ETI|2.5|16V|L4|DOHC"


def test_codigos_inexistentes_retornam_404(cliente):
    for rota in ("/v1/veiculos/999999", "/v1/veiculos/999999/pecas", "/v1/pecas/999999"):
        resposta = cliente.get(rota)
        assert resposta.status_code == 404, rota
        assert "999999" in resposta.json()["detail"]


def test_codigo_nao_numerico_retorna_422(cliente):
    assert cliente.get("/v1/veiculos/abc").status_code == 422
