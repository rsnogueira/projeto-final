ROTAS = {
    "/v1/saude",
    "/v1/fabricantes",
    "/v1/grupos-produto",
    "/v1/veiculos",
    "/v1/veiculos/motorizacoes",
    "/v1/veiculos/combustiveis",
    "/v1/veiculos/{codigo_aplicacao}",
    "/v1/veiculos/{codigo_aplicacao}/pecas",
    "/v1/pecas",
    "/v1/pecas/{codigo_produto}",
}
TAGS_PT = {"Saúde", "Catálogos", "Veículos", "Peças"}


def operacoes(esquema):
    for rota, metodos in esquema["paths"].items():
        for metodo, operacao in metodos.items():
            yield rota, metodo, operacao


def test_openapi_lista_exatamente_as_rotas_previstas(cliente):
    esquema = cliente.get("/openapi.json").json()
    assert set(esquema["paths"]) == ROTAS
    assert all(metodo == "get" for _, metodo, _ in operacoes(esquema))


def test_openapi_descreve_todos_endpoints_com_tags_em_portugues(cliente):
    esquema = cliente.get("/openapi.json").json()
    for rota, _, operacao in operacoes(esquema):
        assert operacao.get("summary"), rota
        assert operacao.get("description"), rota
        assert set(operacao["tags"]) <= TAGS_PT, rota


def test_parametros_tem_descricao_e_os_obrigatorios_tem_exemplo(cliente):
    esquema = cliente.get("/openapi.json").json()
    for rota, _, operacao in operacoes(esquema):
        for parametro in operacao.get("parameters", []):
            assert parametro.get("description"), (rota, parametro["name"])
            if parametro.get("required") and parametro["in"] == "query":
                assert parametro.get("examples") or parametro["schema"].get("examples"), (rota, parametro["name"])


def test_rotas_de_detalhe_documentam_404(cliente):
    esquema = cliente.get("/openapi.json").json()
    for rota in ("/v1/veiculos/{codigo_aplicacao}", "/v1/veiculos/{codigo_aplicacao}/pecas", "/v1/pecas/{codigo_produto}"):
        assert "404" in esquema["paths"][rota]["get"]["responses"], rota


def test_swagger_disponivel(cliente):
    resposta = cliente.get("/docs")
    assert resposta.status_code == 200
    assert "swagger" in resposta.text.lower()


def test_modelos_principais_tem_exemplos_reais(cliente):
    """I5: o Swagger mostra exemplos (valores reais da base) nos componentes das respostas."""
    componentes = cliente.get("/openapi.json").json()["components"]["schemas"]
    for nome in ("Evidencia", "Alerta", "RevisaoHumana", "Fonte", "ParametroEcoado", "MotorNormalizado", "DadosSaude"):
        assert componentes[nome].get("examples"), nome
    rastreados = [n for n in componentes if n.startswith("ValorRastreado")]
    assert rastreados and all(componentes[n].get("examples") for n in rastreados)
