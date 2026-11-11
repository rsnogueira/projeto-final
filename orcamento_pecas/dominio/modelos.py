"""Modelos de dados (Pydantic) compartilhados por serviços, API e auditoria.

Regra geral: todo valor vindo da base é um `ValorRastreado`, com o valor original, o
normalizado (ou null) e a evidência (tabela, chave, coluna e valor original).
"""

from decimal import Decimal
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

TabelaBase = Literal["APLICACAO", "FABRICANTE", "GRUPOPRODUTO", "PRODUTO", "PRODUTO_APLICACAO", "TIPOAPLICACAO"]
Severidade = Literal["info", "atencao", "revisao"]
ValorPrimitivo = str | int | float | None

# Exemplos do Swagger: valores REAIS da base (2026-11-10), nunca inventados.
_EXEMPLO_EVIDENCIA = {"tabela": "APLICACAO", "chave": {"CodigoAplicacao": 31393}, "coluna": "AnoFimFabricacao", "valor_original": ""}


class CodigoAlerta(StrEnum):
    # exigem revisão humana
    ANO_FIM_AUSENTE = "ANO_FIM_AUSENTE"
    FAIXA_ANO_DIVERGENTE = "FAIXA_ANO_DIVERGENTE"
    FAIXA_ANO_NAO_INTERPRETADA = "FAIXA_ANO_NAO_INTERPRETADA"
    MOTORIZACAO_SEM_CODIGO = "MOTORIZACAO_SEM_CODIGO"
    MOTORIZACAO_COMPOSTA = "MOTORIZACAO_COMPOSTA"
    MOTORIZACAO_NAO_INTERPRETADA = "MOTORIZACAO_NAO_INTERPRETADA"
    COMBUSTIVEL_CONFLITANTE = "COMBUSTIVEL_CONFLITANTE"
    PRECO_AUSENTE = "PRECO_AUSENTE"
    PRECO_SUSPEITO = "PRECO_SUSPEITO"
    PECAS_NAO_ENCONTRADAS = "PECAS_NAO_ENCONTRADAS"
    POSSIVEL_PRODUTO_DUPLICADO = "POSSIVEL_PRODUTO_DUPLICADO"
    VINCULO_ORFAO = "VINCULO_ORFAO"
    REFERENCIA_INEXISTENTE = "REFERENCIA_INEXISTENTE"
    # atenção
    MOTOR_NAO_IDENTIFICADO = "MOTOR_NAO_IDENTIFICADO"
    MULTIPLOS_COMBUSTIVEIS = "MULTIPLOS_COMBUSTIVEIS"
    DESCRICAO_COMPOSTA = "DESCRICAO_COMPOSTA"
    CORRESPONDENCIA_PARCIAL_MODELO = "CORRESPONDENCIA_PARCIAL_MODELO"
    MODELO_NAO_ENCONTRADO = "MODELO_NAO_ENCONTRADO"
    ANO_FORA_DO_INTERVALO = "ANO_FORA_DO_INTERVALO"
    FABRICANTE_NAO_ENCONTRADO = "FABRICANTE_NAO_ENCONTRADO"
    FABRICANTE_SEM_VEICULOS = "FABRICANTE_SEM_VEICULOS"
    COMBUSTIVEL_NAO_ENCONTRADO = "COMBUSTIVEL_NAO_ENCONTRADO"
    MOTOR_NAO_ENCONTRADO = "MOTOR_NAO_ENCONTRADO"
    DADO_AUSENTE = "DADO_AUSENTE"


class Evidencia(BaseModel):
    model_config = ConfigDict(frozen=True, json_schema_extra={"examples": [_EXEMPLO_EVIDENCIA]})

    tabela: TabelaBase
    chave: dict[str, int] = Field(description="Chave do registro na tabela (ex.: {'CodigoAplicacao': 35368}).")
    coluna: str
    valor_original: ValorPrimitivo = Field(description="Valor exatamente como está na base.")


class ValorRastreado(BaseModel, Generic[T]):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"original": "", "normalizado": None, "evidencia": _EXEMPLO_EVIDENCIA},
    ]})

    original: ValorPrimitivo = Field(description="Valor exatamente como está na base.")
    normalizado: T | None = Field(description="Valor normalizado; null quando ausente ou não interpretável.")
    evidencia: Evidencia


class Alerta(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "codigo": "ANO_FIM_AUSENTE", "severidade": "revisao",
        "mensagem": "Ano final de fabricação ausente na base; a aplicação foi considerada compatível a partir do ano inicial.",
        "evidencias": [_EXEMPLO_EVIDENCIA], "contexto": {"codigos_aplicacao": [31393]},
    }]})

    codigo: CodigoAlerta
    severidade: Severidade = Field(description="info, atencao ou revisao (revisao exige revisão humana).")
    mensagem: str
    evidencias: list[Evidencia] = Field(default_factory=list)
    contexto: dict[str, Any] = Field(default_factory=dict)


class RevisaoHumana(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"necessaria": True, "motivos": ["ANO_FIM_AUSENTE", "MOTORIZACAO_COMPOSTA"]}]})

    necessaria: bool
    motivos: list[CodigoAlerta]


class ParametroEcoado(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"original": "frontier", "normalizado": "FRONTIER"}]})

    original: str | int | None
    normalizado: str | int | None


class Fonte(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "banco": "Database/SQLite/db_proj_final.db",
        "sha256": "8a700b84124cefe12332e115d73da458f29082d57d627f5c5b0b8064b9d7cd2a",
    }]})

    banco: str = Field(description="Caminho do arquivo SQLite consultado.")
    sha256: str = Field(description="SHA-256 do arquivo no momento da partida do serviço.")


class Correspondencia(BaseModel):
    """Como o modelo pedido casou com a descrição da aplicação."""

    model_config = ConfigDict(frozen=True)

    tipo: Literal["inicio_segmento", "palavra_interna"] = Field(
        description="inicio_segmento: um segmento da descrição começa pelo modelo; "
        "palavra_interna: o modelo aparece como palavra inteira no meio de um segmento."
    )
    confianca: Literal["alta", "baixa"]


class MotorNormalizado(BaseModel):
    """Motorização decomposta em atributos. Ausente = null; nada é completado."""

    model_config = ConfigDict(frozen=True, json_schema_extra={"examples": [{
        "codigos": ["M9T"], "cilindrada_l": "2.3", "valvulas": 16, "cilindros": "L4", "comando": "DOHC",
        "interpretada": True, "chave": "M9T|2.3|16V|L4|DOHC",
    }]})

    codigos: list[str] = Field(description="Códigos de motor antes da cilindrada (vários = motorização composta).")
    cilindrada_l: str | None = Field(description="Cilindrada em litros, como texto exato (ex.: '2.5').")
    valvulas: int | None
    cilindros: str | None = Field(description="Arranjo e número de cilindros (ex.: 'L4').")
    comando: str | None = Field(description="DOHC, SOHC ou OHV.")
    interpretada: bool = Field(description="false quando não foi possível encontrar a cilindrada.")
    chave: str = Field(description="Chave estrita de agrupamento; '?' marca atributo ausente.")

    @property
    def sem_codigo(self) -> bool:
        return self.interpretada and not self.codigos

    @property
    def composta(self) -> bool:
        return len(self.codigos) > 1


class FaixaAnoNormalizada(BaseModel):
    inicio: int | None
    fim: int | None
    interpretada: bool


class Aplicacao(BaseModel):
    """Uma linha de APLICACAO (veículo), com cada valor rastreado."""

    codigo_aplicacao: int
    fabricante: ValorRastreado[str]
    tipo_aplicacao: ValorRastreado[str]
    descricao: ValorRastreado[str]
    modelos_base_derivados: list[str] = Field(description="DERIVADO: primeira palavra de cada item da descrição.")
    faixa_ano: ValorRastreado[FaixaAnoNormalizada]
    ano_inicio: ValorRastreado[int]
    ano_fim: ValorRastreado[int]
    motorizacao: ValorRastreado[MotorNormalizado]
    combustivel: ValorRastreado[str]
    correspondencia: Correspondencia | None = Field(default=None, description="Presente quando a busca foi por modelo.")


class CandidatoMotor(BaseModel):
    chave_motor: str
    motor: MotorNormalizado
    motorizacoes_originais: list[ValorRastreado[MotorNormalizado]]
    combustiveis: list[str]
    codigos_aplicacao: list[int]


class ItemCombustivel(BaseModel):
    combustivel: str | None
    valores: list[ValorRastreado[str]]
    codigos_aplicacao: list[int]


class Produto(BaseModel):
    codigo_produto: int
    descricao: ValorRastreado[str]
    grupo: ValorRastreado[str]
    numero_produto: ValorRastreado[str]
    preco: ValorRastreado[Decimal] = Field(description="Preço exato da base (sem moeda nem unidade documentadas: pendência P3).")
    qtd_embalagem: ValorRastreado[int]
    codigos_aplicacao: list[int] = Field(
        description="Aplicações existentes vinculadas à peça. Nas listagens, só as aplicações da consulta; no detalhe, todas."
    )


class ProdutoDetalhe(Produto):
    vinculos_orfaos: list[int] = Field(description="Códigos de aplicação vinculados que não existem na base.")
    campos_nao_interpretados: dict[str, ValorPrimitivo] = Field(
        description="Colunas sem significado documentado (pendência P2), apenas com o valor original."
    )


class DadosMotorizacoes(BaseModel):
    identificado: bool = Field(description="true somente quando a base deixa exatamente um motor candidato.")
    motor_identificado: CandidatoMotor | None
    candidatos: list[CandidatoMotor]
    atributos_distintivos: dict[str, list[str | None]] = Field(description="Atributos que variam entre os candidatos (null = ausente na base).")
    aplicacoes: list[Aplicacao]


class DadosCombustiveis(BaseModel):
    unico: bool = Field(description="true somente quando há exatamente um combustível.")
    combustiveis: list[ItemCombustivel]
    aplicacoes: list[Aplicacao]


class ItemFabricante(BaseModel):
    codigo_fabricante: int
    descricao: ValorRastreado[str]
    quantidade_aplicacoes: int


class ItemGrupoProduto(BaseModel):
    codigo_grupo_produto: int
    descricao: ValorRastreado[str]
    quantidade_produtos: int


class DadosSaude(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "status": "ok", "banco": "Database/SQLite/db_proj_final.db", "somente_leitura": True,
        "sha256": "8a700b84124cefe12332e115d73da458f29082d57d627f5c5b0b8064b9d7cd2a",
        "contagens": {"APLICACAO": 131, "FABRICANTE": 12, "GRUPOPRODUTO": 27, "PRODUTO": 5944,
                      "PRODUTO_APLICACAO": 1438, "TIPOAPLICACAO": 9},
    }]})

    status: Literal["ok"]
    banco: str
    somente_leitura: bool
    sha256: str
    contagens: dict[str, int]


class Resposta(BaseModel, Generic[T]):
    consulta: dict[str, ParametroEcoado] = Field(description="Parâmetros recebidos: original e normalizado.")
    dados: T
    total: int
    pagina: int | None = None
    limite: int | None = None
    alertas: list[Alerta]
    revisao_humana: RevisaoHumana
    fonte: Fonte
