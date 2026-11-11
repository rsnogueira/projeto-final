"""Configuração: resolução do caminho do banco de dados."""

import os
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_BANCO_PADRAO = RAIZ_PROJETO / "Database" / "SQLite" / "db_proj_final.db"
VARIAVEL_AMBIENTE_BANCO = "ORCAMENTO_PECAS_DB"


def caminho_banco(argumento: Path | str | None = None) -> Path:
    """Prioridade: argumento explícito, depois a variável de ambiente, depois o caminho padrão."""
    if argumento:
        return Path(argumento)
    valor_ambiente = os.environ.get(VARIAVEL_AMBIENTE_BANCO)
    if valor_ambiente:
        return Path(valor_ambiente)
    return CAMINHO_BANCO_PADRAO


def rotulo_banco(caminho: Path | str) -> str:
    """Caminho relativo à raiz do projeto quando possível (respostas iguais em qualquer máquina)."""
    absoluto = Path(caminho).resolve()
    try:
        return absoluto.relative_to(RAIZ_PROJETO).as_posix()
    except ValueError:
        return absoluto.as_posix()
