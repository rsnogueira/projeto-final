import pytest

from orcamento_pecas.dominio.alertas import CodigoAlerta, criar_alerta, revisao_humana
from orcamento_pecas.dominio.modelos import Evidencia


@pytest.mark.parametrize("codigo", list(CodigoAlerta))
def test_todo_codigo_pode_ser_criado_com_severidade_e_mensagem(codigo):
    alerta = criar_alerta(codigo)
    assert alerta.severidade in {"info", "atencao", "revisao"}
    assert alerta.mensagem.strip()


def test_severidades_que_exigem_revisao():
    assert criar_alerta(CodigoAlerta.PRECO_AUSENTE).severidade == "revisao"
    assert criar_alerta(CodigoAlerta.COMBUSTIVEL_CONFLITANTE).severidade == "revisao"
    assert criar_alerta(CodigoAlerta.ANO_FIM_AUSENTE).severidade == "revisao"
    assert criar_alerta(CodigoAlerta.MULTIPLOS_COMBUSTIVEIS).severidade == "atencao"
    assert criar_alerta(CodigoAlerta.MOTOR_NAO_IDENTIFICADO).severidade == "atencao"


def test_severidade_pode_ser_elevada_pelo_contexto():
    assert criar_alerta(CodigoAlerta.MOTOR_NAO_IDENTIFICADO, severidade="revisao").severidade == "revisao"


def test_alerta_guarda_evidencias_e_contexto():
    evidencia = Evidencia(tabela="PRODUTO", chave={"CodigoProduto": 6809}, coluna="PrecoProduto", valor_original=None)
    alerta = criar_alerta(CodigoAlerta.PRECO_AUSENTE, [evidencia], codigos_produto=[6809])
    assert alerta.evidencias == [evidencia]
    assert alerta.contexto == {"codigos_produto": [6809]}


def test_revisao_necessaria_somente_com_alerta_de_revisao():
    assert revisao_humana([criar_alerta(CodigoAlerta.MULTIPLOS_COMBUSTIVEIS)]).necessaria is False
    assert revisao_humana([]).necessaria is False
    resultado = revisao_humana([
        criar_alerta(CodigoAlerta.MULTIPLOS_COMBUSTIVEIS),
        criar_alerta(CodigoAlerta.PRECO_AUSENTE),
        criar_alerta(CodigoAlerta.ANO_FIM_AUSENTE),
        criar_alerta(CodigoAlerta.PRECO_AUSENTE),
    ])
    assert resultado.necessaria is True
    assert resultado.motivos == [CodigoAlerta.PRECO_AUSENTE, CodigoAlerta.ANO_FIM_AUSENTE]


def test_severidades_ajustadas_na_revisao_final():
    assert criar_alerta(CodigoAlerta.CORRESPONDENCIA_PARCIAL_MODELO).severidade == "revisao"
    assert criar_alerta(CodigoAlerta.DADO_AUSENTE).severidade == "revisao"
    assert criar_alerta(CodigoAlerta.PECAS_NAO_ENCONTRADAS).severidade == "revisao"
    assert criar_alerta(CodigoAlerta.PRECO_SUSPEITO).severidade == "revisao"
