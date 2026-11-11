from pathlib import Path

from openpyxl import load_workbook

from orcamento_pecas.auditoria.relatorio import COLUNAS_AMOSTRA
from orcamento_pecas.cli import main


def test_cli_auditoria_sai_com_zero_e_informa_os_arquivos(banco_teste: Path, tmp_path: Path, capsys):
    codigo = main(["auditoria", "--banco", str(banco_teste), "--amostra", "5", "--saida", str(tmp_path)])
    saida = capsys.readouterr().out
    assert codigo == 0
    assert ".xlsx" in saida and ".json" in saida
    assert "falhas: 0" in saida
    assert len(list(tmp_path.glob("auditoria_*.xlsx"))) == 1


def test_cli_auditoria_com_banco_inexistente_sai_com_dois(tmp_path: Path, capsys):
    assert main(["auditoria", "--banco", str(tmp_path / "nao_existe.db"), "--saida", str(tmp_path)]) == 2
    assert "não encontrado" in capsys.readouterr().err


def test_cli_revisao_com_divergencia_sai_com_um(banco_teste: Path, tmp_path: Path, capsys):
    main(["auditoria", "--banco", str(banco_teste), "--amostra", "3", "--saida", str(tmp_path)])
    planilha = next(tmp_path.glob("auditoria_*.xlsx"))
    assert main(["revisao", str(planilha)]) == 0  # só pendentes
    livro = load_workbook(planilha)
    livro["Amostra_revisao"].cell(row=2, column=list(COLUNAS_AMOSTRA).index("Conferido (S/N)") + 1, value="N")
    livro.save(planilha)
    capsys.readouterr()
    assert main(["revisao", str(planilha)]) == 1
    assert '"divergencias": [\n    "A01"\n  ]' in capsys.readouterr().out


def test_cli_servidor_chama_uvicorn_com_a_factory(banco_teste: Path, monkeypatch):
    chamadas = []
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: chamadas.append((args, kwargs)))
    monkeypatch.delenv("ORCAMENTO_PECAS_DB", raising=False)
    assert main(["servidor", "--port", "9000", "--banco", str(banco_teste)]) == 0
    (args, kwargs), = chamadas
    assert args == ("orcamento_pecas.api.app:criar_app",)
    assert kwargs == {"factory": True, "host": "127.0.0.1", "port": 9000, "reload": False}
    import os
    assert os.environ["ORCAMENTO_PECAS_DB"] == str(banco_teste)


def test_cli_revisao_com_valor_invalido_sai_com_um(banco_teste: Path, tmp_path: Path):
    main(["auditoria", "--banco", str(banco_teste), "--amostra", "3", "--saida", str(tmp_path)])
    planilha = next(tmp_path.glob("auditoria_*.xlsx"))
    livro = load_workbook(planilha)
    livro["Amostra_revisao"].cell(row=2, column=list(COLUNAS_AMOSTRA).index("Conferido (S/N)") + 1, value="talvez")
    livro.save(planilha)
    assert main(["revisao", str(planilha)]) == 1
