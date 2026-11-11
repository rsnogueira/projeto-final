"""Conexão somente leitura com a base SQLite."""

import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import quote


class BancoIndisponivelError(RuntimeError):
    """O arquivo do banco não existe ou não pode ser aberto."""


def abrir_somente_leitura(caminho: Path | str) -> sqlite3.Connection:
    """Abre o banco em modo read-only (`mode=ro`). Nunca cria o arquivo.

    `check_same_thread=False` porque o FastAPI pode usar threads diferentes para a
    dependência e para o endpoint de uma mesma requisição. A conexão não é compartilhada
    entre requisições.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        raise BancoIndisponivelError(f"Banco de dados não encontrado: {caminho}")
    uri = f"file:{quote(caminho.resolve().as_posix(), safe='/:')}?mode=ro"
    try:
        conexao = sqlite3.connect(uri, uri=True, check_same_thread=False)
    except sqlite3.Error as erro:  # pragma: no cover - depende do sistema de arquivos
        raise BancoIndisponivelError(f"Não foi possível abrir {caminho}: {erro}") from erro
    conexao.execute("PRAGMA query_only = ON")  # reforço: além de mode=ro, recusa escrita na própria conexão
    conexao.row_factory = sqlite3.Row
    return conexao


def sha256_arquivo(caminho: Path | str) -> str:
    """SHA-256 do arquivo, em hexadecimal minúsculo."""
    resumo = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()
