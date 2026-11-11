"""Amostra determinística (com semente) e estratificada para revisão manual."""

import random
from typing import Literal

from pydantic import BaseModel

from orcamento_pecas.dados.repositorio import ESQUEMA, IdentificadorNaoPermitidoError
from orcamento_pecas.dominio.modelos import Evidencia, ValorPrimitivo


class ItemPopulacao(BaseModel):
    consulta: str
    campo: str
    valor_exibido: str | None
    original: ValorPrimitivo
    evidencia: Evidencia
    com_alerta_revisao: bool


class ItemAmostra(ItemPopulacao):
    id: str
    estrato: Literal["com_alerta", "limpo"]
    sql_conferencia: str


def sql_conferencia(evidencia: Evidencia) -> str:
    """SQL pronto para o revisor conferir o valor original (identificadores só da lista fixa; chaves inteiras)."""
    colunas_chave, colunas = ESQUEMA[evidencia.tabela]
    if evidencia.coluna not in colunas or set(evidencia.chave) != set(colunas_chave):
        raise IdentificadorNaoPermitidoError(f"evidência fora do esquema: {evidencia}")
    condicoes = " AND ".join(f'"{nome}" = {int(evidencia.chave[nome])}' for nome in colunas_chave)
    return f'SELECT "{evidencia.coluna}" FROM "{evidencia.tabela}" WHERE {condicoes};'


def sortear_amostra(itens: list[ItemPopulacao], tamanho: int, semente: int) -> list[ItemAmostra]:
    """Metade com alerta de revisão e metade limpa; se um estrato não tiver itens suficientes, o outro completa."""
    sorteador = random.Random(semente)
    com_alerta = [i for i in itens if i.com_alerta_revisao]
    limpos = [i for i in itens if not i.com_alerta_revisao]
    n_com = min(len(com_alerta), (tamanho + 1) // 2)
    n_limpos = min(len(limpos), tamanho - n_com)
    n_com = min(len(com_alerta), tamanho - n_limpos)
    escolhidos = [("com_alerta", i) for i in sorteador.sample(com_alerta, n_com)]
    escolhidos += [("limpo", i) for i in sorteador.sample(limpos, n_limpos)]
    largura = max(2, len(str(len(escolhidos))))
    return [
        ItemAmostra(**item.model_dump(), id=f"A{n:0{largura}d}", estrato=estrato, sql_conferencia=sql_conferencia(item.evidencia))
        for n, (estrato, item) in enumerate(escolhidos, 1)
    ]
