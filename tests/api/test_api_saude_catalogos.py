from pathlib import Path

import pytest

from orcamento_pecas.api.app import criar_app
from orcamento_pecas.dados.conexao import BancoIndisponivelError, sha256_arquivo


def test_saude(cliente, banco_teste: Path):
    resposta = cliente.get("/v1/saude")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["somente_leitura"] is True
    assert corpo["sha256"] == sha256_arquivo(banco_teste)
    assert corpo["contagens"]["APLICACAO"] == 27


def test_fabricantes_e_grupos(cliente):
    fabricantes = cliente.get("/v1/fabricantes").json()
    grupos = cliente.get("/v1/grupos-produto").json()
    assert [f["descricao"]["normalizado"] for f in fabricantes["dados"]] == ["FIAT", "FORD", "NISSAN"]
    assert [g["codigo_grupo_produto"] for g in grupos["dados"]] == [7, 16, 24, 39]


def test_json_em_utf8_sem_escapes(cliente):
    resposta = cliente.get("/v1/grupos-produto")
    assert "GUIAS DE VÁLVULA".encode("utf-8") in resposta.content
    assert b"\\u00c1" not in resposta.content
    assert resposta.headers["content-type"].startswith("application/json")


def test_criar_app_com_banco_inexistente_falha_na_partida(tmp_path: Path):
    with pytest.raises(BancoIndisponivelError):
        criar_app(tmp_path / "nao_existe.db")
