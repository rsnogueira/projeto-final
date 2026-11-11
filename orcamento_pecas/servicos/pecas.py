"""Serviço de peças: peças de uma aplicação, peças por veículo ou motor, e detalhe do produto."""

import re
import sqlite3
from collections import defaultdict

from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.alertas import CodigoAlerta, criar_alerta
from orcamento_pecas.dominio.evidencias import evidencia_de, valor_de
from orcamento_pecas.dominio.modelos import Alerta, Evidencia, Fonte, ParametroEcoado, Produto, ProdutoDetalhe, Resposta
from orcamento_pecas.dominio.normalizacao import (
    interpretar_motorizacao,
    normalizar_preco,
    normalizar_texto,
    numero_produto_base,
)
from orcamento_pecas.servicos.comum import ecoar_inteiro, ecoar_texto, montar_resposta
from orcamento_pecas.servicos.veiculos import ServicoVeiculos

CAMPOS_NAO_INTERPRETADOS = ("CodigoSimilar", "CpoAuxProd5", "CpoAuxProd25", "PCs", "NumeroProdutoPesq")


def _inteiro(valor: object) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _contem_palavras(descricao_normalizada: str | None, texto: str | None) -> bool:
    """Todas as palavras de `texto` aparecem como palavras inteiras na descrição."""
    alvo = normalizar_texto(texto)
    if not alvo:
        return True
    descricao = descricao_normalizada or ""
    return all(re.search(rf"(?<!\S){re.escape(p)}(?!\S)", descricao) for p in alvo.split())


def _ordem(produto: Produto) -> tuple[str, str, int]:
    return (produto.grupo.normalizado or "", produto.descricao.normalizado or "", produto.codigo_produto)


def alertas_duplicidade(produtos: list[Produto]) -> list[Alerta]:
    """Mesma descrição normalizada e mesmo número-base (sem `#NAC_`). Nunca mescla: só sinaliza."""
    grupos: dict[tuple[str | None, str], list[Produto]] = defaultdict(list)
    for produto in produtos:
        numero = produto.numero_produto.original
        if isinstance(numero, str):
            grupos[(produto.descricao.normalizado, numero_produto_base(numero))].append(produto)
    duplicados = [g for g in grupos.values() if len(g) > 1]
    if not duplicados:
        return []
    return [criar_alerta(
        CodigoAlerta.POSSIVEL_PRODUTO_DUPLICADO,
        [p.numero_produto.evidencia for g in duplicados for p in g],
        grupos_duplicidade=[[p.codigo_produto for p in g] for g in duplicados],
    )]


def alertas_sem_pecas(produtos: list[Produto], codigos_aplicacao: list[int], grupo: int | None, texto: str | None) -> list[Alerta]:
    """Veículo encontrado, mas nenhuma peça: a ausência afeta o orçamento e exige revisão."""
    if produtos:
        return []
    return [criar_alerta(
        CodigoAlerta.PECAS_NAO_ENCONTRADAS,
        codigos_aplicacao=codigos_aplicacao, grupo=grupo, texto=normalizar_texto(texto),
    )]


class ServicoPecas:
    def __init__(self, repo: Repositorio, veiculos: ServicoVeiculos, fonte: Fonte) -> None:
        self.repo = repo
        self.veiculos = veiculos
        self.fonte = fonte

    def montar_produto(self, linha: sqlite3.Row, codigos_aplicacao: list[int]) -> tuple[Produto, list[Alerta]]:
        codigo = linha["CodigoProduto"]
        chave = {"CodigoProduto": codigo}
        ctx = {"codigos_produto": [codigo]}
        alertas: list[Alerta] = []

        def ausente(valor, campo: str) -> None:
            if valor.normalizado is None:
                alertas.append(criar_alerta(CodigoAlerta.DADO_AUSENTE, [valor.evidencia], campos=[campo], **ctx))

        descricao = valor_de(linha, "PRODUTO", chave, "DescricaoProduto", normalizar_texto(linha["DescricaoProduto"]))
        ausente(descricao, "PRODUTO.DescricaoProduto")
        if linha["DescricaoGrupoProduto"] is None:
            grupo = valor_de(linha, "PRODUTO", chave, "CodigoGrupoProduto", None)
            alertas.append(criar_alerta(CodigoAlerta.REFERENCIA_INEXISTENTE, [grupo.evidencia], **ctx))
        else:
            grupo = valor_de(linha, "GRUPOPRODUTO", {"CodigoGrupoProduto": linha["CodigoGrupoProduto"]},
                             "DescricaoGrupoProduto", normalizar_texto(linha["DescricaoGrupoProduto"]))
            ausente(grupo, "GRUPOPRODUTO.DescricaoGrupoProduto")
        numero_original = linha["NumeroProduto"]
        numero = valor_de(linha, "PRODUTO", chave, "NumeroProduto",
                          numero_original.strip() or None if isinstance(numero_original, str) else None)
        ausente(numero, "PRODUTO.NumeroProduto")
        preco = valor_de(linha, "PRODUTO", chave, "PrecoProduto", normalizar_preco(linha["PrecoProduto"]))
        if preco.normalizado is None:
            alertas.append(criar_alerta(CodigoAlerta.PRECO_AUSENTE, [preco.evidencia], **ctx))
        elif preco.normalizado <= 0:
            alertas.append(criar_alerta(CodigoAlerta.PRECO_SUSPEITO, [preco.evidencia], **ctx))
        qtd = valor_de(linha, "PRODUTO", chave, "QtdEmbalagem", _inteiro(linha["QtdEmbalagem"]))
        ausente(qtd, "PRODUTO.QtdEmbalagem")

        produto = Produto(
            codigo_produto=codigo, descricao=descricao, grupo=grupo, numero_produto=numero,
            preco=preco, qtd_embalagem=qtd, codigos_aplicacao=codigos_aplicacao,
        )
        return produto, alertas

    def _produtos_das_linhas(self, linhas: list[sqlite3.Row], texto: str | None) -> list[Produto]:
        """Agrupa as linhas peça × aplicação por produto, filtra por texto e ordena."""
        por_produto: dict[int, sqlite3.Row] = {}
        aplicacoes: dict[int, list[int]] = defaultdict(list)
        for linha in linhas:
            por_produto.setdefault(linha["CodigoProduto"], linha)
            aplicacoes[linha["CodigoProduto"]].append(linha["CodigoAplicacao"])
        produtos = []
        for codigo, linha in por_produto.items():
            produto, _ = self.montar_produto(linha, sorted(set(aplicacoes[codigo])))
            if _contem_palavras(produto.descricao.normalizado, texto):
                produtos.append(produto)
        return sorted(produtos, key=_ordem)

    def _alertas_dos_produtos(self, produtos: list[Produto], linhas: list[sqlite3.Row]) -> list[Alerta]:
        por_codigo = {linha["CodigoProduto"]: linha for linha in linhas}
        alertas: list[Alerta] = []
        for produto in produtos:
            _, alertas_produto = self.montar_produto(por_codigo[produto.codigo_produto], produto.codigos_aplicacao)
            alertas.extend(alertas_produto)
        return alertas

    def da_aplicacao(self, codigo_aplicacao: int, grupo: int | None = None, texto: str | None = None) -> Resposta | None:
        """Peças de uma aplicação (equivalente filtrado de qry_produto_por_veiculo.sql)."""
        if self.repo.obter_aplicacao(codigo_aplicacao) is None:
            return None
        consulta = {"codigo_aplicacao": ecoar_inteiro(codigo_aplicacao), "grupo": ecoar_inteiro(grupo), "texto": ecoar_texto(texto)}
        linhas = self.repo.listar_pecas_das_aplicacoes([codigo_aplicacao], grupo)
        produtos = self._produtos_das_linhas(linhas, texto)
        alertas = self._alertas_dos_produtos(produtos, linhas) + alertas_duplicidade(produtos)
        alertas += alertas_sem_pecas(produtos, [codigo_aplicacao], grupo, texto)
        return montar_resposta(consulta, produtos, len(produtos), alertas, self.fonte)

    def por_veiculo(
        self,
        modelo: str,
        ano: int,
        chave_motor: str | None = None,
        fabricante: str | None = None,
        combustivel: str | None = None,
        grupo: int | None = None,
        texto: str | None = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> Resposta:
        consulta = self.veiculos.consulta_veiculo(modelo, ano, fabricante, combustivel)
        consulta.update({
            # a chave de motor é comparada exatamente como foi recebida (vem de /v1/veiculos/motorizacoes)
            "chave_motor": ParametroEcoado(original=chave_motor, normalizado=chave_motor),
            "grupo": ecoar_inteiro(grupo),
            "texto": ecoar_texto(texto),
        })
        pares, alertas = self.veiculos.resolver_aplicacoes(modelo, ano, fabricante, combustivel, chave_motor)
        aplicacoes, alertas_aplicacoes = self.veiculos.montar_aplicacoes(pares)
        alertas += alertas_aplicacoes
        alertas += self.veiculos.conflitos_no_contexto(aplicacoes, modelo, ano, fabricante, combustivel, chave_motor)

        primeira_por_chave: dict[str, Evidencia] = {}
        for linha, _ in pares:
            chave = interpretar_motorizacao(linha["Motorizacao"]).chave
            primeira_por_chave.setdefault(chave, evidencia_de(linha, "APLICACAO", {"CodigoAplicacao": linha["CodigoAplicacao"]}, "Motorizacao"))
        if len(primeira_por_chave) > 1:
            alertas.append(criar_alerta(
                CodigoAlerta.MOTOR_NAO_IDENTIFICADO,
                [primeira_por_chave[c] for c in sorted(primeira_por_chave)],
                severidade="revisao",
                chaves_candidatas=sorted(primeira_por_chave),
            ))

        linhas = self.repo.listar_pecas_das_aplicacoes([linha["CodigoAplicacao"] for linha, _ in pares], grupo)
        produtos = self._produtos_das_linhas(linhas, texto)
        inicio = (pagina - 1) * limite
        pagina_produtos = produtos[inicio:inicio + limite]
        alertas += self._alertas_dos_produtos(pagina_produtos, linhas) + alertas_duplicidade(produtos)
        if pares:
            alertas += alertas_sem_pecas(produtos, sorted(linha["CodigoAplicacao"] for linha, _ in pares), grupo, texto)
        return montar_resposta(consulta, pagina_produtos, len(produtos), alertas, self.fonte, pagina, limite)

    def obter(self, codigo_produto: int) -> Resposta | None:
        linha = self.repo.obter_produto(codigo_produto)
        if linha is None:
            return None
        produto, alertas = self.montar_produto(linha, self.repo.aplicacoes_do_produto(codigo_produto))
        orfaos = self.repo.vinculos_orfaos_do_produto(codigo_produto)
        if orfaos:
            alertas.append(criar_alerta(
                CodigoAlerta.VINCULO_ORFAO,
                [
                    Evidencia(tabela="PRODUTO_APLICACAO", chave={"CodigoProduto": codigo_produto, "CodigoAplicacao": c},
                              coluna="CodigoAplicacao", valor_original=c)
                    for c in orfaos
                ],
                codigos_produto=[codigo_produto],
                codigos_aplicacao_inexistentes=orfaos,
            ))
        detalhe = ProdutoDetalhe(
            **{nome: getattr(produto, nome) for nome in Produto.model_fields},
            vinculos_orfaos=orfaos,
            campos_nao_interpretados={c: linha[c] for c in CAMPOS_NAO_INTERPRETADOS},
        )
        return montar_resposta({"codigo_produto": ecoar_inteiro(codigo_produto)}, detalhe, 1, alertas, self.fonte)
