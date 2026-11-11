def test_pecas_da_aplicacao(cliente):
    corpo = cliente.get("/v1/veiculos/35368/pecas", params={"grupo": 39}).json()
    assert [p["codigo_produto"] for p in corpo["dados"]] == [6810, 11838, 6811, 11839, 6809, 11837]
    assert all(p["preco"]["normalizado"] is None for p in corpo["dados"])
    assert "PRECO_AUSENTE" in corpo["revisao_humana"]["motivos"]


def test_preco_serializado_como_texto_exato(cliente):
    corpo = cliente.get("/v1/veiculos/15365/pecas").json()
    assert {p["preco"]["normalizado"] for p in corpo["dados"]} == {"11.1"}
    assert {p["preco"]["original"] for p in corpo["dados"]} == {11.1}


def test_pecas_por_veiculo(cliente):
    corpo = cliente.get("/v1/pecas", params={"modelo": "frontier", "ano": 2008, "grupo": 39}).json()
    assert corpo["total"] == 8
    assert (corpo["pagina"], corpo["limite"]) == (1, 50)
    motor = next(a for a in corpo["alertas"] if a["codigo"] == "MOTOR_NAO_IDENTIFICADO")
    assert motor["severidade"] == "revisao"


def test_pecas_por_chave_de_motor(cliente):
    corpo = cliente.get(
        "/v1/pecas", params={"modelo": "frontier", "ano": 2008, "grupo": 39, "chave_motor": "YD25ETI|2.5|16V|L4|DOHC"}
    ).json()
    assert corpo["total"] == 6


def test_detalhe_do_produto(cliente):
    corpo = cliente.get("/v1/pecas/1946").json()
    assert corpo["dados"]["vinculos_orfaos"] == [15098]
    assert "PCs" in corpo["dados"]["campos_nao_interpretados"]
