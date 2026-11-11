from orcamento_pecas.auditoria.amostragem import ItemPopulacao, sortear_amostra, sql_conferencia
from orcamento_pecas.auditoria.bateria import Consulta, gerar_bateria
from orcamento_pecas.dominio.modelos import Evidencia


def test_bateria_deterministica(repo):
    assert gerar_bateria(repo) == gerar_bateria(repo)


def test_bateria_cobre_modelos_anos_aplicacoes_e_produtos(repo):
    bateria = gerar_bateria(repo)
    assert Consulta(tipo="motorizacoes", parametros={"modelo": "FRONTIER", "ano": 2008}) in bateria
    assert Consulta(tipo="combustiveis", parametros={"modelo": "KICKS", "ano": 2018}) in bateria
    assert Consulta(tipo="pecas_da_aplicacao", parametros={"codigo_aplicacao": 35368}) in bateria
    assert Consulta(tipo="produto", parametros={"codigo_produto": 6809}) in bateria
    anos_kicks = {c.parametros["ano"] for c in bateria if c.tipo == "motorizacoes" and c.parametros["modelo"] == "KICKS"}
    # KICKS vai de 2011 (31483, sem fim) até o maior ano final da base (2023)
    assert anos_kicks == set(range(2011, 2024))


def test_rota_da_consulta_para_o_revisor():
    assert Consulta(tipo="motorizacoes", parametros={"modelo": "FRONTIER", "ano": 2008}).rota() == (
        "GET /v1/veiculos/motorizacoes?modelo=FRONTIER&ano=2008"
    )
    assert Consulta(tipo="produto", parametros={"codigo_produto": 6809}).rota() == "GET /v1/pecas/6809"


def _populacao(com: int, sem: int) -> list[ItemPopulacao]:
    itens = []
    for i in range(com + sem):
        evidencia = Evidencia(tabela="APLICACAO", chave={"CodigoAplicacao": i}, coluna="Combustivel", valor_original=f"V{i}")
        itens.append(ItemPopulacao(
            consulta="GET /x", campo=f"dados[{i}]", valor_exibido=f"V{i}", original=f"V{i}",
            evidencia=evidencia, com_alerta_revisao=i < com,
        ))
    return itens


def test_amostra_mesma_semente_mesmo_resultado_e_estratificada():
    populacao = _populacao(10, 10)
    a = sortear_amostra(populacao, 6, 42)
    assert a == sortear_amostra(populacao, 6, 42)
    assert [i.estrato for i in a].count("com_alerta") == 3
    assert [i.estrato for i in a].count("limpo") == 3
    assert [i.id for i in a] == ["A01", "A02", "A03", "A04", "A05", "A06"]


def test_amostra_completa_com_o_estrato_disponivel():
    a = sortear_amostra(_populacao(2, 10), 6, 42)
    assert [i.estrato for i in a].count("com_alerta") == 2
    assert [i.estrato for i in a].count("limpo") == 4


def test_amostra_maior_que_a_populacao():
    assert len(sortear_amostra(_populacao(1, 2), 30, 42)) == 3


def test_sql_de_conferencia_devolve_o_valor_original(conexao_teste):
    evidencia = Evidencia(tabela="APLICACAO", chave={"CodigoAplicacao": 31393}, coluna="AnoFimFabricacao", valor_original="")
    sql = sql_conferencia(evidencia)
    assert sql == 'SELECT "AnoFimFabricacao" FROM "APLICACAO" WHERE "CodigoAplicacao" = 31393;'
    assert conexao_teste.execute(sql).fetchone()[0] == ""


def test_bateria_cobre_o_caminho_do_chatbot_e_os_filtros(repo):
    """I4: /v1/pecas por veículo, por chave de motor e por combustível; filtro de combustível em motorizações;
    detalhe de aplicação e busca de veículos."""
    bateria = gerar_bateria(repo)
    esperadas = [
        Consulta(tipo="pecas_por_veiculo", parametros={"modelo": "FRONTIER", "ano": 2008}),
        Consulta(tipo="pecas_por_veiculo", parametros={"modelo": "FRONTIER", "ano": 2008, "chave_motor": "YD25ETI|2.5|16V|L4|DOHC"}),
        Consulta(tipo="motorizacoes", parametros={"modelo": "KICKS", "ano": 2018, "combustivel": "GASOLINA"}),
        Consulta(tipo="pecas_por_veiculo", parametros={"modelo": "KICKS", "ano": 2018, "combustivel": "GASOLINA"}),
        Consulta(tipo="aplicacao", parametros={"codigo_aplicacao": 35368}),
        Consulta(tipo="busca_veiculos", parametros={"modelo": "FRONTIER"}),
    ]
    for consulta in esperadas:
        assert consulta in bateria, consulta


def test_rotas_das_novas_consultas():
    assert Consulta(tipo="pecas_por_veiculo", parametros={"modelo": "FRONTIER", "ano": 2008, "chave_motor": "YD25ETI|2.5|16V|L4|DOHC"}).rota() == (
        "GET /v1/pecas?modelo=FRONTIER&ano=2008&chave_motor=YD25ETI%7C2.5%7C16V%7CL4%7CDOHC"
    )
    assert Consulta(tipo="aplicacao", parametros={"codigo_aplicacao": 35368}).rota() == "GET /v1/veiculos/35368"
    assert Consulta(tipo="busca_veiculos", parametros={"modelo": "FRONTIER"}).rota() == "GET /v1/veiculos?modelo=FRONTIER"
