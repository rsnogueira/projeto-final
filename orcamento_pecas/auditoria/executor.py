"""Execução completa da auditoria: base, bateria de consultas, invariantes, amostra e relatórios."""

from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from orcamento_pecas import __version__
from orcamento_pecas.auditoria.amostragem import ItemPopulacao, sortear_amostra
from orcamento_pecas.auditoria.bateria import Consulta, gerar_bateria
from orcamento_pecas.auditoria.relatorio import Metadados, RelatorioAuditoria, Resumo, gravar_excel, gravar_json
from orcamento_pecas.auditoria.verificacoes import Falha, auditar_base, auditar_resposta, valores_rastreados
from orcamento_pecas.config import rotulo_banco
from orcamento_pecas.dados.conexao import abrir_somente_leitura, sha256_arquivo
from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.modelos import Fonte, Resposta
from orcamento_pecas.servicos.pecas import ServicoPecas
from orcamento_pecas.servicos.veiculos import ServicoVeiculos


def _exibir(normalizado: Any) -> str | None:
    if normalizado is None:
        return None
    if isinstance(normalizado, BaseModel):
        return normalizado.model_dump_json()
    if isinstance(normalizado, Decimal):
        return str(normalizado)
    return str(normalizado)


def _executar(consulta: Consulta, veiculos: ServicoVeiculos, pecas: ServicoPecas) -> tuple[Resposta | None, dict[str, Any]]:
    p = consulta.parametros
    if consulta.tipo == "motorizacoes":
        return veiculos.motorizacoes(p["modelo"], p["ano"]), dict(p)
    if consulta.tipo == "combustiveis":
        return veiculos.combustiveis(p["modelo"], p["ano"]), dict(p)
    if consulta.tipo == "pecas_da_aplicacao":
        return pecas.da_aplicacao(p["codigo_aplicacao"]), {}
    return pecas.obter(p["codigo_produto"]), {}


def executar_auditoria(
    caminho_banco: Path | str,
    tamanho_amostra: int = 30,
    semente: int = 42,
    pasta_saida: Path | str = Path("saidas/auditoria"),
    agora: datetime | None = None,
    comando: str = "",
) -> tuple[RelatorioAuditoria, Path, Path]:
    caminho = Path(caminho_banco)
    conexao = abrir_somente_leitura(caminho)
    sha_inicial = sha256_arquivo(caminho)
    falhas: list[Falha] = []
    populacao: dict[str, ItemPopulacao] = {}
    valores = 0
    try:
        repo = Repositorio(conexao)
        fonte = Fonte(banco=rotulo_banco(caminho), sha256=sha_inicial)
        veiculos = ServicoVeiculos(repo, fonte)
        pecas = ServicoPecas(repo, veiculos, fonte)
        alertas_base = auditar_base(repo, veiculos, pecas)
        bateria = gerar_bateria(repo)
        for consulta in bateria:
            rota = consulta.rota()
            resposta, filtros = _executar(consulta, veiculos, pecas)
            if resposta is None:
                falhas.append(Falha(invariante="I0", consulta=rota, detalhe="consulta da bateria sem resposta"))
                continue
            falhas += auditar_resposta(resposta, repo, filtros, rota)
            em_revisao = {e.model_dump_json() for a in resposta.alertas if a.severidade == "revisao" for e in a.evidencias}
            for campo, valor in valores_rastreados(resposta.dados):
                valores += 1
                chave = valor.evidencia.model_dump_json()
                if chave not in populacao:
                    populacao[chave] = ItemPopulacao(
                        consulta=rota, campo=campo, valor_exibido=_exibir(valor.normalizado), original=valor.original,
                        evidencia=valor.evidencia, com_alerta_revisao=chave in em_revisao,
                    )
                elif chave in em_revisao and not populacao[chave].com_alerta_revisao:
                    populacao[chave] = populacao[chave].model_copy(update={"com_alerta_revisao": True})
    finally:
        conexao.close()

    sha_final = sha256_arquivo(caminho)
    if sha_final != sha_inicial:
        falhas.append(Falha(invariante="I0", detalhe="o arquivo do banco mudou durante a auditoria"))

    itens = list(populacao.values())
    amostra = sortear_amostra(itens, tamanho_amostra, semente)
    agora = agora or datetime.now()
    relatorio = RelatorioAuditoria(
        metadados=Metadados(
            gerado_em=agora.isoformat(timespec="seconds"), banco=rotulo_banco(caminho), sha256_inicial=sha_inicial,
            sha256_final=sha_final, semente=semente, tamanho_amostra=tamanho_amostra, comando=comando, versao=__version__,
        ),
        resumo=Resumo(
            consultas_executadas=len(bateria),
            valores_verificados=valores,
            falhas=len(falhas),
            falhas_por_invariante=dict(sorted(Counter(f.invariante for f in falhas).items())),
            alertas_base_por_codigo={a.codigo.value: len(a.evidencias) for a in alertas_base},
            populacao_com_alerta=sum(1 for i in itens if i.com_alerta_revisao),
            populacao_limpa=sum(1 for i in itens if not i.com_alerta_revisao),
            itens_amostra=len(amostra),
        ),
        falhas=falhas,
        alertas_base=alertas_base,
        amostra=amostra,
    )
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / f"auditoria_{agora:%Y%m%d-%H%M%S}"
    caminho_json, caminho_excel = base.with_suffix(".json"), base.with_suffix(".xlsx")
    gravar_json(relatorio, caminho_json)
    gravar_excel(relatorio, caminho_excel)
    return relatorio, caminho_json, caminho_excel
