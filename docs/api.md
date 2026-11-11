# API de consulta — v1

Microserviço FastAPI, **somente leitura**, sobre `Database/SQLite/db_proj_final.db`. A documentação interativa (Swagger) fica em `http://127.0.0.1:8000/docs` com o servidor no ar.

## Como executar

```powershell
# servidor (só em 127.0.0.1 por padrão)
.venv\Scripts\python.exe -m orcamento_pecas servidor [--port 8000] [--banco <caminho>] [--reload]

# equivalente direto com o Uvicorn
.venv\Scripts\python.exe -m uvicorn --factory orcamento_pecas.api.app:criar_app
```

O caminho do banco tem esta prioridade: `--banco`, depois a variável `ORCAMENTO_PECAS_DB`, depois `Database/SQLite/db_proj_final.db`. Se o arquivo não existir, o serviço não sobe.

## Endpoints (prefixo `/v1`)

| Rota | Parâmetros | Para que serve |
|---|---|---|
| `GET /saude` | — | Banco acessível, `somente_leitura`, SHA-256 e contagem por tabela. |
| `GET /fabricantes` | — | Fabricantes e a quantidade de aplicações de cada um. |
| `GET /grupos-produto` | — | Grupos de peça (ex.: 39 = BRONZINA) e a quantidade de produtos. |
| `GET /veiculos` | `modelo`, `ano`, `fabricante`, `combustivel` (todos opcionais), `pagina`, `limite` | Busca paginada de aplicações. |
| **`GET /veiculos/motorizacoes`** | `modelo`\*, `ano`\*, `fabricante`, `combustivel` | Motores candidatos para modelo e ano. Diz se o motor está `identificado`. |
| **`GET /veiculos/combustiveis`** | `modelo`\*, `ano`\*, `fabricante` | Combustíveis distintos para modelo e ano, com conflitos. |
| `GET /veiculos/{codigo_aplicacao}` | — | Detalhe de uma aplicação. |
| `GET /veiculos/{codigo_aplicacao}/pecas` | `grupo`, `texto` | Peças da aplicação (equivale a `qry_produto_por_veiculo.sql`, filtrada). |
| `GET /pecas` | `modelo`\*, `ano`\*, `chave_motor`, `fabricante`, `combustivel`, `grupo`, `texto`, `pagina`, `limite` | Peças compatíveis com o veículo ou com o motor. |
| `GET /pecas/{codigo_produto}` | — | Detalhe do produto: aplicações, vínculos órfãos e campos não interpretados. |

\* obrigatório.

**Validação dos parâmetros:**
- `ano` é inteiro de 4 dígitos.
- `limite` tem padrão 50 e máximo 200.
- `modelo` precisa ter ao menos um caractere que não seja espaço.
- Parâmetro inválido devolve **422**. Código inexistente devolve **404**.

## Formato das respostas

Toda resposta (menos `/saude`) usa o mesmo envelope:

```json
{
  "consulta": {"modelo": {"original": "frontier", "normalizado": "FRONTIER"}, "ano": {"original": 2008, "normalizado": 2008},
               "fabricante": {"original": null, "normalizado": null}, "combustivel": {"original": null, "normalizado": null}},
  "dados": "…",
  "total": 6,
  "pagina": null,
  "limite": null,
  "alertas": ["…"],
  "revisao_humana": {"necessaria": true, "motivos": ["ANO_FIM_AUSENTE", "MOTORIZACAO_COMPOSTA"]},
  "fonte": {"banco": "Database/SQLite/db_proj_final.db", "sha256": "8a700b84124cefe12332e115d73da458f29082d57d627f5c5b0b8064b9d7cd2a"}
}
```

Cada valor vindo da base é um **valor rastreado**: o original, o normalizado (`null` quando ausente) e a evidência. Exemplo real, a aplicação 31393, que não tem ano final:

```json
{"original": "", "normalizado": null,
 "evidencia": {"tabela": "APLICACAO", "chave": {"CodigoAplicacao": 31393}, "coluna": "AnoFimFabricacao", "valor_original": ""}}
```

O **preço** é devolvido exatamente como está na base. O `original` vem como número e o `normalizado` como texto decimal exato (ex.: `"11.1"`), sem arredondamento. A base não documenta moeda nem unidade (pendência P3).

`total` tem um significado em cada rota:
- em `motorizacoes`, é o número de motores candidatos;
- em `combustiveis`, o número de combustíveis distintos;
- nas listagens, o total antes da paginação.

## Exemplo: "Preciso de uma bronzina do Frontier 2008"

As respostas abaixo são reais, geradas na validação de 2026-11-10 e gravadas em `saidas/validacao/`.

**1. Motores do Frontier 2008:** `GET /v1/veiculos/motorizacoes?modelo=frontier&ano=2008`

O resultado é `identificado: false`, com **6 candidatos** em 14 aplicações:

| chave_motor | aplicações |
|---|---|
| `4.07 TCE SPRINT\|2.8\|12V\|L4\|SOHC` | 13760, 13761, 13762, 13763, 13764 |
| `M9T\|2.3\|16V\|L4\|DOHC` | 31393 (faixa `2005-...`, sem ano final) |
| `SPRINT EURO 3\|2.8\|12V\|L4\|SOHC` | 34828 |
| `YD25 SELL\|2.5\|16V\|?\|?` | 32415 |
| `YD25DDTI+YD25ETI\|2.5\|16V\|L4\|DOHC` | 36311 (motorização composta) |
| `YD25ETI\|2.5\|16V\|L4\|DOHC` | 13823, 13824, 13979, 35368, 35369 |

`atributos_distintivos` mostra o que diferencia os candidatos, para orientar as perguntas complementares:

```json
{"codigos": ["4.07 TCE SPRINT", "M9T", "SPRINT EURO 3", "YD25 SELL", "YD25DDTI+YD25ETI", "YD25ETI"],
 "cilindrada_l": ["2.3", "2.5", "2.8"], "valvulas": ["12", "16"], "cilindros": ["L4", null], "comando": ["DOHC", "SOHC", null],
 "versoes": ["FRONTIER", "FRONTIER / PATHFINDER", "FRONTIER CD SE 2.8 TDI 4X2", "…"]}
```

Alertas devolvidos:
- `ANO_FIM_AUSENTE` (revisão);
- `DESCRICAO_COMPOSTA` (atenção);
- `MOTORIZACAO_COMPOSTA` (revisão);
- `MOTOR_NAO_IDENTIFICADO` (atenção).

**2. Com o motor confirmado** (por exemplo, 2.5 YD25ETI): `GET /v1/pecas?modelo=frontier&ano=2008&grupo=39&chave_motor=YD25ETI|2.5|16V|L4|DOHC`

O resultado traz 6 bronzinas (6809, 6810, 6811, 11837, 11838, 11839), **todas sem preço**, com `revisao_humana.motivos = ["PRECO_AUSENTE", "POSSIVEL_PRODUTO_DUPLICADO"]`. Exemplo de item:

```json
{"codigo_produto": 6810,
 "descricao": {"original": "BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,25", "normalizado": "BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,25", "evidencia": {"…": "…"}},
 "grupo": {"original": "BRONZINA", "normalizado": "BRONZINA", "evidencia": {"tabela": "GRUPOPRODUTO", "chave": {"CodigoGrupoProduto": 39}, "…": "…"}},
 "numero_produto": {"original": "55.455.107", "normalizado": "55.455.107", "evidencia": {"…": "…"}},
 "preco": {"original": null, "normalizado": null, "evidencia": {"tabela": "PRODUTO", "chave": {"CodigoProduto": 6810}, "coluna": "PrecoProduto", "valor_original": null}},
 "qtd_embalagem": {"original": 1, "normalizado": 1, "evidencia": {"…": "…"}},
 "codigos_aplicacao": [35368, 35369]}
```

Sem `chave_motor`, a mesma busca traz também as bronzinas do motor 2.8 SPRINT, e o alerta `MOTOR_NAO_IDENTIFICADO` passa a ter severidade de **revisão**.

## Catálogo de alertas

**Severidade revisão** (liga `revisao_humana.necessaria`):

| Código | Quando acontece |
|---|---|
| `ANO_FIM_AUSENTE` | Ano final vazio. A aplicação entra como compatível a partir do ano inicial (decisão D2). |
| `FAIXA_ANO_DIVERGENTE` | O texto de `FaixaAno` diverge das colunas de ano. |
| `FAIXA_ANO_NAO_INTERPRETADA` | `FaixaAno` está num formato não reconhecido. |
| `MOTORIZACAO_SEM_CODIGO` | Motorização sem código de motor. |
| `MOTORIZACAO_COMPOSTA` | Motorização com mais de um código. |
| `MOTORIZACAO_NAO_INTERPRETADA` | Motorização sem cilindrada reconhecível. |
| `COMBUSTIVEL_CONFLITANTE` | Mesmo motor com combustíveis diferentes para o mesmo modelo e ano. |
| `PRECO_AUSENTE` | Peça sem preço na base. |
| `POSSIVEL_PRODUTO_DUPLICADO` | Mesma descrição e mesmo número-base (sem `#NAC_`). Os produtos não são mesclados. |
| `VINCULO_ORFAO` | Vínculo peça × aplicação aponta para uma aplicação inexistente. |
| `REFERENCIA_INEXISTENTE` | Chave estrangeira aponta para um registro inexistente. |

**Severidade atenção:**

| Código | Quando acontece |
|---|---|
| `MOTOR_NAO_IDENTIFICADO` | Há mais de um motor candidato. Em `/v1/pecas`, a severidade sobe para **revisão**. |
| `MULTIPLOS_COMBUSTIVEIS` | Há mais de um combustível para o modelo e ano. |
| `DESCRICAO_COMPOSTA` | A descrição reúne vários itens (`/` ou `<br>`). |
| `CORRESPONDENCIA_PARCIAL_MODELO` | O modelo só foi achado no meio da descrição (confiança baixa). |
| `MODELO_NAO_ENCONTRADO` | Nenhuma aplicação para o modelo. O contexto traz `modelos_disponiveis`. |
| `ANO_FORA_DO_INTERVALO` | O modelo existe, mas não no ano pedido. O contexto traz `faixas_disponiveis`. |
| `COMBUSTIVEL_NAO_ENCONTRADO` | Modelo e ano existem, mas não com esse combustível. O contexto traz os disponíveis. |
| `MOTOR_NAO_ENCONTRADO` | Nenhuma aplicação com a `chave_motor` informada. O contexto traz as chaves disponíveis. |
| `FABRICANTE_NAO_ENCONTRADO` | Fabricante desconhecido. O contexto traz os fabricantes disponíveis. |
| `FABRICANTE_SEM_VEICULOS` | O fabricante existe, mas não tem aplicações na base. |
| `DADO_AUSENTE` | Outro valor nulo, por exemplo `QtdEmbalagem`. |

Alertas do mesmo código aparecem uma única vez por resposta. As evidências e as listas do contexto são unidas.

As regras de normalização e de correspondência estão em [dados.md](dados.md).
