"""Rotas HTTP da API (prefixo /v1)."""

from pydantic import BaseModel


class Erro(BaseModel):
    detail: str


RESPOSTA_404 = {404: {"model": Erro, "description": "Código inexistente na base."}}
