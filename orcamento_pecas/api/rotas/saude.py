from fastapi import APIRouter

from orcamento_pecas.api.dependencias import CatalogosDep
from orcamento_pecas.dominio.modelos import DadosSaude

router = APIRouter(tags=["Saúde"])


@router.get(
    "/saude",
    response_model=DadosSaude,
    summary="Estado do serviço",
    description="Confirma que o banco está acessível em modo somente leitura e informa o SHA-256 do arquivo "
    "(calculado na partida) e a contagem de registros por tabela.",
)
def saude(servico: CatalogosDep) -> DadosSaude:
    return servico.saude()
