"""Parâmetros de consulta e de caminho, com descrição e exemplos para o Swagger."""

from typing import Annotated

from fastapi import Path, Query

_TEM_TEXTO = r"\S"  # pelo menos um caractere que não seja espaço
MAIOR_INTEIRO_SQLITE = 2**63 - 1  # acima disso o sqlite3 lança OverflowError (seria erro 500)

Modelo = Annotated[str, Query(
    description="Modelo do veículo como o comprador escreveu (ex.: frontier). Comparado sem acentos e sem diferenciar "
    "maiúsculas, por palavra inteira, contra a descrição da aplicação.",
    pattern=_TEM_TEXTO, examples=["frontier"],
)]
ModeloOpcional = Annotated[str | None, Query(
    description="Modelo do veículo (opcional). Mesmas regras de correspondência de /v1/veiculos/motorizacoes.",
    pattern=_TEM_TEXTO, examples=["frontier"],
)]
Ano = Annotated[int, Query(ge=1000, le=9999, description="Ano de fabricação, com 4 dígitos.", examples=[2008])]
AnoOpcional = Annotated[int | None, Query(ge=1000, le=9999, description="Ano de fabricação (opcional), com 4 dígitos.", examples=[2008])]
Fabricante = Annotated[str | None, Query(
    description="Fabricante (opcional), ex.: nissan. Hoje só a NISSAN tem veículos na base.", examples=["nissan"],
)]
Combustivel = Annotated[str | None, Query(
    description="Combustível (opcional). Valores presentes na base: FLEX, DIESEL e GASOLINA.", examples=["diesel"],
)]
ChaveMotor = Annotated[str | None, Query(
    description="Chave de motor exata, como devolvida em /v1/veiculos/motorizacoes (campo chave_motor).",
    examples=["YD25ETI|2.5|16V|L4|DOHC"],
)]
Grupo = Annotated[int | None, Query(
    ge=1, le=MAIOR_INTEIRO_SQLITE,
    description="Código do grupo de produto (ver /v1/grupos-produto). Ex.: 39 = BRONZINA.", examples=[39],
)]
Texto = Annotated[str | None, Query(
    description="Palavras que devem aparecer inteiras na descrição da peça (ex.: mancal std).", examples=["mancal"],
)]
Pagina = Annotated[int, Query(ge=1, le=MAIOR_INTEIRO_SQLITE, description="Página, começando em 1.", examples=[1])]
Limite = Annotated[int, Query(ge=1, le=200, description="Itens por página (padrão 50, máximo 200).", examples=[50])]
CodigoAplicacao = Annotated[int, Path(ge=1, le=MAIOR_INTEIRO_SQLITE, description="Código da aplicação (APLICACAO.CodigoAplicacao).", examples=[35368])]
CodigoProduto = Annotated[int, Path(ge=1, le=MAIOR_INTEIRO_SQLITE, description="Código do produto (PRODUTO.CodigoProduto).", examples=[6809])]
