from fastapi import APIRouter, HTTPException

from orcamento_pecas.api.dependencias import VeiculosDep
from orcamento_pecas.api.parametros import (
    Ano,
    AnoOpcional,
    CodigoAplicacao,
    Combustivel,
    Fabricante,
    Limite,
    Modelo,
    ModeloOpcional,
    Pagina,
)
from orcamento_pecas.api.rotas import RESPOSTA_404
from orcamento_pecas.dominio.modelos import Aplicacao, DadosCombustiveis, DadosMotorizacoes, Resposta

router = APIRouter(tags=["Veículos"])

_ENVELOPE = (
    " Toda resposta traz `consulta` (parâmetros original e normalizado), `alertas`, `revisao_humana` e `fonte` "
    "(banco e SHA-256). Cada valor vindo da base traz `original`, `normalizado` (null quando ausente) e `evidencia` "
    "(tabela, chave, coluna e valor original)."
)

# As rotas fixas vêm antes de /veiculos/{codigo_aplicacao} para não serem capturadas por ela.


@router.get(
    "/veiculos/motorizacoes",
    response_model=Resposta[DadosMotorizacoes],
    summary="Motorizações por modelo e ano",
    description="Agrupa as aplicações do modelo e ano em motores candidatos (chave estrita: códigos, cilindrada, "
    "válvulas, cilindros e comando). `identificado` só é true quando a base deixa exatamente um candidato; com mais "
    "de um, `atributos_distintivos` mostra o que os diferencia, para que se peçam informações complementares. "
    "Faixas de ano sem fim entram como compatíveis, com o alerta ANO_FIM_AUSENTE." + _ENVELOPE,
)
def motorizacoes(modelo: Modelo, ano: Ano, servico: VeiculosDep, fabricante: Fabricante = None, combustivel: Combustivel = None):
    return servico.motorizacoes(modelo, ano, fabricante, combustivel)


@router.get(
    "/veiculos/combustiveis",
    response_model=Resposta[DadosCombustiveis],
    summary="Combustíveis por modelo e ano",
    description="Combustíveis distintos das aplicações do modelo e ano, cada um com suas evidências. "
    "Mais de um combustível gera MULTIPLOS_COMBUSTIVEIS; o mesmo motor com combustíveis diferentes gera "
    "COMBUSTIVEL_CONFLITANTE, que exige revisão humana." + _ENVELOPE,
)
def combustiveis(modelo: Modelo, ano: Ano, servico: VeiculosDep, fabricante: Fabricante = None):
    return servico.combustiveis(modelo, ano, fabricante)


@router.get(
    "/veiculos",
    response_model=Resposta[list[Aplicacao]],
    summary="Busca de aplicações (veículos)",
    description="Lista paginada de aplicações, com filtros opcionais de modelo, ano, fabricante e combustível, "
    "ordenada pelo código da aplicação." + _ENVELOPE,
)
def buscar_veiculos(
    servico: VeiculosDep,
    modelo: ModeloOpcional = None,
    ano: AnoOpcional = None,
    fabricante: Fabricante = None,
    combustivel: Combustivel = None,
    pagina: Pagina = 1,
    limite: Limite = 50,
):
    return servico.buscar(modelo, ano, fabricante, combustivel, pagina, limite)


@router.get(
    "/veiculos/{codigo_aplicacao}",
    response_model=Resposta[Aplicacao],
    responses=RESPOSTA_404,
    summary="Detalhe de uma aplicação",
    description="Uma aplicação (veículo) com todos os valores rastreados e seus alertas de qualidade de dados." + _ENVELOPE,
)
def obter_veiculo(codigo_aplicacao: CodigoAplicacao, servico: VeiculosDep):
    resposta = servico.obter(codigo_aplicacao)
    if resposta is None:
        raise HTTPException(status_code=404, detail=f"Aplicação {codigo_aplicacao} não encontrada.")
    return resposta
