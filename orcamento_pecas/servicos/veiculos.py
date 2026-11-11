"""Serviço de veículos (aplicações): busca, detalhe, motorizações e combustíveis."""

import sqlite3
from collections import defaultdict
from dataclasses import asdict

from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.alertas import CodigoAlerta, criar_alerta
from orcamento_pecas.dominio.evidencias import evidencia_de, valor_de
from orcamento_pecas.dominio.modelos import (
    Alerta,
    Aplicacao,
    CandidatoMotor,
    Correspondencia,
    DadosCombustiveis,
    DadosMotorizacoes,
    FaixaAnoNormalizada,
    Fonte,
    ItemCombustivel,
    ParametroEcoado,
    Resposta,
)
from orcamento_pecas.dominio.normalizacao import (
    ano_compativel,
    corresponde_modelo,
    faixa_diverge_das_colunas,
    interpretar_faixa_ano,
    interpretar_motorizacao,
    modelos_base,
    normalizar_ano_fim,
    normalizar_texto,
    segmentos_descricao,
)
from orcamento_pecas.servicos.comum import ecoar_inteiro, ecoar_texto, montar_resposta

ParAplicacao = tuple[sqlite3.Row, Correspondencia | None]


def _inteiro(valor: object) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _ordem_com_nulos_no_fim(valor: str | None) -> tuple[bool, str]:
    return (valor is None, valor or "")


def alertas_conflito_combustivel(aplicacoes: list[Aplicacao]) -> list[Alerta]:
    """Mesma chave de motor com combustíveis diferentes dentro do conjunto consultado."""
    por_chave: dict[str, list[Aplicacao]] = defaultdict(list)
    for aplicacao in aplicacoes:
        por_chave[aplicacao.motorizacao.normalizado.chave].append(aplicacao)
    alertas = []
    for chave in sorted(por_chave):
        grupo = por_chave[chave]
        combustiveis = sorted({a.combustivel.normalizado for a in grupo if a.combustivel.normalizado})
        if len(combustiveis) > 1:
            alertas.append(criar_alerta(
                CodigoAlerta.COMBUSTIVEL_CONFLITANTE,
                [a.combustivel.evidencia for a in grupo],
                chaves_motor=[chave],
                combustiveis=combustiveis,
                codigos_aplicacao=[a.codigo_aplicacao for a in grupo],
            ))
    return alertas


class ServicoVeiculos:
    def __init__(self, repo: Repositorio, fonte: Fonte) -> None:
        self.repo = repo
        self.fonte = fonte

    # --- montagem de uma aplicação -------------------------------------------------

    def montar_aplicacao(self, linha: sqlite3.Row, correspondencia: Correspondencia | None = None) -> tuple[Aplicacao, list[Alerta]]:
        codigo = linha["CodigoAplicacao"]
        chave = {"CodigoAplicacao": codigo}
        ctx = {"codigos_aplicacao": [codigo]}
        alertas: list[Alerta] = []

        def ausente(valor, campo: str) -> None:
            if valor.normalizado is None:
                alertas.append(criar_alerta(CodigoAlerta.DADO_AUSENTE, [valor.evidencia], campos=[campo], **ctx))

        def referencia(tabela_ref, coluna_codigo: str, coluna_descricao: str):
            if linha[coluna_descricao] is None:
                valor = valor_de(linha, "APLICACAO", chave, coluna_codigo, None)
                alertas.append(criar_alerta(CodigoAlerta.REFERENCIA_INEXISTENTE, [valor.evidencia], **ctx))
                return valor
            valor = valor_de(linha, tabela_ref, {coluna_codigo: linha[coluna_codigo]}, coluna_descricao,
                             normalizar_texto(linha[coluna_descricao]))
            ausente(valor, f"{tabela_ref}.{coluna_descricao}")
            return valor

        fabricante = referencia("FABRICANTE", "CodigoFabricante", "DescricaoFabricante")
        tipo = referencia("TIPOAPLICACAO", "CodigoTipoAplicacao", "DescricaoTipoAplicacao")

        descricao = valor_de(linha, "APLICACAO", chave, "DescricaoAplicacao", normalizar_texto(linha["DescricaoAplicacao"]))
        ausente(descricao, "APLICACAO.DescricaoAplicacao")
        if len(segmentos_descricao(linha["DescricaoAplicacao"])) > 1:
            alertas.append(criar_alerta(CodigoAlerta.DESCRICAO_COMPOSTA, [descricao.evidencia], **ctx))
        if correspondencia is not None and correspondencia.confianca == "baixa":
            alertas.append(criar_alerta(CodigoAlerta.CORRESPONDENCIA_PARCIAL_MODELO, [descricao.evidencia], **ctx))

        faixa_interpretada = interpretar_faixa_ano(linha["FaixaAno"])
        faixa = valor_de(linha, "APLICACAO", chave, "FaixaAno", FaixaAnoNormalizada(**asdict(faixa_interpretada)))
        ano_inicio = valor_de(linha, "APLICACAO", chave, "AnoInicioFabricacao", _inteiro(linha["AnoInicioFabricacao"]))
        ausente(ano_inicio, "APLICACAO.AnoInicioFabricacao")
        ano_fim = valor_de(linha, "APLICACAO", chave, "AnoFimFabricacao", normalizar_ano_fim(linha["AnoFimFabricacao"]))
        if ano_fim.normalizado is None:
            alertas.append(criar_alerta(CodigoAlerta.ANO_FIM_AUSENTE, [ano_fim.evidencia], **ctx))
        if not faixa_interpretada.interpretada:
            alertas.append(criar_alerta(CodigoAlerta.FAIXA_ANO_NAO_INTERPRETADA, [faixa.evidencia], **ctx))
        elif faixa_diverge_das_colunas(faixa_interpretada, ano_inicio.normalizado, ano_fim.normalizado):
            alertas.append(criar_alerta(
                CodigoAlerta.FAIXA_ANO_DIVERGENTE, [faixa.evidencia, ano_inicio.evidencia, ano_fim.evidencia], **ctx
            ))

        motor = interpretar_motorizacao(linha["Motorizacao"])
        motorizacao = valor_de(linha, "APLICACAO", chave, "Motorizacao", motor)
        if not motor.interpretada:
            alertas.append(criar_alerta(CodigoAlerta.MOTORIZACAO_NAO_INTERPRETADA, [motorizacao.evidencia], **ctx))
        elif motor.sem_codigo:
            alertas.append(criar_alerta(CodigoAlerta.MOTORIZACAO_SEM_CODIGO, [motorizacao.evidencia], **ctx))
        if motor.composta:
            alertas.append(criar_alerta(CodigoAlerta.MOTORIZACAO_COMPOSTA, [motorizacao.evidencia], **ctx))

        combustivel = valor_de(linha, "APLICACAO", chave, "Combustivel", normalizar_texto(linha["Combustivel"]))
        ausente(combustivel, "APLICACAO.Combustivel")

        aplicacao = Aplicacao(
            codigo_aplicacao=codigo,
            fabricante=fabricante,
            tipo_aplicacao=tipo,
            descricao=descricao,
            modelos_base_derivados=modelos_base(linha["DescricaoAplicacao"]),
            faixa_ano=faixa,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            motorizacao=motorizacao,
            combustivel=combustivel,
            correspondencia=correspondencia,
        )
        return aplicacao, alertas

    def montar_aplicacoes(self, pares: list[ParAplicacao]) -> tuple[list[Aplicacao], list[Alerta]]:
        aplicacoes, alertas = [], []
        for linha, correspondencia in pares:
            aplicacao, alertas_aplicacao = self.montar_aplicacao(linha, correspondencia)
            aplicacoes.append(aplicacao)
            alertas.extend(alertas_aplicacao)
        return aplicacoes, alertas

    # --- resolução por atributos do veículo ----------------------------------------

    def _resolver_fabricante(self, fabricante: str | None) -> tuple[int | None, list[Alerta], bool]:
        alvo = normalizar_texto(fabricante)
        if not alvo:
            return None, [], False
        linhas = self.repo.listar_fabricantes()
        for linha in linhas:
            if normalizar_texto(linha["DescricaoFabricante"]) == alvo:
                if linha["QuantidadeAplicacoes"] == 0:
                    evidencia = evidencia_de(linha, "FABRICANTE", {"CodigoFabricante": linha["CodigoFabricante"]}, "DescricaoFabricante")
                    return linha["CodigoFabricante"], [criar_alerta(CodigoAlerta.FABRICANTE_SEM_VEICULOS, [evidencia], fabricante=alvo)], True
                return linha["CodigoFabricante"], [], False
        disponiveis = sorted(n for n in (normalizar_texto(l["DescricaoFabricante"]) for l in linhas) if n)
        return None, [criar_alerta(CodigoAlerta.FABRICANTE_NAO_ENCONTRADO, fabricante=alvo, fabricantes_disponiveis=disponiveis)], True

    def resolver_aplicacoes(
        self,
        modelo: str | None = None,
        ano: int | None = None,
        fabricante: str | None = None,
        combustivel: str | None = None,
        chave_motor: str | None = None,
    ) -> tuple[list[ParAplicacao], list[Alerta]]:
        """Filtra as aplicações por fabricante, modelo, ano, combustível e chave de motor, nessa ordem.

        Quando um filtro zera o resultado, devolve o alerta que explica o motivo (com os valores disponíveis).
        """
        codigo_fabricante, alertas, parar = self._resolver_fabricante(fabricante)
        if parar:
            return [], alertas
        linhas = self.repo.listar_aplicacoes(codigo_fabricante)
        pares: list[ParAplicacao] = [(linha, None) for linha in linhas]

        modelo_normal = normalizar_texto(modelo)
        if modelo_normal:
            pares = [(l, c) for l in linhas if (c := corresponde_modelo(l["DescricaoAplicacao"], modelo))]
            if not pares:
                disponiveis = sorted({m for l in linhas for m in modelos_base(l["DescricaoAplicacao"])})
                return [], [criar_alerta(CodigoAlerta.MODELO_NAO_ENCONTRADO, modelo=modelo_normal, modelos_disponiveis=disponiveis)]

        if ano is not None:
            compativeis = [
                (l, c) for l, c in pares
                if (inicio := _inteiro(l["AnoInicioFabricacao"])) is not None
                and ano_compativel(ano, inicio, normalizar_ano_fim(l["AnoFimFabricacao"]))
            ]
            if not compativeis:
                faixas = sorted({
                    f"{l['AnoInicioFabricacao']}-{normalizar_ano_fim(l['AnoFimFabricacao']) or ''}" for l, _ in pares
                })
                return [], [criar_alerta(CodigoAlerta.ANO_FORA_DO_INTERVALO, ano=ano, faixas_disponiveis=faixas)]
            pares = compativeis

        combustivel_normal = normalizar_texto(combustivel)
        if combustivel_normal:
            filtrados = [(l, c) for l, c in pares if normalizar_texto(l["Combustivel"]) == combustivel_normal]
            if not filtrados:
                disponiveis = sorted({n for l, _ in pares if (n := normalizar_texto(l["Combustivel"]))})
                return [], [criar_alerta(
                    CodigoAlerta.COMBUSTIVEL_NAO_ENCONTRADO, combustivel=combustivel_normal, combustiveis_disponiveis=disponiveis
                )]
            pares = filtrados

        if chave_motor:
            filtrados = [(l, c) for l, c in pares if interpretar_motorizacao(l["Motorizacao"]).chave == chave_motor]
            if not filtrados:
                disponiveis = sorted({interpretar_motorizacao(l["Motorizacao"]).chave for l, _ in pares})
                return [], [criar_alerta(CodigoAlerta.MOTOR_NAO_ENCONTRADO, chave_motor=chave_motor, chaves_disponiveis=disponiveis)]
            pares = filtrados
        return pares, alertas

    def conflitos_no_contexto(
        self,
        aplicacoes: list[Aplicacao],
        modelo: str | None,
        ano: int | None,
        fabricante: str | None,
        combustivel: str | None,
        chave_motor: str | None = None,
    ) -> list[Alerta]:
        """Conflitos de combustível calculados ANTES do filtro de combustível.

        O combustível informado pelo comprador não pode resolver em silêncio um conflito da base: o conflito
        é procurado no conjunto sem esse filtro, restrito às chaves de motor que sobraram depois dele.
        """
        if not normalizar_texto(combustivel):
            return alertas_conflito_combustivel(aplicacoes)
        chaves = {a.motorizacao.normalizado.chave for a in aplicacoes}
        pares, _ = self.resolver_aplicacoes(modelo, ano, fabricante, None, chave_motor)
        contexto = [self.montar_aplicacao(linha, c)[0] for linha, c in pares]
        return alertas_conflito_combustivel([a for a in contexto if a.motorizacao.normalizado.chave in chaves])

    @staticmethod
    def consulta_veiculo(modelo, ano, fabricante, combustivel) -> dict[str, ParametroEcoado]:
        return {
            "modelo": ecoar_texto(modelo),
            "ano": ecoar_inteiro(ano),
            "fabricante": ecoar_texto(fabricante),
            "combustivel": ecoar_texto(combustivel),
        }

    # --- endpoints -------------------------------------------------------------------

    def motorizacoes(self, modelo: str, ano: int, fabricante: str | None = None, combustivel: str | None = None) -> Resposta:
        consulta = self.consulta_veiculo(modelo, ano, fabricante, combustivel)
        pares, alertas = self.resolver_aplicacoes(modelo, ano, fabricante, combustivel)
        aplicacoes, alertas_aplicacoes = self.montar_aplicacoes(pares)
        alertas += alertas_aplicacoes
        candidatos = agrupar_candidatos(aplicacoes)
        identificado = len(candidatos) == 1
        if len(candidatos) > 1:
            alertas.append(criar_alerta(
                CodigoAlerta.MOTOR_NAO_IDENTIFICADO,
                [c.motorizacoes_originais[0].evidencia for c in candidatos],
                chaves_candidatas=[c.chave_motor for c in candidatos],
            ))
        alertas += self.conflitos_no_contexto(aplicacoes, modelo, ano, fabricante, combustivel)
        dados = DadosMotorizacoes(
            identificado=identificado,
            motor_identificado=candidatos[0] if identificado else None,
            candidatos=candidatos,
            atributos_distintivos=atributos_distintivos(candidatos, aplicacoes) if len(candidatos) > 1 else {},
            aplicacoes=aplicacoes,
        )
        return montar_resposta(consulta, dados, len(candidatos), alertas, self.fonte)

    def combustiveis(self, modelo: str, ano: int, fabricante: str | None = None) -> Resposta:
        consulta = self.consulta_veiculo(modelo, ano, fabricante, None)
        del consulta["combustivel"]
        pares, alertas = self.resolver_aplicacoes(modelo, ano, fabricante)
        aplicacoes, alertas_aplicacoes = self.montar_aplicacoes(pares)
        alertas += alertas_aplicacoes
        grupos: dict[str | None, list[Aplicacao]] = defaultdict(list)
        for aplicacao in aplicacoes:
            grupos[aplicacao.combustivel.normalizado].append(aplicacao)
        itens = [
            ItemCombustivel(
                combustivel=nome,
                valores=[a.combustivel for a in grupos[nome]],
                codigos_aplicacao=[a.codigo_aplicacao for a in grupos[nome]],
            )
            for nome in sorted(grupos, key=_ordem_com_nulos_no_fim)
        ]
        if len(itens) > 1:
            alertas.append(criar_alerta(
                CodigoAlerta.MULTIPLOS_COMBUSTIVEIS,
                [item.valores[0].evidencia for item in itens],
                combustiveis=[item.combustivel for item in itens],
            ))
        alertas += alertas_conflito_combustivel(aplicacoes)
        dados = DadosCombustiveis(unico=len(itens) == 1, combustiveis=itens, aplicacoes=aplicacoes)
        return montar_resposta(consulta, dados, len(itens), alertas, self.fonte)

    def buscar(
        self,
        modelo: str | None = None,
        ano: int | None = None,
        fabricante: str | None = None,
        combustivel: str | None = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> Resposta:
        consulta = self.consulta_veiculo(modelo, ano, fabricante, combustivel)
        pares, alertas = self.resolver_aplicacoes(modelo, ano, fabricante, combustivel)
        inicio = (pagina - 1) * limite
        aplicacoes, alertas_aplicacoes = self.montar_aplicacoes(pares[inicio:inicio + limite])
        return montar_resposta(consulta, aplicacoes, len(pares), alertas + alertas_aplicacoes, self.fonte, pagina, limite)

    def obter(self, codigo_aplicacao: int) -> Resposta | None:
        linha = self.repo.obter_aplicacao(codigo_aplicacao)
        if linha is None:
            return None
        aplicacao, alertas = self.montar_aplicacao(linha)
        return montar_resposta({"codigo_aplicacao": ecoar_inteiro(codigo_aplicacao)}, aplicacao, 1, alertas, self.fonte)


def agrupar_candidatos(aplicacoes: list[Aplicacao]) -> list[CandidatoMotor]:
    grupos: dict[str, list[Aplicacao]] = defaultdict(list)
    for aplicacao in aplicacoes:
        grupos[aplicacao.motorizacao.normalizado.chave].append(aplicacao)
    return [
        CandidatoMotor(
            chave_motor=chave,
            motor=grupos[chave][0].motorizacao.normalizado,
            motorizacoes_originais=[a.motorizacao for a in grupos[chave]],
            combustiveis=sorted({a.combustivel.normalizado for a in grupos[chave] if a.combustivel.normalizado}),
            codigos_aplicacao=sorted(a.codigo_aplicacao for a in grupos[chave]),
        )
        for chave in sorted(grupos)
    ]


def atributos_distintivos(candidatos: list[CandidatoMotor], aplicacoes: list[Aplicacao]) -> dict[str, list[str | None]]:
    """Só os atributos que variam entre os candidatos. A API não sugere perguntas: isso é papel da skill."""
    extratores = {
        "codigos": lambda m: "+".join(m.codigos) or None,
        "cilindrada_l": lambda m: m.cilindrada_l,
        "valvulas": lambda m: str(m.valvulas) if m.valvulas is not None else None,
        "cilindros": lambda m: m.cilindros,
        "comando": lambda m: m.comando,
    }
    resultado: dict[str, list[str | None]] = {}
    for nome, extrair in extratores.items():
        valores = {extrair(c.motor) for c in candidatos}
        if len(valores) > 1:
            resultado[nome] = sorted(valores, key=_ordem_com_nulos_no_fim)
    combustiveis = {combustivel for c in candidatos for combustivel in c.combustiveis}
    if len(combustiveis) > 1:
        resultado["combustivel"] = sorted(combustiveis)
    versoes = {a.descricao.normalizado for a in aplicacoes}
    if len(versoes) > 1:
        resultado["versoes"] = sorted(versoes, key=_ordem_com_nulos_no_fim)
    return resultado


__all__ = ["ServicoVeiculos", "agrupar_candidatos", "alertas_conflito_combustivel", "atributos_distintivos"]
