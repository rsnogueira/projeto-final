"""Validação real controlada (casos V1 a V7) contra Database/SQLite/db_proj_final.db, somente leitura.

Os valores esperados foram levantados no perfil da base de 2026-11-10 (SHA-256 abaixo). Se a base mudar,
o teste V7 falha primeiro: os demais valores precisam ser levantados de novo, nunca ajustados às cegas.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcamento_pecas.api.app import criar_app
from orcamento_pecas.config import CAMINHO_BANCO_PADRAO as BANCO_REAL
from orcamento_pecas.dados.conexao import sha256_arquivo

pytestmark = pytest.mark.base_real

SHA256_BASE_VALIDADA = "8a700b84124cefe12332e115d73da458f29082d57d627f5c5b0b8064b9d7cd2a"
CHAVES_FRONTIER_2008 = {
    "4.07 TCE SPRINT|2.8|12V|L4|SOHC",
    "SPRINT EURO 3|2.8|12V|L4|SOHC",
    "YD25ETI|2.5|16V|L4|DOHC",
    "YD25 SELL|2.5|16V|?|?",
    "YD25DDTI+YD25ETI|2.5|16V|L4|DOHC",
    "M9T|2.3|16V|L4|DOHC",
}


@pytest.fixture(scope="module")
def sha_antes() -> str:
    if not BANCO_REAL.exists():
        pytest.skip(f"base real ausente: {BANCO_REAL}")
    return sha256_arquivo(BANCO_REAL)


@pytest.fixture(scope="module")
def cliente(sha_antes):
    with TestClient(criar_app(BANCO_REAL)) as cliente:
        yield cliente


def _alerta(corpo, codigo):
    return next(a for a in corpo["alertas"] if a["codigo"] == codigo)


def test_v1_frontier_2008_motorizacoes(cliente):
    corpo = cliente.get("/v1/veiculos/motorizacoes", params={"modelo": "frontier", "ano": 2008}).json()
    assert len(corpo["dados"]["aplicacoes"]) == 14
    assert corpo["dados"]["identificado"] is False
    assert {c["chave_motor"] for c in corpo["dados"]["candidatos"]} == CHAVES_FRONTIER_2008
    assert any(e["chave"] == {"CodigoAplicacao": 31393} for e in _alerta(corpo, "ANO_FIM_AUSENTE")["evidencias"])
    assert any(e["chave"] == {"CodigoAplicacao": 36311} for e in _alerta(corpo, "MOTORIZACAO_COMPOSTA")["evidencias"])
    assert "MOTOR_NAO_IDENTIFICADO" in {a["codigo"] for a in corpo["alertas"]}


def test_v2_kicks_2018_combustiveis(cliente):
    corpo = cliente.get("/v1/veiculos/combustiveis", params={"modelo": "kicks", "ano": 2018}).json()
    assert len(corpo["dados"]["aplicacoes"]) == 12
    assert [(c["combustivel"], c["codigos_aplicacao"]) for c in corpo["dados"]["combustiveis"]] == [
        ("FLEX", [31383, 31483, 32111, 34585, 34586]),
        ("GASOLINA", [15365, 15366, 15368, 15369, 15370, 15372, 15373]),
    ]
    assert _alerta(corpo, "COMBUSTIVEL_CONFLITANTE")["contexto"]["chaves_motor"] == ["HR16DE|1.6|16V|L4|DOHC"]
    assert "MULTIPLOS_COMBUSTIVEIS" in {a["codigo"] for a in corpo["alertas"]}


def test_v3_bronzinas_da_aplicacao_35368(cliente):
    corpo = cliente.get("/v1/veiculos/35368/pecas", params={"grupo": 39}).json()
    assert {p["codigo_produto"] for p in corpo["dados"]} == {6809, 6810, 6811, 11837, 11838, 11839}
    assert all(p["preco"]["normalizado"] is None for p in corpo["dados"])
    assert len(_alerta(corpo, "POSSIVEL_PRODUTO_DUPLICADO")["contexto"]["grupos_duplicidade"]) == 3
    assert "PRECO_AUSENTE" in corpo["revisao_humana"]["motivos"]
    assert corpo["revisao_humana"]["necessaria"] is True


def test_v4_frontier_2008_combustivel_unico(cliente):
    corpo = cliente.get("/v1/veiculos/combustiveis", params={"modelo": "frontier", "ano": 2008}).json()
    assert corpo["dados"]["unico"] is True
    assert [c["combustivel"] for c in corpo["dados"]["combustiveis"]] == ["DIESEL"]


def test_v5_modelo_inexistente(cliente):
    corpo = cliente.get("/v1/veiculos/motorizacoes", params={"modelo": "xyz", "ano": 2008}).json()
    assert corpo["dados"]["aplicacoes"] == []
    assert {"FRONTIER", "KICKS"} <= set(_alerta(corpo, "MODELO_NAO_ENCONTRADO")["contexto"]["modelos_disponiveis"])


def test_v6_fabricante_sem_veiculos(cliente):
    corpo = cliente.get("/v1/veiculos/motorizacoes", params={"fabricante": "fiat", "modelo": "uno", "ano": 2010}).json()
    assert [a["codigo"] for a in corpo["alertas"]] == ["FABRICANTE_SEM_VEICULOS"]


def test_v7_base_inalterada(cliente, sha_antes):
    assert sha_antes == SHA256_BASE_VALIDADA, "a base mudou: levante de novo os valores esperados de V1 a V6"
    assert cliente.get("/v1/saude").json()["sha256"] == SHA256_BASE_VALIDADA
    assert sha256_arquivo(BANCO_REAL) == SHA256_BASE_VALIDADA


def test_v8_pecas_por_chave_de_motor(cliente):
    """Caminho do chatbot: motor identificado (chave) → bronzinas. Perfil: só 35368 e 35369 têm bronzinas YD25ETI."""
    corpo = cliente.get(
        "/v1/pecas", params={"modelo": "frontier", "ano": 2008, "grupo": 39, "chave_motor": "YD25ETI|2.5|16V|L4|DOHC"}
    ).json()
    assert sorted(p["codigo_produto"] for p in corpo["dados"]) == [6809, 6810, 6811, 11837, 11838, 11839]
    assert "MOTOR_NAO_IDENTIFICADO" not in {a["codigo"] for a in corpo["alertas"]}
    assert corpo["revisao_humana"]["motivos"] == ["PRECO_AUSENTE", "POSSIVEL_PRODUTO_DUPLICADO"]
