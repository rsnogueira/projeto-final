"""Fábrica de evidências e valores rastreados a partir de linhas do SQLite."""

import sqlite3
from typing import Any

from orcamento_pecas.dominio.modelos import Evidencia, TabelaBase, ValorRastreado


def evidencia_de(linha: sqlite3.Row, tabela: TabelaBase, chave: dict[str, int], coluna: str) -> Evidencia:
    return Evidencia(tabela=tabela, chave=dict(chave), coluna=coluna, valor_original=linha[coluna])


def valor_de(linha: sqlite3.Row, tabela: TabelaBase, chave: dict[str, int], coluna: str, normalizado: Any) -> ValorRastreado:
    """`linha[coluna]` deve ser o valor da coluna `coluna` da `tabela` (as consultas preservam os nomes)."""
    evidencia = evidencia_de(linha, tabela, chave, coluna)
    return ValorRastreado(original=evidencia.valor_original, normalizado=normalizado, evidencia=evidencia)
