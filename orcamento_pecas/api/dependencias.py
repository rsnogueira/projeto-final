"""Dependências por requisição: uma conexão somente leitura, aberta e fechada a cada chamada."""

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from orcamento_pecas.dados.conexao import abrir_somente_leitura
from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.servicos.catalogos import ServicoCatalogos
from orcamento_pecas.servicos.pecas import ServicoPecas
from orcamento_pecas.servicos.veiculos import ServicoVeiculos


def obter_conexao(request: Request) -> Iterator[sqlite3.Connection]:
    conexao = abrir_somente_leitura(request.app.state.caminho_banco)
    try:
        yield conexao
    finally:
        conexao.close()


ConexaoDep = Annotated[sqlite3.Connection, Depends(obter_conexao)]


def obter_servico_veiculos(request: Request, conexao: ConexaoDep) -> ServicoVeiculos:
    return ServicoVeiculos(Repositorio(conexao), request.app.state.fonte)


VeiculosDep = Annotated[ServicoVeiculos, Depends(obter_servico_veiculos)]


def obter_servico_pecas(request: Request, conexao: ConexaoDep, veiculos: VeiculosDep) -> ServicoPecas:
    return ServicoPecas(Repositorio(conexao), veiculos, request.app.state.fonte)


def obter_servico_catalogos(request: Request, conexao: ConexaoDep) -> ServicoCatalogos:
    return ServicoCatalogos(Repositorio(conexao), request.app.state.fonte)


PecasDep = Annotated[ServicoPecas, Depends(obter_servico_pecas)]
CatalogosDep = Annotated[ServicoCatalogos, Depends(obter_servico_catalogos)]
