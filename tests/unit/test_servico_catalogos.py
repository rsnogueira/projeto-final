from orcamento_pecas.dominio.alertas import CodigoAlerta
from orcamento_pecas.dominio.modelos import Fonte
from orcamento_pecas.servicos.catalogos import ServicoCatalogos

FONTE = Fonte(banco="base_teste.db", sha256="0" * 64)


def test_fabricantes_com_quantidade_e_evidencia(repo):
    r = ServicoCatalogos(repo, FONTE).fabricantes()
    assert [(f.codigo_fabricante, f.descricao.normalizado, f.quantidade_aplicacoes) for f in r.dados] == [
        (2, "FIAT", 0), (3, "FORD", 0), (73, "NISSAN", 27),
    ]
    assert r.dados[2].descricao.evidencia.chave == {"CodigoFabricante": 73}
    sem_veiculos = next(a for a in r.alertas if a.codigo == CodigoAlerta.FABRICANTE_SEM_VEICULOS)
    assert sem_veiculos.contexto["fabricantes"] == ["FIAT", "FORD"]
    assert r.total == 3


def test_grupos_de_produto(repo):
    r = ServicoCatalogos(repo, FONTE).grupos()
    assert [(g.codigo_grupo_produto, g.quantidade_produtos) for g in r.dados] == [(7, 4), (16, 0), (24, 1), (39, 8)]
    assert r.dados[0].descricao.normalizado == "GUIAS DE VALVULA"
    assert r.dados[0].descricao.original == "GUIAS DE VÁLVULA"


def test_saude(repo):
    saude = ServicoCatalogos(repo, FONTE).saude()
    assert saude.status == "ok"
    assert saude.somente_leitura is True
    assert saude.sha256 == FONTE.sha256
    assert saude.banco == FONTE.banco
    assert saude.contagens["APLICACAO"] == 27
