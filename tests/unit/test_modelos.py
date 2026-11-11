import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from orcamento_pecas.dominio.alertas import CodigoAlerta, criar_alerta
from orcamento_pecas.dominio.evidencias import valor_de
from orcamento_pecas.dominio.modelos import DadosMotorizacoes, Evidencia, Resposta, ValorRastreado

EVIDENCIA_ANO_FIM = Evidencia(tabela="APLICACAO", chave={"CodigoAplicacao": 31393}, coluna="AnoFimFabricacao", valor_original="")


def test_none_serializa_como_null_e_nao_como_valor_padrao():
    valor = ValorRastreado[int](original="", normalizado=None, evidencia=EVIDENCIA_ANO_FIM)
    assert valor.model_dump(mode="json") == {
        "original": "",
        "normalizado": None,
        "evidencia": {"tabela": "APLICACAO", "chave": {"CodigoAplicacao": 31393}, "coluna": "AnoFimFabricacao", "valor_original": ""},
    }
    assert '"normalizado":null' in valor.model_dump_json()


def test_valor_rastreado_exige_evidencia():
    with pytest.raises(ValidationError):
        ValorRastreado[int](original=2008, normalizado=2008)


def test_evidencia_rejeita_tabela_desconhecida():
    with pytest.raises(ValidationError):
        Evidencia(tabela="OUTRA", chave={"Id": 1}, coluna="X", valor_original=1)


def test_decimal_serializa_sem_perder_casas():
    evidencia = Evidencia(tabela="PRODUTO", chave={"CodigoProduto": 5580}, coluna="PrecoProduto", valor_original=11.1)
    valor = ValorRastreado[Decimal](original=11.1, normalizado=Decimal("547.28"), evidencia=evidencia)
    assert valor.model_dump(mode="json")["normalizado"] == "547.28"


def test_json_preserva_acentos():
    alerta = criar_alerta(CodigoAlerta.PRECO_AUSENTE, contexto_extra="Utilitários")
    assert "Utilitários" in alerta.model_dump_json()
    assert "preço" in json.loads(alerta.model_dump_json())["mensagem"].lower()
    assert "\\u" not in alerta.model_dump_json()


def test_valor_de_monta_evidencia_a_partir_da_linha(repo):
    linha = repo.obter_aplicacao(31393)
    valor = valor_de(linha, "APLICACAO", {"CodigoAplicacao": 31393}, "AnoFimFabricacao", None)
    assert valor.original == ""
    assert valor.normalizado is None
    assert valor.evidencia == EVIDENCIA_ANO_FIM


def test_esquema_da_resposta_de_motorizacoes_e_gerado():
    esquema = Resposta[DadosMotorizacoes].model_json_schema()
    assert {"consulta", "dados", "total", "alertas", "revisao_humana", "fonte"} <= set(esquema["properties"])
