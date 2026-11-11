from fastapi import APIRouter

from orcamento_pecas.api.dependencias import CatalogosDep
from orcamento_pecas.dominio.modelos import ItemFabricante, ItemGrupoProduto, Resposta

router = APIRouter(tags=["Catálogos"])


@router.get(
    "/fabricantes",
    response_model=Resposta[list[ItemFabricante]],
    summary="Fabricantes",
    description="Fabricantes cadastrados, com a quantidade de aplicações (veículos) de cada um. "
    "Fabricantes sem veículos geram o alerta FABRICANTE_SEM_VEICULOS.",
)
def fabricantes(servico: CatalogosDep):
    return servico.fabricantes()


@router.get(
    "/grupos-produto",
    response_model=Resposta[list[ItemGrupoProduto]],
    summary="Grupos de produto",
    description="Grupos de peças (ex.: 39 = BRONZINA), com a quantidade de produtos de cada um. "
    "Use o código no parâmetro `grupo` das consultas de peças.",
)
def grupos_produto(servico: CatalogosDep):
    return servico.grupos()
