"""Verificações da auditoria.

* `auditar_base`: achados de QUALIDADE DE DADOS (viram alertas, não falhas).
* `auditar_resposta`: INVARIANTES que toda resposta precisa cumprir (violação = falha):
  I1 evidência relida na base confere com o original; I2 todo normalizado null tem alerta citando a
  evidência; I3 revisão humana coerente com os alertas; I4 `identificado`/`unico` coerentes;
  I5 aplicações devolvidas satisfazem os filtros; I6 listagens sem repetição e com total coerente.
"""

from collections import defaultdict
from collections.abc import Iterator
from itertools import combinations
from typing import Any

from pydantic import BaseModel

from orcamento_pecas.dados.repositorio import IdentificadorNaoPermitidoError, RegistroInexistenteError, Repositorio
from orcamento_pecas.dominio.alertas import CodigoAlerta, consolidar_alertas, criar_alerta, revisao_humana
from orcamento_pecas.dominio.modelos import (
    Alerta,
    Aplicacao,
    DadosCombustiveis,
    DadosMotorizacoes,
    Evidencia,
    Produto,
    Resposta,
    ValorRastreado,
)
from orcamento_pecas.dominio.normalizacao import ano_compativel, corresponde_modelo, normalizar_texto
from orcamento_pecas.servicos.pecas import ServicoPecas, alertas_duplicidade
from orcamento_pecas.servicos.veiculos import ServicoVeiculos


class Falha(BaseModel):
    invariante: str
    consulta: str = ""
    detalhe: str
    evidencia: Evidencia | None = None


def valores_rastreados(objeto: Any, caminho: str = "dados") -> Iterator[tuple[str, ValorRastreado]]:
    """Percorre a estrutura e devolve (caminho do campo, valor rastreado)."""
    if isinstance(objeto, ValorRastreado):
        yield caminho, objeto
    elif isinstance(objeto, BaseModel):
        for nome in type(objeto).model_fields:
            yield from valores_rastreados(getattr(objeto, nome), f"{caminho}.{nome}")
    elif isinstance(objeto, list):
        for indice, item in enumerate(objeto):
            yield from valores_rastreados(item, f"{caminho}[{indice}]")
    elif isinstance(objeto, dict):
        for chave, valor in objeto.items():
            yield from valores_rastreados(valor, f"{caminho}.{chave}")


def _mesmo_valor(a: object, b: object) -> bool:
    return type(a) is type(b) and a == b


def _aplicacoes(dados: Any) -> list[Aplicacao]:
    if isinstance(dados, (DadosMotorizacoes, DadosCombustiveis)):
        return dados.aplicacoes
    if isinstance(dados, Aplicacao):
        return [dados]
    if isinstance(dados, list):
        return [item for item in dados if isinstance(item, Aplicacao)]
    return []


def auditar_resposta(resposta: Resposta, repo: Repositorio, filtros: dict[str, Any] | None = None, consulta: str = "") -> list[Falha]:
    falhas: list[Falha] = []

    def falha(invariante: str, detalhe: str, evidencia: Evidencia | None = None) -> None:
        falhas.append(Falha(invariante=invariante, consulta=consulta, detalhe=detalhe, evidencia=evidencia))

    pares = list(valores_rastreados(resposta.dados))

    # I1: a evidência relida na base confere com o original (valores e evidências citadas nos alertas)
    relidos: dict[str, tuple[bool, object]] = {}

    def reler(evidencia: Evidencia) -> tuple[bool, object]:
        chave = evidencia.model_dump_json()
        if chave not in relidos:
            try:
                relidos[chave] = (True, repo.ler_valor(evidencia.tabela, evidencia.chave, evidencia.coluna))
            except (RegistroInexistenteError, IdentificadorNaoPermitidoError) as erro:
                relidos[chave] = (False, str(erro))
        return relidos[chave]

    for caminho, valor in pares:
        evidencia = valor.evidencia
        if not _mesmo_valor(evidencia.valor_original, valor.original):
            falha("I1", f"{caminho}: original {valor.original!r} difere da evidência {evidencia.valor_original!r}", evidencia)
        encontrado, atual = reler(evidencia)
        if not encontrado:
            falha("I1", f"{caminho}: {atual}", evidencia)
        elif not _mesmo_valor(atual, valor.original):
            falha("I1", f"{caminho}: base {atual!r} ≠ resposta {valor.original!r}", evidencia)
    for alerta in resposta.alertas:
        for evidencia in alerta.evidencias:
            encontrado, atual = reler(evidencia)
            if not encontrado:
                falha("I1", f"alerta {alerta.codigo.value}: {atual}", evidencia)
            elif not _mesmo_valor(atual, evidencia.valor_original):
                falha("I1", f"alerta {alerta.codigo.value}: base {atual!r} ≠ evidência {evidencia.valor_original!r}", evidencia)

    # I2: normalizado null precisa de alerta citando a evidência
    citadas = {e.model_dump_json() for alerta in resposta.alertas for e in alerta.evidencias}
    for caminho, valor in pares:
        if valor.normalizado is None and valor.evidencia.model_dump_json() not in citadas:
            falha("I2", f"{caminho}: valor ausente sem alerta", valor.evidencia)

    # I3: revisão humana coerente com os alertas
    if resposta.revisao_humana != revisao_humana(resposta.alertas):
        falha("I3", f"revisao_humana {resposta.revisao_humana.model_dump()} incoerente com os alertas")

    # I4: identificado / unico
    dados = resposta.dados
    if isinstance(dados, DadosMotorizacoes):
        esperado = len(dados.candidatos) == 1
        coerente_motor = (dados.motor_identificado == dados.candidatos[0]) if esperado else dados.motor_identificado is None
        if dados.identificado != esperado or not coerente_motor:
            falha("I4", f"identificado={dados.identificado} com {len(dados.candidatos)} candidato(s)")
    if isinstance(dados, DadosCombustiveis) and dados.unico != (len(dados.combustiveis) == 1):
        falha("I4", f"unico={dados.unico} com {len(dados.combustiveis)} combustível(is)")

    # I5: aplicações satisfazem os filtros (rechecado a partir dos valores originais)
    filtros = filtros or {}
    modelo, ano = filtros.get("modelo"), filtros.get("ano")
    combustivel = normalizar_texto(filtros.get("combustivel"))
    for aplicacao in _aplicacoes(dados):
        if modelo and corresponde_modelo(aplicacao.descricao.original, modelo) is None:
            falha("I5", f"aplicação {aplicacao.codigo_aplicacao} não corresponde ao modelo {modelo!r}", aplicacao.descricao.evidencia)
        inicio, fim = aplicacao.ano_inicio.normalizado, aplicacao.ano_fim.normalizado
        if ano is not None and (inicio is None or not ano_compativel(ano, inicio, fim)):
            falha("I5", f"aplicação {aplicacao.codigo_aplicacao} não cobre o ano {ano}", aplicacao.ano_inicio.evidencia)
        if combustivel and aplicacao.combustivel.normalizado != combustivel:
            falha("I5", f"aplicação {aplicacao.codigo_aplicacao} não é {combustivel}", aplicacao.combustivel.evidencia)

    # I6: listagens sem repetição e com total coerente
    if isinstance(dados, list):
        codigos = [
            item.codigo_produto if isinstance(item, Produto) else getattr(item, "codigo_aplicacao", id(item))
            for item in dados
        ]
        if len(codigos) != len(set(codigos)):
            falha("I6", "item repetido na listagem")
        if resposta.total < len(dados) or (resposta.limite is not None and len(dados) > resposta.limite):
            falha("I6", f"total={resposta.total}, limite={resposta.limite}, itens={len(dados)}")
        sem_paginacao = resposta.limite is None
        primeira_pagina_completa = resposta.pagina == 1 and resposta.limite is not None and resposta.total <= resposta.limite
        if (sem_paginacao or primeira_pagina_completa) and resposta.total != len(dados):
            falha("I6", f"total={resposta.total} difere da quantidade de itens ({len(dados)})")
    return falhas


def _sobrepoe(a: Aplicacao, b: Aplicacao) -> bool:
    ai, bi = a.ano_inicio.normalizado, b.ano_inicio.normalizado
    if ai is None or bi is None:
        return False
    af, bf = a.ano_fim.normalizado, b.ano_fim.normalizado
    return ai <= (bf if bf is not None else 9999) and bi <= (af if af is not None else 9999)


def conflitos_combustivel_base(aplicacoes: list[Aplicacao]) -> list[Alerta]:
    """Mesmo modelo-base e mesma chave de motor, com anos sobrepostos e combustíveis diferentes."""
    grupos: dict[tuple[str, str], list[Aplicacao]] = defaultdict(list)
    for aplicacao in aplicacoes:
        for modelo in aplicacao.modelos_base_derivados:
            grupos[(modelo, aplicacao.motorizacao.normalizado.chave)].append(aplicacao)
    alertas = []
    for (modelo, chave), grupo in sorted(grupos.items()):
        envolvidas: dict[int, Aplicacao] = {}
        for a, b in combinations(grupo, 2):
            ca, cb = a.combustivel.normalizado, b.combustivel.normalizado
            if ca and cb and ca != cb and _sobrepoe(a, b):
                envolvidas[a.codigo_aplicacao] = a
                envolvidas[b.codigo_aplicacao] = b
        if envolvidas:
            ordenadas = [envolvidas[c] for c in sorted(envolvidas)]
            alertas.append(criar_alerta(
                CodigoAlerta.COMBUSTIVEL_CONFLITANTE,
                [a.combustivel.evidencia for a in ordenadas],
                modelos=[modelo],
                chaves_motor=[chave],
                combustiveis=sorted({a.combustivel.normalizado for a in ordenadas}),
                codigos_aplicacao=sorted(envolvidas),
            ))
    return alertas


def auditar_base(repo: Repositorio, veiculos: ServicoVeiculos, pecas: ServicoPecas) -> list[Alerta]:
    alertas: list[Alerta] = []
    aplicacoes: list[Aplicacao] = []
    for linha in repo.listar_aplicacoes(None):
        aplicacao, alertas_aplicacao = veiculos.montar_aplicacao(linha)
        aplicacoes.append(aplicacao)
        alertas.extend(alertas_aplicacao)
    alertas.extend(conflitos_combustivel_base(aplicacoes))

    orfaos = repo.vinculos_orfaos()
    if orfaos:
        alertas.append(criar_alerta(
            CodigoAlerta.VINCULO_ORFAO,
            [
                Evidencia(tabela="PRODUTO_APLICACAO", chave={"CodigoProduto": o["CodigoProduto"], "CodigoAplicacao": o["CodigoAplicacao"]},
                          coluna="CodigoAplicacao", valor_original=o["CodigoAplicacao"])
                for o in orfaos
            ],
            codigos_produto=sorted({o["CodigoProduto"] for o in orfaos}),
            codigos_aplicacao_inexistentes=sorted({o["CodigoAplicacao"] for o in orfaos}),
        ))
    for referencia in repo.referencias_inexistentes():
        alertas.append(criar_alerta(
            CodigoAlerta.REFERENCIA_INEXISTENTE,
            [Evidencia(tabela=referencia["tabela"], chave=referencia["chave"], coluna=referencia["coluna"], valor_original=referencia["valor"])],
        ))

    produtos: list[Produto] = []
    for codigo in repo.listar_produtos_vinculados():
        produto, alertas_produto = pecas.montar_produto(repo.obter_produto(codigo), repo.aplicacoes_do_produto(codigo))
        produtos.append(produto)
        alertas.extend(alertas_produto)
    alertas.extend(alertas_duplicidade(produtos))
    return consolidar_alertas(alertas)
