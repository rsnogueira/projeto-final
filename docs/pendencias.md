# Registro de pendências

Itens que dependem de decisão humana, de dado ausente ou de correção na origem. A API **não** corrige nada disso: ela sinaliza com alertas e exige revisão. Os números vêm da auditoria de 2026-11-10 (base com SHA-256 `8a700b84…cd2a`).

Status possíveis: `aberta`, `em análise`, `resolvida`.

| ID | Tipo | Pendência | Evidência | Impacto | Status |
|---|---|---|---|---|---|
| P1 | dado ausente | `PrecoProduto` nulo em 4.047 de 5.944 produtos. Entre os 182 vinculados a veículos, **131 sem preço**, inclusive todas as bronzinas do Frontier 2008. | `PRODUTO.PrecoProduto` | Orçamento sem valor; `PRECO_AUSENTE` | aberta |
| P2 | decisão do usuário | Significado de `CodigoSimilar`, `CpoAuxProd5`, `CpoAuxProd25`, `PCs` e `NumeroProdutoPesq`. | `PRODUTO` | Expostos só como `campos_nao_interpretados` | aberta |
| P3 | decisão do usuário | Moeda e unidade do preço: por peça ou por embalagem (`QtdEmbalagem`)? | `PRODUTO.PrecoProduto`, `PRODUTO.QtdEmbalagem` | Preço exibido sem moeda nem unidade | aberta |
| P4 | ambiguidade | **Os 182 produtos vinculados formam 91 pares** "número" × "`#NAC_`número" com a mesma descrição. Qual vale? São itens diferentes (ex.: nacional × importado) ou duplicatas? | ex.: 6809 `55.455.007` × 11837 `#NAC_55.455.007` | `POSSIVEL_PRODUTO_DUPLICADO` em toda listagem de peças | aberta |
| P5 | integridade | 212 vínculos, de 78 produtos, para 20 aplicações inexistentes (excluídas na migração). | `PRODUTO_APLICACAO.CodigoAplicacao` | `VINCULO_ORFAO` na auditoria e no detalhe do produto | aberta |
| P6 | ambiguidade | 3 aplicações sem ano final: o veículo ainda é fabricado ou o dado é desconhecido? | `APLICACAO` 31393, 31483, 36312 | Entram na busca com `ANO_FIM_AUSENTE` (decisão D2). Ex.: o motor M9T 2.3 vira candidato do Frontier 2008 só por causa de 31393 (`2005-...`) | aberta |
| P7 | conflito | `FaixaAno` diverge das colunas de ano em 5 aplicações. | ex.: 32609 (`2013-…`, fim 2013), 32452 (`…-2014`), 34590 (`2020--`, fim 2020) | `FAIXA_ANO_DIVERGENTE` | aberta |
| P8 | ambiguidade | Motorizações sem código (35374 `- 2.5 L 16V DOHC L4`, 32452 `MOTOR 1.6 16V`) ou compostas (36311 e 36312 `YD25DDTI / YD25ETI`). | `APLICACAO.Motorizacao` | `MOTORIZACAO_SEM_CODIGO` e `MOTORIZACAO_COMPOSTA` | aberta |
| P9 | conflito | KICKS: 22 aplicações com o mesmo motor HR16DE 1.6 em FLEX e em GASOLINA. | ex.: 31383 (FLEX) × 15365 (GASOLINA) | `COMBUSTIVEL_CONFLITANTE`; o combustível precisa ser confirmado | aberta |
| P10 | cobertura | Só a NISSAN tem veículos. Os outros 11 fabricantes não têm aplicações. | `APLICACAO.CodigoFabricante` | `FABRICANTE_SEM_VEICULOS` | aberta |
| P11 | modelagem | Não há coluna de modelo. As descrições misturam modelo e versão, trazem vários modelos ou HTML (`<br>`). O modelo-base derivado erra em nomes compostos ("GRAND LIVINA" vira "GRAND"). Uma tabela de-para curada (abordagem 3 do plano) resolveria. | `APLICACAO.DescricaoAplicacao`, ex.: 15569, 34564 | Correspondência por texto, com confiança e alertas | aberta |
| P12 | documentação | `readme.md` é o modelo acadêmico e cabe ao aluno preenchê-lo. | `readme.md` | — | aberta |
| P13 | versionamento | `.mcp.json` (servidor fipex, fora do escopo da v1) passou a ser versionado a pedido do usuário. Falta decidir sobre `.claude/settings.json`. | `git status` | — | em análise |
| P14 | revisão humana | Revisar a amostra de 30 itens (15 com alerta e 15 limpos) da auditoria da base real e rodar o comando `revisao`. | `saidas/auditoria/auditoria_20261110-210403.xlsx` | A conclusão técnica não depende disso; a confiança nos dados, sim | aberta |
| P15 | técnica | A correspondência de modelo percorre em Python todas as aplicações do fabricante a cada consulta. Com 131 aplicações isso é instantâneo; se a base crescer muito (milhares por fabricante), avaliar um índice em memória (abordagem 2 do plano). | `servicos/veiculos.py` | Desempenho | aberta |
