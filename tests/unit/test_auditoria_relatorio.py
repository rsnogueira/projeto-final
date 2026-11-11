import json
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import load_workbook

from orcamento_pecas.auditoria.executor import executar_auditoria
from orcamento_pecas.auditoria.relatorio import ABAS, COLUNAS_AMOSTRA, ler_revisao
from orcamento_pecas.dados.conexao import sha256_arquivo

AGORA = datetime(2026, 11, 10, 9, 30, 0)


@pytest.fixture
def auditoria(banco_teste: Path, tmp_path: Path):
    return executar_auditoria(banco_teste, tamanho_amostra=10, semente=42, pasta_saida=tmp_path, agora=AGORA)


def test_executar_auditoria_gera_json_e_excel_sem_falhas(auditoria, banco_teste):
    relatorio, caminho_json, caminho_excel = auditoria
    assert caminho_json.name == "auditoria_20261110-093000.json"
    assert caminho_excel.name == "auditoria_20261110-093000.xlsx"
    assert relatorio.resumo.falhas == 0, relatorio.falhas[:3]
    assert relatorio.resumo.consultas_executadas > 0
    assert relatorio.resumo.valores_verificados > 0
    assert relatorio.metadados.sha256_inicial == relatorio.metadados.sha256_final == sha256_arquivo(banco_teste)
    assert len(relatorio.amostra) == 10
    assert json.loads(caminho_json.read_text(encoding="utf-8")) == relatorio.model_dump(mode="json")


def test_excel_tem_abas_e_colunas_do_revisor(auditoria):
    _, _, caminho_excel = auditoria
    livro = load_workbook(caminho_excel)
    assert livro.sheetnames == list(ABAS)
    cabecalho = [c.value for c in livro["Amostra_revisao"][1]]
    assert cabecalho == list(COLUNAS_AMOSTRA)
    assert {"Conferido (S/N)", "Divergência", "Comentário", "Revisor", "Data"} <= set(cabecalho)


def test_json_e_excel_consistentes(auditoria):
    relatorio, _, caminho_excel = auditoria
    livro = load_workbook(caminho_excel)
    linhas = list(livro["Amostra_revisao"].iter_rows(min_row=2, values_only=True))
    colunas = list(COLUNAS_AMOSTRA)
    assert [l[colunas.index("ID")] for l in linhas] == [i.id for i in relatorio.amostra]
    assert [l[colunas.index("Valor original")] for l in linhas] == [
        json.dumps(i.original, ensure_ascii=False) for i in relatorio.amostra
    ]
    total_evidencias = sum(max(1, len(a.evidencias)) for a in relatorio.alertas_base)  # 1 linha por evidência
    assert livro["Alertas_base"].max_row - 1 == total_evidencias


def test_ler_revisao_conta_conferidos_e_divergencias(auditoria):
    _, _, caminho_excel = auditoria
    livro = load_workbook(caminho_excel)
    aba = livro["Amostra_revisao"]
    colunas = list(COLUNAS_AMOSTRA)
    aba.cell(row=2, column=colunas.index("Conferido (S/N)") + 1, value="S")
    aba.cell(row=3, column=colunas.index("Conferido (S/N)") + 1, value="N")
    aba.cell(row=3, column=colunas.index("Divergência") + 1, value="valor diferente")
    aba.cell(row=4, column=colunas.index("Conferido (S/N)") + 1, value="s")
    livro.save(caminho_excel)
    resumo = ler_revisao(caminho_excel)
    assert resumo.total == 10
    assert resumo.conferidos == ["A01", "A03"]
    assert resumo.divergencias == ["A02"]
    assert resumo.pendentes == [f"A{n:02d}" for n in range(4, 11)]
