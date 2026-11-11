"""Catálogos (fabricantes, grupos de produto) e estado do serviço."""

from orcamento_pecas.dados.repositorio import Repositorio
from orcamento_pecas.dominio.alertas import CodigoAlerta, criar_alerta
from orcamento_pecas.dominio.evidencias import valor_de
from orcamento_pecas.dominio.modelos import DadosSaude, Fonte, ItemFabricante, ItemGrupoProduto, Resposta
from orcamento_pecas.dominio.normalizacao import normalizar_texto
from orcamento_pecas.servicos.comum import montar_resposta


class ServicoCatalogos:
    def __init__(self, repo: Repositorio, fonte: Fonte) -> None:
        self.repo = repo
        self.fonte = fonte

    def fabricantes(self) -> Resposta:
        itens = []
        for linha in self.repo.listar_fabricantes():
            descricao = valor_de(linha, "FABRICANTE", {"CodigoFabricante": linha["CodigoFabricante"]}, "DescricaoFabricante",
                                 normalizar_texto(linha["DescricaoFabricante"]))
            itens.append(ItemFabricante(
                codigo_fabricante=linha["CodigoFabricante"], descricao=descricao, quantidade_aplicacoes=linha["QuantidadeAplicacoes"],
            ))
        sem_veiculos = [i for i in itens if i.quantidade_aplicacoes == 0]
        alertas = []
        if sem_veiculos:
            alertas.append(criar_alerta(
                CodigoAlerta.FABRICANTE_SEM_VEICULOS,
                [i.descricao.evidencia for i in sem_veiculos],
                fabricantes=[i.descricao.normalizado for i in sem_veiculos],
            ))
        return montar_resposta({}, itens, len(itens), alertas, self.fonte)

    def grupos(self) -> Resposta:
        itens = []
        for linha in self.repo.listar_grupos_produto():
            descricao = valor_de(linha, "GRUPOPRODUTO", {"CodigoGrupoProduto": linha["CodigoGrupoProduto"]},
                                 "DescricaoGrupoProduto", normalizar_texto(linha["DescricaoGrupoProduto"]))
            itens.append(ItemGrupoProduto(
                codigo_grupo_produto=linha["CodigoGrupoProduto"], descricao=descricao, quantidade_produtos=linha["QuantidadeProdutos"],
            ))
        return montar_resposta({}, itens, len(itens), [], self.fonte)

    def saude(self) -> DadosSaude:
        return DadosSaude(
            status="ok",
            banco=self.fonte.banco,
            somente_leitura=self.repo.somente_leitura(),
            sha256=self.fonte.sha256,
            contagens=self.repo.contagens(),
        )
