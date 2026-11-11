# Dados: dicionário, regras e problemas conhecidos

Fonte única: `Database/SQLite/db_proj_final.db`, aberta com `mode=ro` e `PRAGMA query_only = ON`. O código nunca altera a base. O modelo ER está em `Documentacao/MER/modelo_ER_Proj_v1.png`.

## Tabelas e colunas

| Tabela | Linhas | Colunas usadas e como são tratadas |
|---|---|---|
| `APLICACAO` (veículos) | 131 | `CodigoAplicacao` é a chave. `DescricaoAplicacao`, `FaixaAno`, `AnoInicioFabricacao`, `AnoFimFabricacao`, `Motorizacao` e `Combustivel` são interpretadas (ver regras abaixo). Também usa `CodigoFabricante` e `CodigoTipoAplicacao`. |
| `FABRICANTE` | 12 | `CodigoFabricante`, `DescricaoFabricante`. Só a NISSAN (73) tem aplicações. |
| `TIPOAPLICACAO` | 9 | `CodigoTipoAplicacao`, `DescricaoTipoAplicacao` (Leves, Pesados, Utilitários…). |
| `PRODUTO` (peças) | 5.944 | `DescricaoProduto`, `CodigoGrupoProduto`, `PrecoProduto`, `NumeroProduto`, `QtdEmbalagem`. **Não interpretadas** (pendência P2): `CodigoSimilar`, `CpoAuxProd5`, `CpoAuxProd25`, `PCs`, `NumeroProdutoPesq`, que só aparecem em `campos_nao_interpretados` no detalhe do produto. |
| `GRUPOPRODUTO` | 27 | `CodigoGrupoProduto`, `DescricaoGrupoProduto` (ex.: 39 = BRONZINA). |
| `PRODUTO_APLICACAO` | 1.438 | Vínculo peça × aplicação. A chave composta é (`CodigoProduto`, `CodigoAplicacao`). |

## Regras de normalização

O valor original nunca é alterado. As regras abaixo só geram o valor normalizado.

| Regra | Como funciona |
|---|---|
| **Texto** | Maiúsculas, sem acentos, espaços colapsados. Texto vazio vira `null`. |
| **Modelo** | A descrição é quebrada em `<br>` e `/`, gerando segmentos. Se um segmento for igual ao modelo ou começar por `modelo + espaço`, a correspondência é `inicio_segmento` (confiança alta). Se o modelo aparecer como palavras inteiras no meio de um segmento, é `palavra_interna` (confiança baixa, com alerta). `MARCH` não casa com `MARCHA`. |
| **Modelo-base** (derivado) | A primeira palavra de cada segmento. Serve só para listar modelos disponíveis e montar a bateria da auditoria. Limitação: "GRAND LIVINA" gera "GRAND" (pendência P11). |
| **Ano final** | Inteiro é usado como está. `''`, `NULL` ou texto vira `null`. A compatibilidade é `inicio ≤ ano ≤ fim`, com bordas inclusivas. Sem fim, vale `ano ≥ inicio` (decisão D2, com alerta). |
| **FaixaAno** | Serve só para comparar com as colunas de ano. Formatos reconhecidos: `AAAA-AAAA`, `AAAA-...`, `AAAA-…`, `AAAA--` e `…-AAAA`. Qualquer diferença em relação às colunas gera `FAIXA_ANO_DIVERGENTE`. |
| **Motorização** | Decomposta em códigos (o texto antes da cilindrada, separado por `/`, sem a palavra genérica "MOTOR"), cilindrada (`\d.\d`), válvulas (`NNV`), cilindros (`L4`, `L3`…) e comando (DOHC, SOHC, OHV). A chave é estrita: `códigos\|cilindrada\|válvulas\|cilindros\|comando`, com `?` em cada atributo ausente. `HR16` e `HR16DE` **não** se juntam. |
| **Preço** | `Decimal` exato a partir do número, sem arredondar. `NULL` vira `null`, com `PRECO_AUSENTE`. |
| **Número-base** | O número sem o prefixo literal `#NAC_`. É usado **apenas** para detectar possível duplicidade. |

Exemplos de motorização. Os 29 textos distintos da base estão fixados em `tests/unit/test_motorizacao.py`.

| Original | Chave |
|---|---|
| `HR16DE - 1.6L 16V DOHC L4` | `HR16DE\|1.6\|16V\|L4\|DOHC` |
| `HR16DE 1.6 16V L4 DOHC` | `HR16DE\|1.6\|16V\|L4\|DOHC` |
| `4.07 TCE SPRINT 2.8 12V L4 SOHC` | `4.07 TCE SPRINT\|2.8\|12V\|L4\|SOHC` |
| `YD25DDTI / YD25ETI 2.5L 16V DOHC L4` | `YD25DDTI+YD25ETI\|2.5\|16V\|L4\|DOHC` |
| `YD25 SELL 2.5L 16V` | `YD25 SELL\|2.5\|16V\|?\|?` |
| `- 2.5 L 16V DOHC L4` | `?\|2.5\|16V\|L4\|DOHC` |
| `MOTOR 1.6 16V` | `?\|1.6\|16V\|?\|?` |

## Problemas conhecidos

Números medidos pela auditoria de 2026-11-10 na base com SHA-256 `8a700b84…cd2a`:

| Problema | Medida | Tratamento |
|---|---|---|
| Preço ausente | 4.047 de 5.944 produtos no total. Entre os 182 produtos vinculados a veículos, **131 sem preço**. | `PRECO_AUSENTE` (revisão) |
| Possível duplicidade `#NAC_` | **Os 182 produtos vinculados formam 91 pares** (ex.: 6809 `55.455.007` × 11837 `#NAC_55.455.007`). | `POSSIVEL_PRODUTO_DUPLICADO` (revisão), sem mesclar |
| Vínculos órfãos | 212 vínculos, de 78 produtos, para 20 aplicações inexistentes (excluídas na migração). | `VINCULO_ORFAO` (revisão) |
| Combustível conflitante | 22 aplicações do KICKS com o motor HR16DE 1.6 em FLEX e em GASOLINA. | `COMBUSTIVEL_CONFLITANTE` (revisão) |
| FaixaAno divergente | 5 aplicações (ex.: 32609 `2013-…` com fim 2013, 32452 `…-2014`). | `FAIXA_ANO_DIVERGENTE` (revisão) |
| Ano final ausente | 3 aplicações (31393, 31483, 36312). | `ANO_FIM_AUSENTE` (revisão), entram na busca |
| Motorização sem código ou composta | 2 sem código (35374, 32452) e 2 compostas (36311, 36312). | alertas de revisão |
| Descrição composta | 11 aplicações com `/` ou `<br>`. | `DESCRICAO_COMPOSTA` (atenção) |
| Cobertura | Só a NISSAN tem veículos. Duplicatas exatas em `APLICACAO`: 0. Há, porém, registros sobrepostos, em que o mesmo veículo aparece descrito de formas diferentes. | `FABRICANTE_SEM_VEICULOS`; os candidatos não se mesclam |

As decisões pendentes estão em [pendencias.md](pendencias.md).
