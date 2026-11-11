"""Bateria determinística de consultas usada pela auditoria."""

from collections import defaultdict
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict

from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.normalizacao import (
    ano_compativel,
    corresponde_modelo,
    interpretar_motorizacao,
    modelos_base,
    normalizar_ano_fim,
    normalizar_texto,
)

TipoConsulta = Literal[
    "motorizacoes", "combustiveis", "pecas_por_veiculo", "pecas_da_aplicacao", "produto", "aplicacao", "busca_veiculos",
]
_ROTAS: dict[str, str] = {
    "motorizacoes": "/v1/veiculos/motorizacoes",
    "combustiveis": "/v1/veiculos/combustiveis",
    "pecas_por_veiculo": "/v1/pecas",
    "busca_veiculos": "/v1/veiculos",
    "pecas_da_aplicacao": "/v1/veiculos/{codigo_aplicacao}/pecas",
    "produto": "/v1/pecas/{codigo_produto}",
    "aplicacao": "/v1/veiculos/{codigo_aplicacao}",
}
_COM_QUERY = {"motorizacoes", "combustiveis", "pecas_por_veiculo", "busca_veiculos"}


class Consulta(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: TipoConsulta
    parametros: dict[str, str | int]

    def rota(self) -> str:
        """Rota HTTP equivalente, para o revisor reproduzir a consulta no Swagger."""
        if self.tipo in _COM_QUERY:
            return f"GET {_ROTAS[self.tipo]}?{urlencode(self.parametros)}"
        return "GET " + _ROTAS[self.tipo].format(**self.parametros)


def _inteiro(valor: object) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def gerar_bateria(repo: Repositorio) -> list[Consulta]:
    """Para cada modelo-base e cada ano das suas faixas (faixa aberta vai até o maior ano presente na base):
    motorizações e combustíveis; peças por veículo, por cada chave de motor candidata e por cada combustível;
    motorizações filtradas por cada combustível. Depois: busca de veículos por modelo, detalhe e peças de cada
    aplicação, e detalhe de cada produto vinculado."""
    linhas = repo.listar_aplicacoes(None)
    anos_presentes = [
        ano for linha in linhas
        for ano in (_inteiro(linha["AnoInicioFabricacao"]), normalizar_ano_fim(linha["AnoFimFabricacao"]))
        if ano is not None
    ]
    maior_ano = max(anos_presentes, default=0)
    anos_por_modelo: dict[str, set[int]] = defaultdict(set)
    for linha in linhas:
        inicio = _inteiro(linha["AnoInicioFabricacao"])
        if inicio is None:
            continue
        fim = normalizar_ano_fim(linha["AnoFimFabricacao"])
        for modelo in modelos_base(linha["DescricaoAplicacao"]):
            anos_por_modelo[modelo].update(range(inicio, (fim if fim is not None else maior_ano) + 1))

    consultas: list[Consulta] = []
    for modelo in sorted(anos_por_modelo):
        for ano in sorted(anos_por_modelo[modelo]):
            compativeis = [
                l for l in linhas
                if corresponde_modelo(l["DescricaoAplicacao"], modelo)
                and (inicio := _inteiro(l["AnoInicioFabricacao"])) is not None
                and ano_compativel(ano, inicio, normalizar_ano_fim(l["AnoFimFabricacao"]))
            ]
            chaves = sorted({interpretar_motorizacao(l["Motorizacao"]).chave for l in compativeis})
            combustiveis = sorted({c for l in compativeis if (c := normalizar_texto(l["Combustivel"]))})
            base = {"modelo": modelo, "ano": ano}
            consultas.append(Consulta(tipo="motorizacoes", parametros=base))
            consultas.append(Consulta(tipo="combustiveis", parametros=base))
            consultas.append(Consulta(tipo="pecas_por_veiculo", parametros=base))
            consultas += [Consulta(tipo="pecas_por_veiculo", parametros={**base, "chave_motor": c}) for c in chaves]
            for combustivel in combustiveis:
                consultas.append(Consulta(tipo="motorizacoes", parametros={**base, "combustivel": combustivel}))
                consultas.append(Consulta(tipo="pecas_por_veiculo", parametros={**base, "combustivel": combustivel}))
    consultas += [Consulta(tipo="busca_veiculos", parametros={"modelo": m}) for m in sorted(anos_por_modelo)]
    for linha in linhas:
        consultas.append(Consulta(tipo="aplicacao", parametros={"codigo_aplicacao": linha["CodigoAplicacao"]}))
        consultas.append(Consulta(tipo="pecas_da_aplicacao", parametros={"codigo_aplicacao": linha["CodigoAplicacao"]}))
    consultas += [Consulta(tipo="produto", parametros={"codigo_produto": c}) for c in repo.listar_produtos_vinculados()]
    return consultas
