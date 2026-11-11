from fastapi import APIRouter, HTTPException

from orcamento_pecas.api.dependencias import PecasDep
from orcamento_pecas.api.parametros import (
    Ano,
    ChaveMotor,
    CodigoAplicacao,
    CodigoProduto,
    Combustivel,
    Fabricante,
    Grupo,
    Limite,
    Modelo,
    Pagina,
    Texto,
)
from orcamento_pecas.api.rotas import RESPOSTA_404
from orcamento_pecas.dominio.modelos import Produto, ProdutoDetalhe, Resposta

router = APIRouter(tags=["Peças"])

_PRECO = (
    " O preço é devolvido exatamente como está na base (`normalizado` em texto decimal, sem arredondamento); "
    "preço ausente gera PRECO_AUSENTE e exige revisão humana. Produtos com a mesma descrição e o mesmo número-base "
    "geram POSSIVEL_PRODUTO_DUPLICADO; nada é mesclado."
)


@router.get(
    "/veiculos/{codigo_aplicacao}/pecas",
    response_model=Resposta[list[Produto]],
    responses=RESPOSTA_404,
    summary="Peças de uma aplicação",
    description="Peças vinculadas a uma aplicação, com filtros opcionais por grupo e por palavras da descrição. "
    "Equivale à consulta Database/Queries_Uteis/qry_produto_por_veiculo.sql filtrada por aplicação." + _PRECO,
)
def pecas_da_aplicacao(codigo_aplicacao: CodigoAplicacao, servico: PecasDep, grupo: Grupo = None, texto: Texto = None):
    resposta = servico.da_aplicacao(codigo_aplicacao, grupo, texto)
    if resposta is None:
        raise HTTPException(status_code=404, detail=f"Aplicação {codigo_aplicacao} não encontrada.")
    return resposta


@router.get(
    "/pecas",
    response_model=Resposta[list[Produto]],
    summary="Peças por veículo ou motor",
    description="Peças compatíveis com as aplicações do modelo e ano (e, opcionalmente, da chave de motor, do "
    "fabricante e do combustível), com filtros por grupo e texto. Sem `chave_motor` e com mais de um motor "
    "candidato, o alerta MOTOR_NAO_IDENTIFICADO tem severidade de revisão: as peças podem ser de motores diferentes."
    + _PRECO,
)
def pecas_por_veiculo(
    modelo: Modelo,
    ano: Ano,
    servico: PecasDep,
    chave_motor: ChaveMotor = None,
    fabricante: Fabricante = None,
    combustivel: Combustivel = None,
    grupo: Grupo = None,
    texto: Texto = None,
    pagina: Pagina = 1,
    limite: Limite = 50,
):
    return servico.por_veiculo(modelo, ano, chave_motor, fabricante, combustivel, grupo, texto, pagina, limite)


@router.get(
    "/pecas/{codigo_produto}",
    response_model=Resposta[ProdutoDetalhe],
    responses=RESPOSTA_404,
    summary="Detalhe de uma peça",
    description="Produto com todas as aplicações existentes às quais está vinculado, os vínculos órfãos "
    "(aplicações inexistentes) e as colunas sem significado documentado em `campos_nao_interpretados`, "
    "apenas com o valor original." + _PRECO,
)
def obter_peca(codigo_produto: CodigoProduto, servico: PecasDep):
    resposta = servico.obter(codigo_produto)
    if resposta is None:
        raise HTTPException(status_code=404, detail=f"Produto {codigo_produto} não encontrado.")
    return resposta
