import sqlite3
from pathlib import Path

import pytest

from orcamento_pecas.dominio.normalizacao import interpretar_motorizacao

# Os 29 textos distintos de APLICACAO.Motorizacao na base real (2026-11-10),
# com a chave esperada derivada à mão a partir das regras do plano (seção 1.5).
CASOS_REAIS = {
    "- 2.5 L 16V DOHC L4": "?|2.5|16V|L4|DOHC",
    "4.07 TCA SPRINT 2.8 12V L4 SOHC": "4.07 TCA SPRINT|2.8|12V|L4|SOHC",
    "4.07 TCE SPRINT 2.8 12V L4 SOHC": "4.07 TCE SPRINT|2.8|12V|L4|SOHC",
    "CVVTCS 1.6 L 16V DOHC L4": "CVVTCS|1.6|16V|L4|DOHC",
    "CVVTCS 1.8 L 16V DOHC L4": "CVVTCS|1.8|16V|L4|DOHC",
    "CVVTCS 2.0 L 16V DOHC L4": "CVVTCS|2.0|16V|L4|DOHC",
    "D4D 1.0 L 16V DOHC L4": "D4D|1.0|16V|L4|DOHC",
    "D4D HI-POWER 1.0 16V L4 SOHC": "D4D HI-POWER|1.0|16V|L4|SOHC",
    "HR10 1.0 12V L3 DOHC": "HR10|1.0|12V|L3|DOHC",
    "HR16 - 1.6 L 16V DOHC L4": "HR16|1.6|16V|L4|DOHC",
    "HR16 - 1.6L 16V DOHC L4": "HR16|1.6|16V|L4|DOHC",
    "HR16 1.6 L 16V DOHC L4": "HR16|1.6|16V|L4|DOHC",
    "HR16DE - 1.6 L 16V DOHC L4": "HR16DE|1.6|16V|L4|DOHC",
    "HR16DE - 1.6L 16V DOHC L4": "HR16DE|1.6|16V|L4|DOHC",
    "HR16DE 1.6 16V L4 DOHC": "HR16DE|1.6|16V|L4|DOHC",
    "HR16DE 1.6 L 16V DOHC L4": "HR16DE|1.6|16V|L4|DOHC",
    "K4M - 1.6 L 16V DOHC L4": "K4M|1.6|16V|L4|DOHC",
    "K4M 1.6 16V L4 DOHC": "K4M|1.6|16V|L4|DOHC",
    "M9T - 2.3L 16V DOHC L4": "M9T|2.3|16V|L4|DOHC",
    "MOTOR 1.6 16V": "?|1.6|16V|?|?",
    "MR18DE 1.8 16V L4 DOHC": "MR18DE|1.8|16V|L4|DOHC",
    "SPRINT EURO 2 2.8 L 12V SOHC L4": "SPRINT EURO 2|2.8|12V|L4|SOHC",
    "SPRINT EURO 3 2.8 L 12V SOHC L4": "SPRINT EURO 3|2.8|12V|L4|SOHC",
    "YD25 SELL 2.5L 16V": "YD25 SELL|2.5|16V|?|?",
    "YD25DDTI / YD25ETI 2.5L 16V DOHC L4": "YD25DDTI+YD25ETI|2.5|16V|L4|DOHC",
    "YD25DDTI 2.5 L 16V DOHC L4": "YD25DDTI|2.5|16V|L4|DOHC",
    "YD25DDTI 2.5L 16V": "YD25DDTI|2.5|16V|?|?",
    "YD25ETI 2.5 16V L4 DOHC": "YD25ETI|2.5|16V|L4|DOHC",
    "YD25ETI 2.5 L 16V DOHC L4": "YD25ETI|2.5|16V|L4|DOHC",
}


@pytest.mark.parametrize(("texto", "chave"), sorted(CASOS_REAIS.items()))
def test_todas_as_motorizacoes_reais_interpretadas(texto, chave):
    motor = interpretar_motorizacao(texto)
    assert motor.interpretada is True
    assert motor.chave == chave


def test_atributos_decompostos():
    motor = interpretar_motorizacao("HR16DE - 1.6L 16V DOHC L4")
    assert motor.codigos == ["HR16DE"]
    assert motor.cilindrada_l == "1.6"
    assert motor.valvulas == 16
    assert motor.cilindros == "L4"
    assert motor.comando == "DOHC"


def test_motorizacao_composta_tem_dois_codigos():
    motor = interpretar_motorizacao("YD25DDTI / YD25ETI 2.5L 16V DOHC L4")
    assert motor.codigos == ["YD25DDTI", "YD25ETI"]
    assert motor.composta is True
    assert motor.sem_codigo is False


def test_motorizacao_sem_codigo():
    for texto in ("- 2.5 L 16V DOHC L4", "MOTOR 1.6 16V"):
        motor = interpretar_motorizacao(texto)
        assert motor.codigos == []
        assert motor.sem_codigo is True


def test_cilindrada_nao_confunde_4_07():
    motor = interpretar_motorizacao("4.07 TCE SPRINT 2.8 12V L4 SOHC")
    assert motor.cilindrada_l == "2.8"
    assert motor.codigos == ["4.07 TCE SPRINT"]


def test_atributos_ausentes_ficam_none():
    motor = interpretar_motorizacao("YD25 SELL 2.5L 16V")
    assert (motor.cilindros, motor.comando) == (None, None)


def test_sem_cilindrada_nao_interpretada():
    motor = interpretar_motorizacao("DIESEL TURBO")
    assert motor.interpretada is False
    assert motor.codigos == []
    assert motor.cilindrada_l is None
    assert motor.chave == "TEXTO:DIESEL TURBO"


@pytest.mark.base_real
def test_casos_cobrem_todas_as_motorizacoes_da_base_real(banco_real: Path):
    conexao = sqlite3.connect(f"file:{banco_real.as_posix()}?mode=ro", uri=True)
    try:
        distintas = {linha[0] for linha in conexao.execute("SELECT DISTINCT Motorizacao FROM APLICACAO")}
    finally:
        conexao.close()
    assert distintas == set(CASOS_REAIS)
