from pathlib import Path

import pytest

from orcamento_pecas.dados.conexao import abrir_somente_leitura
from orcamento_pecas.dados.repositorio import IdentificadorNaoPermitidoError, Repositorio

RAIZ = Path(__file__).resolve().parents[2]
BRONZINAS_35368 = {6809, 6810, 6811, 11837, 11838, 11839}


def test_contagens_por_tabela(repo):
    assert repo.contagens() == {
        "APLICACAO": 27,
        "FABRICANTE": 3,
        "GRUPOPRODUTO": 4,
        "PRODUTO": 13,
        "PRODUTO_APLICACAO": 26,
        "TIPOAPLICACAO": 9,
    }


def test_listar_fabricantes_com_numero_de_aplicacoes(repo):
    linhas = [(r["CodigoFabricante"], r["DescricaoFabricante"], r["QuantidadeAplicacoes"]) for r in repo.listar_fabricantes()]
    assert linhas == [(2, "FIAT", 0), (3, "FORD", 0), (73, "NISSAN", 27)]


def test_listar_grupos_com_numero_de_produtos(repo):
    linhas = {r["CodigoGrupoProduto"]: r["QuantidadeProdutos"] for r in repo.listar_grupos_produto()}
    assert linhas == {7: 4, 16: 0, 24: 1, 39: 8}  # grupo 7: 5580, 5581, 3118 e 1946


def test_listar_aplicacoes_filtra_por_fabricante(repo):
    assert len(repo.listar_aplicacoes(None)) == 27
    assert len(repo.listar_aplicacoes(73)) == 27
    assert repo.listar_aplicacoes(2) == []


def test_aplicacao_traz_descricoes_de_fabricante_e_tipo(repo):
    linha = repo.obter_aplicacao(35368)
    assert linha["DescricaoFabricante"] == "NISSAN"
    assert linha["CodigoTipoAplicacao"] == 3
    assert linha["DescricaoTipoAplicacao"] == "Utilitários"
    assert linha["Motorizacao"] == "YD25ETI 2.5 L 16V DOHC L4"


def test_obter_aplicacao_inexistente_devolve_none(repo):
    assert repo.obter_aplicacao(999999) is None


def test_ano_fim_texto_vazio_preservado_como_texto(repo):
    linha = repo.obter_aplicacao(31393)
    assert linha["AnoFimFabricacao"] == ""
    assert isinstance(linha["AnoFimFabricacao"], str)


def test_pecas_da_aplicacao_filtradas_por_grupo(repo):
    todas = {r["CodigoProduto"] for r in repo.listar_pecas_das_aplicacoes([35368], None)}
    bronzinas = {r["CodigoProduto"] for r in repo.listar_pecas_das_aplicacoes([35368], 39)}
    assert todas == BRONZINAS_35368 | {3118}
    assert bronzinas == BRONZINAS_35368


def test_pecas_trazem_codigo_da_aplicacao_e_grupo(repo):
    linha = next(r for r in repo.listar_pecas_das_aplicacoes([15365], None) if r["CodigoProduto"] == 5580)
    assert linha["CodigoAplicacao"] == 15365
    assert linha["DescricaoGrupoProduto"] == "GUIAS DE VÁLVULA"
    assert linha["PrecoProduto"] == 11.1


def test_pecas_de_lista_vazia_de_aplicacoes(repo):
    assert repo.listar_pecas_das_aplicacoes([], None) == []


def test_pecas_das_aplicacoes_equivalem_a_query_sql_original(repo, conexao_teste):
    sql_original = (RAIZ / "Database" / "Queries_Uteis" / "qry_produto_por_veiculo.sql").read_text(encoding="utf-8")
    esperado = {(r["CodigoAplicacao"], r["CodigoProduto"]) for r in conexao_teste.execute(sql_original)}
    codigos = [r["CodigoAplicacao"] for r in repo.listar_aplicacoes(None)]
    obtido = {(r["CodigoAplicacao"], r["CodigoProduto"]) for r in repo.listar_pecas_das_aplicacoes(codigos, None)}
    assert obtido == esperado
    assert len(obtido) == 25  # 26 vínculos menos o órfão (1946, 15098)


def test_produto_e_suas_aplicacoes(repo):
    assert repo.obter_produto(6809)["NumeroProduto"] == "55.455.007"
    assert repo.obter_produto(999999) is None
    assert repo.aplicacoes_do_produto(6809) == [35368, 35369, 35374]


def test_vinculos_orfaos_do_produto(repo):
    assert repo.aplicacoes_do_produto(1946) == []
    assert repo.vinculos_orfaos_do_produto(1946) == [15098]
    assert repo.vinculos_orfaos_do_produto(6809) == []


def test_vinculos_orfaos_da_base(repo):
    assert [(r["CodigoProduto"], r["CodigoAplicacao"]) for r in repo.vinculos_orfaos()] == [(1946, 15098)]


def test_listar_produtos_vinculados_ignora_orfaos_e_soltos(repo):
    assert repo.listar_produtos_vinculados() == sorted(BRONZINAS_35368 | {6656, 11758, 5580, 5581, 3118})


def test_referencias_inexistentes_vazias_na_base_teste(repo):
    assert repo.referencias_inexistentes() == []


def test_referencias_inexistentes_detecta_fabricante_e_grupo(criar_banco):
    banco = criar_banco(
        "INSERT INTO APLICACAO VALUES (1, 999, 1, '2000-2001', 'X 1.0', 'FLEX', 'TESTE', 2000, 2001);"
        "INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, NumeroProduto, NumeroProdutoPesq)"
        " VALUES (2, 'PECA', 888, 'N', 'N');"
    )
    conexao = abrir_somente_leitura(banco)
    try:
        refs = Repositorio(conexao).referencias_inexistentes()
    finally:
        conexao.close()
    assert sorted((r["tabela"], tuple(r["chave"].items()), r["coluna"], r["valor"]) for r in refs) == [
        ("APLICACAO", (("CodigoAplicacao", 1),), "CodigoFabricante", 999),
        ("PRODUTO", (("CodigoProduto", 2),), "CodigoGrupoProduto", 888),
    ]


def test_ler_valor_devolve_valor_original(repo):
    assert repo.ler_valor("APLICACAO", {"CodigoAplicacao": 31393}, "AnoFimFabricacao") == ""
    assert repo.ler_valor("PRODUTO", {"CodigoProduto": 6809}, "PrecoProduto") is None
    assert repo.ler_valor("PRODUTO_APLICACAO", {"CodigoProduto": 6809, "CodigoAplicacao": 35368}, "CodigoAplicacao") == 35368


@pytest.mark.parametrize(
    ("tabela", "chave", "coluna"),
    [
        ("sqlite_master", {"CodigoAplicacao": 1}, "sql"),
        ("APLICACAO; DROP TABLE APLICACAO", {"CodigoAplicacao": 1}, "Motorizacao"),
        ("APLICACAO", {"CodigoAplicacao": 1}, "Motorizacao FROM APLICACAO --"),
        ("APLICACAO", {"1=1 OR CodigoAplicacao": 1}, "Motorizacao"),
    ],
)
def test_ler_valor_rejeita_identificadores_fora_da_lista(repo, tabela, chave, coluna):
    with pytest.raises(IdentificadorNaoPermitidoError):
        repo.ler_valor(tabela, chave, coluna)
