from decimal import Decimal

import pytest

from orcamento_pecas.dominio.normalizacao import (
    FaixaInterpretada,
    ano_compativel,
    corresponde_modelo,
    faixa_diverge_das_colunas,
    interpretar_faixa_ano,
    modelos_base,
    normalizar_ano_fim,
    normalizar_preco,
    normalizar_texto,
    numero_produto_base,
    segmentos_descricao,
)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("  frôntier   cd ", "FRONTIER CD"),
        ("Utilitários", "UTILITARIOS"),
        ("KICKS", "KICKS"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalizar_texto(entrada, esperado):
    assert normalizar_texto(entrada) == esperado


@pytest.mark.parametrize(
    ("descricao", "esperado"),
    [
        ("FRONTIER/ PATHFINDER", ["FRONTIER", "PATHFINDER"]),
        ("KICKS / MARCH / VERSA", ["KICKS", "MARCH", "VERSA"]),
        ("KICKS RIO 2016<br>KICKS SL<br>", ["KICKS RIO 2016", "KICKS SL"]),
        ("FRONTIER CD SE TDI 4X4", ["FRONTIER CD SE TDI 4X4"]),
    ],
)
def test_segmentos_descricao(descricao, esperado):
    assert segmentos_descricao(descricao) == esperado


def test_modelos_base_sao_a_primeira_palavra_de_cada_segmento_sem_repetir():
    assert modelos_base("KICKS RIO 2016<br>KICKS SL<br>MARCH S<br>") == ["KICKS", "MARCH"]
    assert modelos_base("X-TERRA SE 2.8 TDI 4X4") == ["X-TERRA"]


@pytest.mark.parametrize(
    ("descricao", "modelo", "tipo", "confianca"),
    [
        ("FRONTIER CD SE TDI 4X4", "frontier ", "inicio_segmento", "alta"),
        ("FRONTIER CD SE TDI 4X4", "Frontier", "inicio_segmento", "alta"),
        ("FRONTIER CD SE TDI 4X4", "FRÔNTIER", "inicio_segmento", "alta"),
        ("FRONTIER", "FRONTIER", "inicio_segmento", "alta"),
        ("FRONTIER SL 4X4 AT", "frontier sl", "inicio_segmento", "alta"),
        ("FRONTIER/ PATHFINDER", "pathfinder", "inicio_segmento", "alta"),
        ("KICKS / MARCH / VERSA", "MARCH", "inicio_segmento", "alta"),
        ("KICKS RIO 2016<br>KICKS SL", "kicks", "inicio_segmento", "alta"),
        ("FRONTIER CD SE TDI 4X4", "SE", "palavra_interna", "baixa"),
        ("FRONTIER CD SE TDI 4X4", "cd se", "palavra_interna", "baixa"),
    ],
)
def test_corresponde_modelo(descricao, modelo, tipo, confianca):
    correspondencia = corresponde_modelo(descricao, modelo)
    assert correspondencia is not None
    assert (correspondencia.tipo, correspondencia.confianca) == (tipo, confianca)


@pytest.mark.parametrize(
    ("descricao", "modelo"),
    [
        ("MARCHA X", "MARCH"),
        ("UNIVERSAL", "VERSA"),
        ("FRONTIERS", "FRONTIER"),
        ("X-TERRA SE", "X"),
        ("FRONTIER", ""),
        ("FRONTIER", "   "),
    ],
)
def test_nao_corresponde_modelo(descricao, modelo):
    assert corresponde_modelo(descricao, modelo) is None


@pytest.mark.parametrize(
    ("faixa", "esperado"),
    [
        ("2017-2022", FaixaInterpretada(2017, 2022, True)),
        ("2005-...", FaixaInterpretada(2005, None, True)),
        ("2013-…", FaixaInterpretada(2013, None, True)),
        ("2020--", FaixaInterpretada(2020, None, True)),
        ("…-2014", FaixaInterpretada(None, 2014, True)),
        ("abc", FaixaInterpretada(None, None, False)),
        ("", FaixaInterpretada(None, None, False)),
    ],
)
def test_interpretar_faixa_ano(faixa, esperado):
    assert interpretar_faixa_ano(faixa) == esperado


@pytest.mark.parametrize(
    ("faixa", "inicio", "fim", "diverge"),
    [
        ("2013-…", 2013, 2013, True),      # APLICACAO 32609
        ("2020--", 2020, 2020, True),      # APLICACAO 34590
        ("…-2014", 2014, 2014, True),      # APLICACAO 32452
        ("2005-...", 2005, None, False),   # APLICACAO 31393: as duas abertas
        ("2017-2022", 2017, 2022, False),
        ("2017-2022", 2017, 2023, True),
        ("abc", 2017, 2022, False),        # não interpretada tem alerta próprio
    ],
)
def test_faixa_diverge_das_colunas(faixa, inicio, fim, diverge):
    assert faixa_diverge_das_colunas(interpretar_faixa_ano(faixa), inicio, fim) is diverge


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(2008, 2008), ("", None), (None, None), ("2014", 2014), ("abc", None), (" ", None)],
)
def test_normalizar_ano_fim(valor, esperado):
    assert normalizar_ano_fim(valor) == esperado


@pytest.mark.parametrize(
    ("ano", "inicio", "fim", "compativel"),
    [
        (2008, 2006, 2008, True),   # borda final
        (2008, 2008, 2013, True),   # borda inicial
        (2008, 2009, 2013, False),
        (2014, 2006, 2013, False),
        (2008, 2005, None, True),   # faixa aberta (decisão D2)
        (2004, 2005, None, False),
    ],
)
def test_ano_compativel(ano, inicio, fim, compativel):
    assert ano_compativel(ano, inicio, fim) is compativel


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(66.84, Decimal("66.84")), (11.1, Decimal("11.1")), (547.28, Decimal("547.28")), (None, None)],
)
def test_normalizar_preco_sem_arredondar(valor, esperado):
    assert normalizar_preco(valor) == esperado


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [("#NAC_55.455.007", "55.455.007"), ("55.455.007", "55.455.007"), (" #NAC_X ", "X")],
)
def test_numero_produto_base(numero, esperado):
    assert numero_produto_base(numero) == esperado
