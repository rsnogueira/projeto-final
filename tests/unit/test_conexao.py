import sqlite3
from pathlib import Path

import pytest

from orcamento_pecas.config import CAMINHO_BANCO_PADRAO, caminho_banco
from orcamento_pecas.dados.conexao import BancoIndisponivelError, abrir_somente_leitura, sha256_arquivo


def test_escrita_falha_em_modo_somente_leitura(banco_teste: Path):
    conexao = abrir_somente_leitura(banco_teste)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conexao.execute("INSERT INTO FABRICANTE (CodigoFabricante, DescricaoFabricante) VALUES (999, 'X')")
    finally:
        conexao.close()


def test_banco_inexistente_lanca_erro_claro(tmp_path: Path):
    inexistente = tmp_path / "nao_existe.db"
    with pytest.raises(BancoIndisponivelError, match="nao_existe.db"):
        abrir_somente_leitura(inexistente)
    assert not inexistente.exists(), "abrir não pode criar o arquivo"


def test_linhas_acessiveis_por_nome_de_coluna(conexao_teste):
    linha = conexao_teste.execute("SELECT DescricaoFabricante FROM FABRICANTE WHERE CodigoFabricante = 73").fetchone()
    assert linha["DescricaoFabricante"] == "NISSAN"


def test_sha256_arquivo(tmp_path: Path):
    arquivo = tmp_path / "abc.txt"
    arquivo.write_bytes(b"abc")
    assert sha256_arquivo(arquivo) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_caminho_banco_prioriza_argumento_depois_variavel_depois_padrao(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ORCAMENTO_PECAS_DB", raising=False)
    assert caminho_banco() == CAMINHO_BANCO_PADRAO
    assert CAMINHO_BANCO_PADRAO.parts[-3:] == ("Database", "SQLite", "db_proj_final.db")

    monkeypatch.setenv("ORCAMENTO_PECAS_DB", str(tmp_path / "env.db"))
    assert caminho_banco() == tmp_path / "env.db"
    assert caminho_banco(tmp_path / "arg.db") == tmp_path / "arg.db"
