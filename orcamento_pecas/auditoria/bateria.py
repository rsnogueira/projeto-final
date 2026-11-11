"""Bateria determinística de consultas usada pela auditoria."""

from collections import defaultdict
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict

from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.normalizacao import modelos_base, normalizar_ano_fim

TipoConsulta = Literal["motorizacoes", "combustiveis", "pecas_da_aplicacao", "produto"]
_ROTAS: dict[str, str] = {
    "motorizacoes": "/v1/veiculos/motorizacoes",
    "combustiveis": "/v1/veiculos/combustiveis",
    "pecas_da_aplicacao": "/v1/veiculos/{codigo_aplicacao}/pecas",
    "produto": "/v1/pecas/{codigo_produto}",
}


class Consulta(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: TipoConsulta
    parametros: dict[str, str | int]

    def rota(self) -> str:
        """Rota HTTP equivalente, para o revisor reproduzir a consulta no Swagger."""
        if self.tipo in ("motorizacoes", "combustiveis"):
            return f"GET {_ROTAS[self.tipo]}?{urlencode(self.parametros)}"
        return "GET " + _ROTAS[self.tipo].format(**self.parametros)


def _inteiro(valor: object) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def gerar_bateria(repo: Repositorio) -> list[Consulta]:
    """Para cada modelo-base, cada ano das suas faixas (faixa aberta vai até o maior ano presente na base):
    motorizações e combustíveis. Depois, as peças de cada aplicação e o detalhe de cada produto vinculado."""
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
            consultas.append(Consulta(tipo="motorizacoes", parametros={"modelo": modelo, "ano": ano}))
            consultas.append(Consulta(tipo="combustiveis", parametros={"modelo": modelo, "ano": ano}))
    consultas += [Consulta(tipo="pecas_da_aplicacao", parametros={"codigo_aplicacao": l["CodigoAplicacao"]}) for l in linhas]
    consultas += [Consulta(tipo="produto", parametros={"codigo_produto": c}) for c in repo.listar_produtos_vinculados()]
    return consultas
