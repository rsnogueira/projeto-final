"""Catálogo de alertas: código, severidade padrão e mensagem (pt-BR)."""

from collections.abc import Iterable
from typing import Any

from orcamento_pecas.dominio.modelos import Alerta, CodigoAlerta, Evidencia, RevisaoHumana, Severidade

__all__ = ["CATALOGO", "CodigoAlerta", "consolidar_alertas", "criar_alerta", "revisao_humana"]

CATALOGO: dict[CodigoAlerta, tuple[Severidade, str]] = {
    CodigoAlerta.ANO_FIM_AUSENTE: ("revisao", "Ano final de fabricação ausente na base; a aplicação foi considerada compatível a partir do ano inicial."),
    CodigoAlerta.FAIXA_ANO_DIVERGENTE: ("revisao", "O texto de FaixaAno diverge das colunas de ano de fabricação."),
    CodigoAlerta.FAIXA_ANO_NAO_INTERPRETADA: ("revisao", "O texto de FaixaAno não está em um formato reconhecido."),
    CodigoAlerta.MOTORIZACAO_SEM_CODIGO: ("revisao", "Motorização sem código de motor."),
    CodigoAlerta.MOTORIZACAO_COMPOSTA: ("revisao", "Motorização com mais de um código de motor."),
    CodigoAlerta.MOTORIZACAO_NAO_INTERPRETADA: ("revisao", "Não foi possível decompor a motorização (cilindrada não encontrada)."),
    CodigoAlerta.COMBUSTIVEL_CONFLITANTE: ("revisao", "O mesmo motor aparece com combustíveis diferentes para o mesmo modelo e ano."),
    CodigoAlerta.PRECO_AUSENTE: ("revisao", "Preço ausente na base para a peça."),
    CodigoAlerta.POSSIVEL_PRODUTO_DUPLICADO: ("revisao", "Produtos com a mesma descrição e o mesmo número-base (possível duplicidade; nada foi mesclado)."),
    CodigoAlerta.VINCULO_ORFAO: ("revisao", "Vínculo peça × aplicação aponta para uma aplicação inexistente."),
    CodigoAlerta.REFERENCIA_INEXISTENTE: ("revisao", "Referência para um registro inexistente em outra tabela."),
    CodigoAlerta.MOTOR_NAO_IDENTIFICADO: ("atencao", "Mais de um motor candidato; são necessárias informações complementares."),
    CodigoAlerta.MULTIPLOS_COMBUSTIVEIS: ("atencao", "Há mais de um combustível para o modelo e ano informados."),
    CodigoAlerta.DESCRICAO_COMPOSTA: ("atencao", "A descrição da aplicação reúne mais de um item (modelos ou versões)."),
    CodigoAlerta.CORRESPONDENCIA_PARCIAL_MODELO: ("atencao", "O modelo foi encontrado só como palavra no meio da descrição (baixa confiança)."),
    CodigoAlerta.MODELO_NAO_ENCONTRADO: ("atencao", "Nenhuma aplicação corresponde ao modelo informado."),
    CodigoAlerta.ANO_FORA_DO_INTERVALO: ("atencao", "O modelo existe, mas nenhuma aplicação cobre o ano informado."),
    CodigoAlerta.FABRICANTE_NAO_ENCONTRADO: ("atencao", "Fabricante não encontrado na base."),
    CodigoAlerta.FABRICANTE_SEM_VEICULOS: ("atencao", "O fabricante existe, mas não tem aplicações (veículos) na base."),
    CodigoAlerta.COMBUSTIVEL_NAO_ENCONTRADO: ("atencao", "O modelo e o ano existem, mas não com o combustível informado."),
    CodigoAlerta.MOTOR_NAO_ENCONTRADO: ("atencao", "Nenhuma aplicação do modelo e ano tem a chave de motor informada."),
    CodigoAlerta.DADO_AUSENTE: ("atencao", "Valor ausente na base."),
}


def criar_alerta(
    codigo: CodigoAlerta,
    evidencias: Iterable[Evidencia] | None = None,
    *,
    severidade: Severidade | None = None,
    **contexto: Any,
) -> Alerta:
    severidade_padrao, mensagem = CATALOGO[codigo]
    return Alerta(
        codigo=codigo,
        severidade=severidade or severidade_padrao,
        mensagem=mensagem,
        evidencias=list(evidencias or []),
        contexto=contexto,
    )


def revisao_humana(alertas: Iterable[Alerta]) -> RevisaoHumana:
    motivos: list[CodigoAlerta] = []
    for alerta in alertas:
        if alerta.severidade == "revisao" and alerta.codigo not in motivos:
            motivos.append(alerta.codigo)
    return RevisaoHumana(necessaria=bool(motivos), motivos=motivos)


def consolidar_alertas(alertas: Iterable[Alerta]) -> list[Alerta]:
    """Um alerta por (código, severidade), na ordem da primeira ocorrência.

    Evidências repetidas são descartadas. No contexto, listas são unidas sem repetição;
    os demais valores ficam com o da primeira ocorrência.
    """
    grupos: dict[tuple[CodigoAlerta, str], Alerta] = {}
    for alerta in alertas:
        chave = (alerta.codigo, alerta.severidade)
        if chave not in grupos:
            grupos[chave] = alerta.model_copy(deep=True)
            continue
        atual = grupos[chave]
        vistas = {e.model_dump_json() for e in atual.evidencias}
        for evidencia in alerta.evidencias:
            if evidencia.model_dump_json() not in vistas:
                atual.evidencias.append(evidencia)
                vistas.add(evidencia.model_dump_json())
        for nome, valor in alerta.contexto.items():
            if nome not in atual.contexto:
                atual.contexto[nome] = valor
            elif isinstance(valor, list) and isinstance(atual.contexto[nome], list):
                atual.contexto[nome] = atual.contexto[nome] + [v for v in valor if v not in atual.contexto[nome]]
    return list(grupos.values())
