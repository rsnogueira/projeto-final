"""Aplicação FastAPI. Uso: `uvicorn --factory orcamento_pecas.api.app:criar_app`."""

from pathlib import Path

from fastapi import FastAPI

from orcamento_pecas import __version__
from orcamento_pecas.api.rotas import catalogos, pecas, saude, veiculos
from orcamento_pecas.config import caminho_banco, rotulo_banco
from orcamento_pecas.dados.conexao import abrir_somente_leitura, sha256_arquivo
from orcamento_pecas.dominio.modelos import Fonte

DESCRICAO = """
API **somente leitura** sobre a base SQLite de aplicações (veículos) e peças de motor.

* Nada é inventado, estimado ou completado: dado ausente é `null`.
* Todo valor vindo da base traz o valor **original**, o **normalizado** e a **evidência** (tabela, chave, coluna e valor original).
* Conflitos, ambiguidades e dados ausentes geram **alertas**. Os de severidade `revisao` ligam `revisao_humana.necessaria`.
* O motor só é considerado identificado quando a base deixa **exatamente um** candidato.
"""

TAGS = [
    {"name": "Saúde", "description": "Estado do serviço e da base."},
    {"name": "Catálogos", "description": "Fabricantes e grupos de produto."},
    {"name": "Veículos", "description": "Aplicações (veículos), motorizações e combustíveis."},
    {"name": "Peças", "description": "Peças por aplicação, por veículo ou motor, e detalhe do produto."},
]


def criar_app(caminho: Path | str | None = None) -> FastAPI:
    banco = caminho_banco(caminho)
    abrir_somente_leitura(banco).close()  # falha na partida se o banco não existir
    app = FastAPI(
        title="Orçamento de peças — API de consulta",
        version=__version__,
        description=DESCRICAO,
        openapi_tags=TAGS,
    )
    app.state.caminho_banco = banco
    app.state.fonte = Fonte(banco=rotulo_banco(banco), sha256=sha256_arquivo(banco))
    for modulo in (saude, catalogos, veiculos, pecas):
        app.include_router(modulo.router, prefix="/v1")
    return app
