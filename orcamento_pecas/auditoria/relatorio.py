"""Relatório de auditoria: modelo, gravação em JSON e Excel, e leitura da revisão manual."""

import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from pydantic import BaseModel

from orcamento_pecas.auditoria.amostragem import ItemAmostra
from orcamento_pecas.auditoria.verificacoes import Falha
from orcamento_pecas.dominio.modelos import Alerta
from orcamento_pecas.dominio.normalizacao import normalizar_texto

ABAS = ("Resumo", "Falhas", "Alertas_base", "Amostra_revisao", "Metadados")
COLUNAS_REVISOR = ("Conferido (S/N)", "Divergência", "Comentário", "Revisor", "Data")
COLUNAS_AMOSTRA = (
    "ID", "Estrato", "Consulta", "Campo", "Valor exibido", "Valor original",
    "Tabela", "Chave", "Coluna", "SQL de conferência", *COLUNAS_REVISOR,
)


class Metadados(BaseModel):
    gerado_em: str
    banco: str
    sha256_inicial: str
    sha256_final: str
    semente: int
    tamanho_amostra: int
    comando: str
    versao: str


class Resumo(BaseModel):
    consultas_executadas: int
    valores_verificados: int
    falhas: int
    falhas_por_invariante: dict[str, int]
    alertas_base_por_codigo: dict[str, int]
    populacao_com_alerta: int
    populacao_limpa: int
    itens_amostra: int


class RelatorioAuditoria(BaseModel):
    metadados: Metadados
    resumo: Resumo
    falhas: list[Falha]
    alertas_base: list[Alerta]
    amostra: list[ItemAmostra]


class ResumoRevisao(BaseModel):
    arquivo: str
    total: int
    conferidos: list[str]
    divergencias: list[str]
    pendentes: list[str]
    invalidos: list[str] = []  # valor de "Conferido (S/N)" fora de S/SIM/N/NAO


def _json(valor: object) -> str:
    return json.dumps(valor, ensure_ascii=False)


def gravar_json(relatorio: RelatorioAuditoria, caminho: Path) -> None:
    caminho.write_text(relatorio.model_dump_json(indent=2), encoding="utf-8")


def _aba(livro: Workbook, titulo: str, cabecalho: tuple[str, ...], linhas: list[tuple]) -> None:
    aba = livro.create_sheet(titulo)
    aba.append(list(cabecalho))
    for celula in aba[1]:
        celula.font = Font(bold=True)
    for linha in linhas:
        aba.append(list(linha))
    aba.freeze_panes = "A2"
    for indice, nome in enumerate(cabecalho, 1):
        maior = max([len(str(nome))] + [len(str(l[indice - 1] or "")) for l in linhas[:200]])
        aba.column_dimensions[aba.cell(row=1, column=indice).column_letter].width = min(max(10, maior + 2), 60)


def gravar_excel(relatorio: RelatorioAuditoria, caminho: Path) -> None:
    livro = Workbook()
    livro.remove(livro.active)
    resumo = relatorio.resumo
    linhas_resumo = [
        ("consultas_executadas", resumo.consultas_executadas),
        ("valores_verificados", resumo.valores_verificados),
        ("falhas", resumo.falhas),
        ("populacao_com_alerta", resumo.populacao_com_alerta),
        ("populacao_limpa", resumo.populacao_limpa),
        ("itens_amostra", resumo.itens_amostra),
    ]
    linhas_resumo += [(f"falhas_por_invariante.{k}", v) for k, v in resumo.falhas_por_invariante.items()]
    linhas_resumo += [(f"alertas_base_por_codigo.{k}", v) for k, v in resumo.alertas_base_por_codigo.items()]
    _aba(livro, "Resumo", ("Indicador", "Valor"), linhas_resumo)

    _aba(livro, "Falhas", ("Invariante", "Consulta", "Detalhe", "Tabela", "Chave", "Coluna", "Valor original"), [
        (f.invariante, f.consulta, f.detalhe,
         f.evidencia.tabela if f.evidencia else None,
         _json(f.evidencia.chave) if f.evidencia else None,
         f.evidencia.coluna if f.evidencia else None,
         _json(f.evidencia.valor_original) if f.evidencia else None)
        for f in relatorio.falhas
    ])

    linhas_alertas = []
    for alerta in relatorio.alertas_base:
        contexto = _json(alerta.contexto)
        for evidencia in alerta.evidencias or [None]:
            linhas_alertas.append((
                alerta.codigo.value, alerta.severidade, alerta.mensagem,
                evidencia.tabela if evidencia else None,
                _json(evidencia.chave) if evidencia else None,
                evidencia.coluna if evidencia else None,
                _json(evidencia.valor_original) if evidencia else None,
                contexto,
            ))
    _aba(livro, "Alertas_base", ("Código", "Severidade", "Mensagem", "Tabela", "Chave", "Coluna", "Valor original", "Contexto"), linhas_alertas)

    _aba(livro, "Amostra_revisao", COLUNAS_AMOSTRA, [
        (i.id, i.estrato, i.consulta, i.campo, i.valor_exibido, _json(i.original),
         i.evidencia.tabela, _json(i.evidencia.chave), i.evidencia.coluna, i.sql_conferencia,
         *([None] * len(COLUNAS_REVISOR)))
        for i in relatorio.amostra
    ])

    _aba(livro, "Metadados", ("Campo", "Valor"), list(relatorio.metadados.model_dump().items()))
    livro.save(caminho)


def ler_revisao(caminho: Path) -> ResumoRevisao:
    """Lê a aba Amostra_revisao preenchida.

    Texto em Divergência, ou N/NÃO = divergência; S/SIM = conferido; vazio = pendente; outro valor = inválido.
    """
    livro = load_workbook(caminho, read_only=True)
    try:
        linhas = list(livro["Amostra_revisao"].iter_rows(values_only=True))
    finally:
        livro.close()
    cabecalho = list(linhas[0])
    pos = {nome: cabecalho.index(nome) for nome in ("ID", "Conferido (S/N)", "Divergência")}
    conferidos, divergencias, pendentes, invalidos = [], [], [], []
    for linha in linhas[1:]:
        identificador = linha[pos["ID"]]
        if identificador is None:
            continue
        conferido = normalizar_texto(str(linha[pos["Conferido (S/N)"]] or "")) or ""
        divergencia = str(linha[pos["Divergência"]] or "").strip()
        if conferido in {"N", "NAO"} or divergencia:
            divergencias.append(identificador)
        elif conferido in {"S", "SIM"}:
            conferidos.append(identificador)
        elif not conferido:
            pendentes.append(identificador)
        else:
            invalidos.append(identificador)
    return ResumoRevisao(
        arquivo=str(caminho), total=len(conferidos) + len(divergencias) + len(pendentes) + len(invalidos),
        conferidos=conferidos, divergencias=divergencias, pendentes=pendentes, invalidos=invalidos,
    )
