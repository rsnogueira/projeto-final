"""Acesso a dados: todo o SQL do projeto, sempre parametrizado.

Nomes de tabela e coluna vêm apenas de `ESQUEMA` (lista fixa). Texto digitado pelo
usuário nunca chega ao SQL: a correspondência de modelo é feita em Python.
"""

import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any

# tabela -> (colunas da chave usada nas evidências, todas as colunas)
ESQUEMA: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "APLICACAO": (
        ("CodigoAplicacao",),
        ("CodigoAplicacao", "CodigoFabricante", "CodigoTipoAplicacao", "FaixaAno", "Motorizacao", "Combustivel",
         "DescricaoAplicacao", "AnoInicioFabricacao", "AnoFimFabricacao"),
    ),
    "FABRICANTE": (("CodigoFabricante",), ("CodigoFabricante", "DescricaoFabricante")),
    "GRUPOPRODUTO": (("CodigoGrupoProduto",), ("CodigoGrupoProduto", "DescricaoGrupoProduto")),
    "PRODUTO": (
        ("CodigoProduto",),
        ("CodigoProduto", "DescricaoProduto", "CodigoGrupoProduto", "PrecoProduto", "NumeroProduto",
         "NumeroProdutoPesq", "CodigoSimilar", "CpoAuxProd5", "QtdEmbalagem", "CpoAuxProd25", "PCs"),
    ),
    "PRODUTO_APLICACAO": (("CodigoProduto", "CodigoAplicacao"), ("CodigoProduto", "CodigoAplicacao")),
    "TIPOAPLICACAO": (("CodigoTipoAplicacao",), ("CodigoTipoAplicacao", "DescricaoTipoAplicacao")),
}

_SELECT_APLICACAO = """
    SELECT a.CodigoAplicacao, a.CodigoFabricante, f.DescricaoFabricante,
           a.CodigoTipoAplicacao, t.DescricaoTipoAplicacao,
           a.FaixaAno, a.Motorizacao, a.Combustivel, a.DescricaoAplicacao,
           a.AnoInicioFabricacao, a.AnoFimFabricacao
      FROM APLICACAO a
      LEFT JOIN FABRICANTE f ON f.CodigoFabricante = a.CodigoFabricante
      LEFT JOIN TIPOAPLICACAO t ON t.CodigoTipoAplicacao = a.CodigoTipoAplicacao
"""

# Equivalente filtrado de Database/Queries_Uteis/qry_produto_por_veiculo.sql
_SELECT_PECAS = """
    SELECT pa.CodigoAplicacao, p.CodigoProduto, p.DescricaoProduto, p.CodigoGrupoProduto,
           g.DescricaoGrupoProduto, p.PrecoProduto, p.NumeroProduto, p.QtdEmbalagem
      FROM PRODUTO_APLICACAO pa
      JOIN APLICACAO a ON a.CodigoAplicacao = pa.CodigoAplicacao
      JOIN PRODUTO p ON p.CodigoProduto = pa.CodigoProduto
      LEFT JOIN GRUPOPRODUTO g ON g.CodigoGrupoProduto = p.CodigoGrupoProduto
"""


class IdentificadorNaoPermitidoError(ValueError):
    """Tabela, coluna ou chave fora da lista fixa do esquema."""


class RegistroInexistenteError(LookupError):
    """A chave informada não corresponde a nenhum registro."""


def _marcadores(quantidade: int) -> str:
    return ", ".join("?" for _ in range(quantidade))


class Repositorio:
    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao

    def _todas(self, sql: str, parametros: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return self._conexao.execute(sql, parametros).fetchall()

    def _uma(self, sql: str, parametros: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self._conexao.execute(sql, parametros).fetchone()

    # --- catálogos ---------------------------------------------------------------

    def contagens(self) -> dict[str, int]:
        return {tabela: self._uma(f'SELECT COUNT(*) FROM "{tabela}"')[0] for tabela in sorted(ESQUEMA)}

    def listar_fabricantes(self) -> list[sqlite3.Row]:
        return self._todas(
            """
            SELECT f.CodigoFabricante, f.DescricaoFabricante, COUNT(a.CodigoAplicacao) AS QuantidadeAplicacoes
              FROM FABRICANTE f
              LEFT JOIN APLICACAO a ON a.CodigoFabricante = f.CodigoFabricante
             GROUP BY f.CodigoFabricante, f.DescricaoFabricante
             ORDER BY f.DescricaoFabricante
            """
        )

    def listar_grupos_produto(self) -> list[sqlite3.Row]:
        return self._todas(
            """
            SELECT g.CodigoGrupoProduto, g.DescricaoGrupoProduto, COUNT(p.CodigoProduto) AS QuantidadeProdutos
              FROM GRUPOPRODUTO g
              LEFT JOIN PRODUTO p ON p.CodigoGrupoProduto = g.CodigoGrupoProduto
             GROUP BY g.CodigoGrupoProduto, g.DescricaoGrupoProduto
             ORDER BY g.CodigoGrupoProduto
            """
        )

    # --- aplicações (veículos) ---------------------------------------------------

    def listar_aplicacoes(self, codigo_fabricante: int | None) -> list[sqlite3.Row]:
        return self._todas(
            _SELECT_APLICACAO + " WHERE (? IS NULL OR a.CodigoFabricante = ?) ORDER BY a.CodigoAplicacao",
            (codigo_fabricante, codigo_fabricante),
        )

    def obter_aplicacao(self, codigo: int) -> sqlite3.Row | None:
        return self._uma(_SELECT_APLICACAO + " WHERE a.CodigoAplicacao = ?", (codigo,))

    # --- peças -------------------------------------------------------------------

    def listar_pecas_das_aplicacoes(self, codigos: Sequence[int], codigo_grupo: int | None) -> list[sqlite3.Row]:
        if not codigos:
            return []
        return self._todas(
            _SELECT_PECAS
            + f" WHERE pa.CodigoAplicacao IN ({_marcadores(len(codigos))})"
            + " AND (? IS NULL OR p.CodigoGrupoProduto = ?)"
            + " ORDER BY pa.CodigoAplicacao, p.CodigoProduto",
            (*codigos, codigo_grupo, codigo_grupo),
        )

    def obter_produto(self, codigo: int) -> sqlite3.Row | None:
        return self._uma(
            """
            SELECT p.*, g.DescricaoGrupoProduto
              FROM PRODUTO p
              LEFT JOIN GRUPOPRODUTO g ON g.CodigoGrupoProduto = p.CodigoGrupoProduto
             WHERE p.CodigoProduto = ?
            """,
            (codigo,),
        )

    def aplicacoes_do_produto(self, codigo: int) -> list[int]:
        return [
            linha[0]
            for linha in self._todas(
                """
                SELECT pa.CodigoAplicacao
                  FROM PRODUTO_APLICACAO pa
                  JOIN APLICACAO a ON a.CodigoAplicacao = pa.CodigoAplicacao
                 WHERE pa.CodigoProduto = ?
                 ORDER BY pa.CodigoAplicacao
                """,
                (codigo,),
            )
        ]

    def vinculos_orfaos_do_produto(self, codigo: int) -> list[int]:
        return [
            linha[0]
            for linha in self._todas(
                """
                SELECT pa.CodigoAplicacao
                  FROM PRODUTO_APLICACAO pa
                 WHERE pa.CodigoProduto = ?
                   AND NOT EXISTS (SELECT 1 FROM APLICACAO a WHERE a.CodigoAplicacao = pa.CodigoAplicacao)
                 ORDER BY pa.CodigoAplicacao
                """,
                (codigo,),
            )
        ]

    # --- auditoria ---------------------------------------------------------------

    def vinculos_orfaos(self) -> list[sqlite3.Row]:
        return self._todas(
            """
            SELECT pa.CodigoProduto, pa.CodigoAplicacao
              FROM PRODUTO_APLICACAO pa
             WHERE NOT EXISTS (SELECT 1 FROM APLICACAO a WHERE a.CodigoAplicacao = pa.CodigoAplicacao)
             ORDER BY pa.CodigoProduto, pa.CodigoAplicacao
            """
        )

    def listar_produtos_vinculados(self) -> list[int]:
        return [
            linha[0]
            for linha in self._todas(
                """
                SELECT DISTINCT pa.CodigoProduto
                  FROM PRODUTO_APLICACAO pa
                  JOIN APLICACAO a ON a.CodigoAplicacao = pa.CodigoAplicacao
                  JOIN PRODUTO p ON p.CodigoProduto = pa.CodigoProduto
                 ORDER BY pa.CodigoProduto
                """
            )
        ]

    def referencias_inexistentes(self) -> list[dict[str, Any]]:
        """Chaves estrangeiras que apontam para registros inexistentes (exceto vínculos órfãos de aplicação)."""
        verificacoes = [
            ("APLICACAO", "CodigoAplicacao", "CodigoFabricante", "FABRICANTE", "CodigoFabricante"),
            ("APLICACAO", "CodigoAplicacao", "CodigoTipoAplicacao", "TIPOAPLICACAO", "CodigoTipoAplicacao"),
            ("PRODUTO", "CodigoProduto", "CodigoGrupoProduto", "GRUPOPRODUTO", "CodigoGrupoProduto"),
        ]
        resultado: list[dict[str, Any]] = []
        for tabela, chave, coluna, referida, coluna_referida in verificacoes:
            for linha in self._todas(
                f'SELECT o."{chave}", o."{coluna}" FROM "{tabela}" o WHERE o."{coluna}" IS NOT NULL'
                f' AND NOT EXISTS (SELECT 1 FROM "{referida}" r WHERE r."{coluna_referida}" = o."{coluna}")'
                f' ORDER BY o."{chave}"'
            ):
                resultado.append({"tabela": tabela, "chave": {chave: linha[0]}, "coluna": coluna, "valor": linha[1]})
        for linha in self._todas(
            """
            SELECT pa.CodigoProduto, pa.CodigoAplicacao FROM PRODUTO_APLICACAO pa
             WHERE NOT EXISTS (SELECT 1 FROM PRODUTO p WHERE p.CodigoProduto = pa.CodigoProduto)
             ORDER BY 1, 2
            """
        ):
            resultado.append({
                "tabela": "PRODUTO_APLICACAO",
                "chave": {"CodigoProduto": linha[0], "CodigoAplicacao": linha[1]},
                "coluna": "CodigoProduto",
                "valor": linha[0],
            })
        return resultado

    def ler_valor(self, tabela: str, chave: Mapping[str, int], coluna: str) -> Any:
        """Relê um valor original pela evidência. Usado pela auditoria (invariante I1)."""
        if tabela not in ESQUEMA:
            raise IdentificadorNaoPermitidoError(f"tabela não permitida: {tabela!r}")
        colunas_chave, colunas = ESQUEMA[tabela]
        if coluna not in colunas:
            raise IdentificadorNaoPermitidoError(f"coluna não permitida: {tabela}.{coluna!r}")
        if set(chave) != set(colunas_chave):
            raise IdentificadorNaoPermitidoError(f"chave não permitida para {tabela}: {sorted(chave)!r}")
        condicao = " AND ".join(f'"{nome}" = ?' for nome in colunas_chave)
        linha = self._uma(
            f'SELECT "{coluna}" FROM "{tabela}" WHERE {condicao}',
            tuple(chave[nome] for nome in colunas_chave),
        )
        if linha is None:
            raise RegistroInexistenteError(f"{tabela} {dict(chave)!r} não encontrado")
        return linha[0]

    def somente_leitura(self) -> bool:
        """True quando a conexão recusa escrita (PRAGMA query_only ativo, definido por abrir_somente_leitura)."""
        return self._uma("PRAGMA query_only")[0] == 1
