"""Montagem padronizada das respostas dos serviços."""

from typing import Any

from orcamento_pecas.dominio.alertas import consolidar_alertas, revisao_humana
from orcamento_pecas.dominio.modelos import Alerta, Fonte, ParametroEcoado, Resposta
from orcamento_pecas.dominio.normalizacao import normalizar_texto


def ecoar_texto(valor: str | None) -> ParametroEcoado:
    return ParametroEcoado(original=valor, normalizado=normalizar_texto(valor))


def ecoar_inteiro(valor: int | None) -> ParametroEcoado:
    return ParametroEcoado(original=valor, normalizado=valor)


def montar_resposta(
    consulta: dict[str, ParametroEcoado],
    dados: Any,
    total: int,
    alertas: list[Alerta],
    fonte: Fonte,
    pagina: int | None = None,
    limite: int | None = None,
) -> Resposta:
    consolidados = consolidar_alertas(alertas)
    return Resposta(
        consulta=consulta,
        dados=dados,
        total=total,
        pagina=pagina,
        limite=limite,
        alertas=consolidados,
        revisao_humana=revisao_humana(consolidados),
        fonte=fonte,
    )
