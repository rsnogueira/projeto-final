"""Fixtures compartilhadas pelos testes.

A base de teste é criada em diretório temporário a partir de tests/dados/base_teste.sql
(DDL idêntico ao da base real e linhas copiadas dela). A base real nunca é alterada.
"""

import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SQL_BASE_TESTE = RAIZ / "tests" / "dados" / "base_teste.sql"
BANCO_REAL = RAIZ / "Database" / "SQLite" / "db_proj_final.db"


def _executar_script(destino: Path, script: str) -> None:
    conexao = sqlite3.connect(destino)
    try:
        conexao.execute("PRAGMA journal_mode = OFF")
        conexao.execute("PRAGMA synchronous = OFF")
        conexao.executescript(script)
        conexao.commit()
    finally:
        conexao.close()


@pytest.fixture(scope="session")
def _modelo_banco(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Base de teste criada uma única vez por sessão. É somente leitura para os testes."""
    destino = tmp_path_factory.mktemp("base") / "base_teste.db"
    _executar_script(destino, SQL_BASE_TESTE.read_text(encoding="utf-8"))
    return destino


@pytest.fixture
def criar_banco(_modelo_banco: Path, tmp_path: Path) -> Callable[..., Path]:
    """Fábrica: copia a base de teste e aplica SQL extra (para semear anomalias)."""
    contador = {"n": 0}

    def fabrica(sql_extra: str = "") -> Path:
        contador["n"] += 1
        destino = tmp_path / f"base_teste_{contador['n']}.db"
        shutil.copyfile(_modelo_banco, destino)
        if sql_extra:
            _executar_script(destino, sql_extra)
        return destino

    return fabrica


@pytest.fixture
def banco_teste(_modelo_banco: Path) -> Path:
    return _modelo_banco


@pytest.fixture
def conexao_teste(banco_teste: Path):
    from orcamento_pecas.dados.conexao import abrir_somente_leitura

    conexao = abrir_somente_leitura(banco_teste)
    yield conexao
    conexao.close()


@pytest.fixture
def repo(conexao_teste):
    from orcamento_pecas.dados.repositorio import Repositorio

    return Repositorio(conexao_teste)


@pytest.fixture
def banco_real() -> Path:
    if not BANCO_REAL.exists():
        pytest.skip(f"base real ausente: {BANCO_REAL}")
    return BANCO_REAL
