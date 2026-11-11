# Plano de implementação — API de consulta v1

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: usar `superpowers:executing-plans` (execução nativa, recomendada) ou `superpowers:subagent-driven-development` para executar este plano etapa por etapa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** microserviço FastAPI, somente leitura, que consulta a base SQLite de aplicações (veículos) e peças. Todo valor devolvido carrega evidência, e dados ausentes, conflitos e itens para revisão humana são sinalizados.

**Arquitetura:** três camadas (acesso a dados → regras determinísticas e serviços → rotas HTTP), com modelos Pydantic compartilhados. Uma camada de auditoria reexecuta as consultas, confere cada evidência contra a base e gera um relatório JSON e Excel, com amostra para revisão manual.

**Stack:** Python 3.13 (`.venv` existente), FastAPI, Uvicorn, Pydantic, sqlite3 (biblioteca padrão), openpyxl, pytest, httpx.

**Spec:** a seção 1 deste documento é a especificação condensada (brainstorming e plano unificados a pedido do usuário). Regras permanentes: [CLAUDE.md](../../../CLAUDE.md).

## Restrições globais

- Usar somente `.venv\Scripts\python.exe` (3.13.9). Nunca criar outro ambiente virtual e, portanto, não usar git worktree (o único `.venv` fica na raiz).
- Fonte única: `Database/SQLite/db_proj_final.db`, aberto com `mode=ro`. O SHA-256 do arquivo deve ser igual antes e depois de toda a execução.
- Sem chamadas a APIs de LLM e sem SDK de LLM. Sem servidores MCP. Sem aplicação web.
- SQL sempre parametrizado. Nomes de tabela e coluna vêm só de uma lista fixa (*whitelist*), nunca da entrada do usuário.
- Nunca inventar, estimar ou completar valores. Dado ausente = `null`. Valor original e normalizado sempre lado a lado, com evidência (tabela, chave, coluna, valor original).
- Saída da API determinística: a mesma entrada e a mesma base produzem o mesmo JSON (sem *timestamp* nas respostas).
- Texto em UTF-8. JSON com `ensure_ascii=False`.
- TDD em toda etapa: primeiro o teste falhando, depois o código mínimo, depois os testes passando.
- Documentação, mensagens da API e mensagens de commit em português (pt-BR).
- Commit e push só com autorização do usuário (ver decisão D1).

## Foco de revisão

Entradas que um usuário real vai usar e que precisam de teste explícito:

1. **Ano final vazio gravado como texto (`''`).** No SQLite, texto é sempre maior que inteiro, então `'' >= 2008` dá verdadeiro. O repositório precisa tratar `typeof`, e não confiar na comparação. *Teste na etapa 1.*
2. **Modelo digitado de outro jeito** (`"frontier "`, `"Frontier"`, `"FRÔNTIER"`) deve casar. **Modelo contido em outra palavra** (`"MARCH"` em `"MARCHA"`, `"VERSA"` em `"UNIVERSAL"`) não pode casar. *Testes na etapa 2.*
3. **Ano exatamente na borda da faixa** (2008 em `2006-2008` e em `2008-2013`) conta como compatível. *Teste na etapa 4.*
4. **Caracteres especiais no texto de busca** (`%`, `_`, `'`, `' OR 1=1 --`) são tratados como texto literal e não alteram a consulta. *Teste na etapa 1, repositório, e na etapa 6, API.*
5. **Ordem das rotas:** `/v1/veiculos/motorizacoes` e `/v1/veiculos/combustiveis` não podem ser capturadas por `/v1/veiculos/{codigo_aplicacao}`. *Teste na etapa 6.*

---

## 1. Entendimento e desenho

### 1.1 O que foi pedido e o que é suposição

**Pedido:**
- Versão inicial apenas com a API de consulta à base SQLite. Endpoints definidos a partir da base.
- Dois endpoints obrigatórios: motorização por modelo e ano, e combustíveis por modelo e ano.
- Considerar fabricante, modelo, ano de fabricação e combustível, e o arquivo `qry_produto_por_veiculo.sql`.
- O plano cobre estrutura, arquitetura, modelos, auditoria e amostragem, execução, testes, validação real, documentação, `requirements.txt`, pendências e versionamento.

**Suposições (a confirmar na aprovação):**
- Nesta versão, o Excel é o **relatório de auditoria com a amostra para revisão manual**. O Excel de orçamento fica para a v2 (decisão D3).
- "Ano" é ano de **fabricação** (colunas `AnoInicioFabricacao` e `AnoFimFabricacao`).
- O estado de partida descrito como ".venv + CLAUDE.md" refere-se ao código. A base, os SQLs, o MER e o `readme.md` existentes são preservados.

### 1.2 Achados da base (perfil somente leitura em 2026-11-10)

| Tema | Achado | Consequência no desenho |
|---|---|---|
| Volume | 131 aplicações, todas da NISSAN (fabricante 73). 12 fabricantes cadastrados. 5.944 produtos. 1.438 vínculos peça × aplicação. | Filtragem de modelo em Python é viável. Fabricante sem veículos gera alerta. |
| Modelo | **Não existe coluna de modelo.** `DescricaoAplicacao` mistura modelo e versão (`FRONTIER CD SE TDI 4X4`), vários modelos (`FRONTIER / PATHFINDER`, `KICKS / MARCH / VERSA`) e listas em HTML com `<br>` (6 linhas). | Correspondência por segmento e por palavra inteira (1.5), com nível de confiança. Modelo-base é um valor **derivado** e marcado como tal. |
| Anos | `AnoInicioFabricacao` sempre inteiro. `AnoFimFabricacao` com 3 valores `''` (texto). `FaixaAno` com 6 formatos abertos (`2005-...`, `2013-…`, `2020--`), às vezes divergentes das colunas (ex.: 32609 `2013-…` com fim 2013). | Ano final ausente vira `null` com alerta. Divergência entre faixa e colunas vira alerta. A filtragem usa as colunas. |
| Motorização | 29 textos distintos, muitos para o mesmo motor (`HR16DE 1.6 16V L4 DOHC` = `HR16DE - 1.6L 16V DOHC L4`). Há texto sem código (`- 2.5 L 16V DOHC L4`) e composto (`YD25DDTI / YD25ETI`). | Interpretação em atributos e agrupamento por chave estrita (1.5). |
| Combustível | Só FLEX (71), DIESEL (48) e GASOLINA (12). Conflito: o motor HR16DE 1.6 do Kicks 2018 aparece como FLEX e como GASOLINA. | Alerta `COMBUSTIVEL_CONFLITANTE`. |
| Frontier 2008 | 14 aplicações e **6 motores candidatos** (2.3, 2.5 e 2.8, com códigos diferentes). | O endpoint devolve `identificado=false` e os atributos que distinguem os candidatos. |
| Preço | `PrecoProduto` nulo em **4.047 de 5.944** produtos (68%). As bronzinas do Frontier 2008 estão todas sem preço. Nenhum preço ≤ 0. | Alerta `PRECO_AUSENTE`, que exige revisão humana. Moeda e unidade não estão documentadas (pendência). |
| Duplicidade de produto | Pares como 6809 `55.455.007` e 11837 `#NAC_55.455.007`, com a mesma descrição. | Alerta `POSSIVEL_PRODUTO_DUPLICADO`. Nunca se juntam os dois. |
| Integridade | 212 vínculos `PRODUTO_APLICACAO` apontam para aplicações inexistentes. 5.738 produtos não têm aplicação. Duplicatas exatas em `APLICACAO`: 0. | Vínculos órfãos entram na auditoria da base. O CLAUDE.md será corrigido (hoje diz "registros repetidos"). |
| Grupos | "Bronzina" é o grupo 39 (650 produtos). Busca textual por "BRONZ" também pega "GUIA DE VALVULA ... BRONZE". | Filtrar peças por **grupo** (código) e só depois por texto. |
| Colunas desconhecidas | `CodigoSimilar`, `CpoAuxProd5`, `CpoAuxProd25`, `PCs`, `NumeroProdutoPesq`. | Aparecem só no detalhe do produto, em `campos_nao_interpretados`, apenas com o valor original. |

### 1.3 Abordagens para "modelo" (o ponto central do desenho)

1. **Recomendada — correspondência em tempo de consulta sobre `DescricaoAplicacao`.** O texto é normalizado, quebrado em segmentos (`<br>` e `/`) e comparado por palavra inteira, com nível de confiança e alertas. Não altera a base e é determinística. Atende ao volume atual (131 linhas).
2. **Índice de modelos montado em memória na partida.** Mais rápido com bases grandes, mas acrescenta estado e invalidação de cache sem necessidade hoje. Fica como pendência caso a base cresça.
3. **Tabela de-para curada por humanos (modelo → aplicações).** É a mais precisa, mas depende de trabalho manual e de um arquivo novo de dados. Candidata para a v2.

Também foram decididos: `sqlite3` da biblioteca padrão em vez de ORM (menos dependências, `mode=ro` nativo, mesmo SQL dos arquivos `.sql` existentes) e evidência **por valor**, não só por registro, como exige o CLAUDE.md.

### 1.4 Endpoints (prefixo `/v1`, tags em português no Swagger)

| Método e rota | Parâmetros | Finalidade |
|---|---|---|
| `GET /v1/saude` | — | Estado do serviço: caminho do banco, `somente_leitura=true`, SHA-256 e contagem por tabela. |
| `GET /v1/fabricantes` | — | Fabricantes, com o número de aplicações de cada um. |
| `GET /v1/grupos-produto` | — | Grupos de produto (ex.: 39 BRONZINA), com o número de produtos. |
| `GET /v1/veiculos` | `modelo`, `ano`, `fabricante`, `combustivel` (todos opcionais), `pagina`, `limite` | Busca geral de aplicações. |
| **`GET /v1/veiculos/motorizacoes`** | `modelo`*, `ano`*, `fabricante`, `combustivel` | **Obrigatório.** Motores candidatos agrupados, `identificado` e atributos distintivos. |
| **`GET /v1/veiculos/combustiveis`** | `modelo`*, `ano`*, `fabricante` | **Obrigatório.** Combustíveis distintos com evidências e conflitos. |
| `GET /v1/veiculos/{codigo_aplicacao}` | — | Detalhe da aplicação (404 se não existir). |
| `GET /v1/veiculos/{codigo_aplicacao}/pecas` | `grupo`, `texto` | Peças da aplicação. É o equivalente filtrado de `qry_produto_por_veiculo.sql`. |
| `GET /v1/pecas` | `modelo`*, `ano`*, `chave_motor`, `fabricante`, `combustivel`, `grupo`, `texto`, `pagina`, `limite` | Peças compatíveis com o veículo ou motor (o caminho que o chatbot vai usar). |
| `GET /v1/pecas/{codigo_produto}` | — | Detalhe do produto: aplicações vinculadas, vínculos órfãos e `campos_nao_interpretados`. |

\* obrigatório. `ano` é inteiro de 4 dígitos. `limite` tem padrão 50 e máximo 200. Parâmetro inválido devolve 422, código inexistente devolve 404, e as duas respostas aparecem documentadas no Swagger.

### 1.5 Regras determinísticas

**Texto:** maiúsculas, sem acentos (NFKD) só para comparação, espaços colapsados. `''` vira `None`.

**Modelo:**
- A descrição normalizada é quebrada em `<BR>` e `/`, gerando segmentos aparados e não vazios.
- Um segmento igual ao modelo, ou que começa com `modelo + " "`, casa com confiança **alta** (`inicio_segmento`).
- O modelo como sequência de palavras inteiras dentro de um segmento casa com confiança **baixa** (`palavra_interna`) e gera o alerta `CORRESPONDENCIA_PARCIAL_MODELO`.
- Descrição com mais de um segmento gera `DESCRICAO_COMPOSTA`.
- Modelo-base (derivado) é a primeira palavra de cada segmento.

**Ano:**
- `AnoFimFabricacao` inteiro é usado como está. `''`, `NULL` ou texto não numérico viram `None` com `ANO_FIM_AUSENTE`.
- Há compatibilidade quando `inicio ≤ ano` e (`fim` é `None` ou `ano ≤ fim`). A faixa aberta entra como candidata, com alerta e revisão (decisão D2).
- `FaixaAno` é interpretada só para comparar com as colunas: `^\d{4}-\d{4}$` é fechada, e `^\d{4}-(\.\.\.|…|-)?$` é aberta. Qualquer diferença gera `FAIXA_ANO_DIVERGENTE`. Formato não reconhecido gera `FAIXA_ANO_NAO_INTERPRETADA`.

**Motorização:** `interpretar_motorizacao(texto) -> MotorNormalizado`
1. Normalizar o texto, trocar `" - "` por espaço e remover o `-` inicial.
2. Cilindrada: primeira ocorrência de `(?<![\d.])(\d\.\d)(?![\d.])\s*L?`. Assim `4.07` não é tomado como cilindrada.
3. Códigos: o texto antes da cilindrada, quebrado em `/` e aparado. Sem código gera `MOTORIZACAO_SEM_CODIGO`. Mais de um código gera `MOTORIZACAO_COMPOSTA`.
4. Válvulas `\b(\d{1,2})V\b`, cilindros `\b([LV]\d{1,2})\b`, comando `\b(DOHC|SOHC|OHV)\b`. Atributo não encontrado fica `None`.
5. Sem cilindrada: `interpretada=False` e `MOTORIZACAO_NAO_INTERPRETADA`, com chave `TEXTO:<texto normalizado>`.
6. Chave estrita: `"+".join(codigos)|cilindrada|{v}V|cilindros|comando`, com `?` no lugar de cada ausente. Só textos com **todos** os atributos iguais se agrupam. `HR16` e `HR16DE` não se juntam.

Exemplos que entram nos testes:

| Texto original | Chave esperada |
|---|---|
| `HR16DE - 1.6L 16V DOHC L4` | `HR16DE\|1.6\|16V\|L4\|DOHC` |
| `HR16DE 1.6 16V L4 DOHC` | `HR16DE\|1.6\|16V\|L4\|DOHC` |
| `4.07 TCE SPRINT 2.8 12V L4 SOHC` | `4.07 TCE SPRINT\|2.8\|12V\|L4\|SOHC` |
| `YD25DDTI / YD25ETI 2.5L 16V DOHC L4` | `YD25DDTI+YD25ETI\|2.5\|16V\|L4\|DOHC` (composta) |
| `YD25 SELL 2.5L 16V` | `YD25 SELL\|2.5\|16V\|?\|?` |
| `- 2.5 L 16V DOHC L4` | `?\|2.5\|16V\|L4\|DOHC` (sem código) |

**Identificação do motor:** `identificado = (número de chaves distintas == 1)`. Com mais de uma chave, gera `MOTOR_NAO_IDENTIFICADO` e preenche `atributos_distintivos`, só com os atributos que variam entre os candidatos (códigos, cilindrada, válvulas, comando, combustível e versões, que são as descrições). A API não sugere perguntas: isso é papel da skill.

**Combustível:**
- Mais de um combustível no conjunto gera `MULTIPLOS_COMBUSTIVEIS` (atenção).
- A mesma chave de motor com combustíveis diferentes gera `COMBUSTIVEL_CONFLITANTE` (revisão).

**Peças:**
- Ordem: grupo, descrição normalizada e código.
- Preço nulo gera `PRECO_AUSENTE`. O valor normalizado é um `Decimal` exato a partir de `str(original)`, sem arredondar.
- Mesma descrição normalizada com o mesmo número-base (número sem o prefixo literal `#NAC_`, usado só para detecção) gera `POSSIVEL_PRODUTO_DUPLICADO`, com as duas evidências.
- Busca por veículo sem `chave_motor` e com mais de um motor gera `MOTOR_NAO_IDENTIFICADO`, com severidade de revisão.

**Fabricante:** nome desconhecido gera `FABRICANTE_NAO_ENCONTRADO`. Nome conhecido sem aplicações gera `FABRICANTE_SEM_VEICULOS`.

**Sem resultado:**
- Modelo inexistente gera `MODELO_NAO_ENCONTRADO`, com os modelos-base disponíveis no contexto.
- Modelo existente com ano fora gera `ANO_FORA_DO_INTERVALO`, com as faixas disponíveis.

**Revisão humana:** `necessaria = existe algum alerta de severidade "revisao"`, e `motivos` lista os códigos.

### 1.6 Modelos de dados (Pydantic, em `orcamento_pecas/dominio/modelos.py`)

```text
Evidencia        { tabela: Literal["APLICACAO","PRODUTO","PRODUTO_APLICACAO","FABRICANTE","GRUPOPRODUTO","TIPOAPLICACAO"],
                   chave: dict[str, int], coluna: str, valor_original: str | int | float | None }
ValorRastreado   { original: str|int|float|None, normalizado: Any | None, evidencia: Evidencia }
Alerta           { codigo: CodigoAlerta, severidade: Literal["info","atencao","revisao"], mensagem: str,
                   evidencias: list[Evidencia], contexto: dict[str, Any] }
RevisaoHumana    { necessaria: bool, motivos: list[CodigoAlerta] }
ParametroEcoado  { original: str|int|None, normalizado: str|int|None }
Fonte            { banco: str, sha256: str }
Correspondencia  { tipo: Literal["inicio_segmento","palavra_interna"], confianca: Literal["alta","baixa"] }
MotorNormalizado { codigos: list[str], cilindrada_l: str|None, valvulas: int|None, cilindros: str|None,
                   comando: str|None, interpretada: bool, chave: str }
Aplicacao        { codigo_aplicacao: int, fabricante: ValorRastreado, tipo_aplicacao: ValorRastreado,
                   descricao: ValorRastreado, modelos_base_derivados: list[str], faixa_ano: ValorRastreado,
                   ano_inicio: ValorRastreado, ano_fim: ValorRastreado, motorizacao: ValorRastreado (normalizado=MotorNormalizado),
                   combustivel: ValorRastreado, correspondencia: Correspondencia | None }
CandidatoMotor   { chave_motor: str, motor: MotorNormalizado, motorizacoes_originais: list[ValorRastreado],
                   combustiveis: list[str], codigos_aplicacao: list[int] }
ItemCombustivel  { combustivel: str, valores: list[ValorRastreado], codigos_aplicacao: list[int] }
Produto          { codigo_produto: int, descricao: ValorRastreado, grupo: ValorRastreado, numero_produto: ValorRastreado,
                   preco: ValorRastreado (normalizado=Decimal|None), qtd_embalagem: ValorRastreado,
                   codigos_aplicacao: list[int] }
ProdutoDetalhe   = Produto + { vinculos_orfaos: list[int], campos_nao_interpretados: dict[str, str|None] }
Resposta[T]      { consulta: dict[str, ParametroEcoado], dados: T, total: int, pagina: int|None, limite: int|None,
                   alertas: list[Alerta], revisao_humana: RevisaoHumana, fonte: Fonte }
DadosMotorizacoes  { identificado: bool, motor_identificado: CandidatoMotor|None, candidatos: list[CandidatoMotor],
                     atributos_distintivos: dict[str, list[str]], aplicacoes: list[Aplicacao] }
DadosCombustiveis  { unico: bool, combustiveis: list[ItemCombustivel], aplicacoes: list[Aplicacao] }
```

Catálogo inicial de alertas (`CodigoAlerta`, StrEnum), com a severidade:
- **revisao:** `ANO_FIM_AUSENTE`, `FAIXA_ANO_DIVERGENTE`, `FAIXA_ANO_NAO_INTERPRETADA`, `MOTORIZACAO_SEM_CODIGO`, `MOTORIZACAO_COMPOSTA`, `MOTORIZACAO_NAO_INTERPRETADA`, `COMBUSTIVEL_CONFLITANTE`, `PRECO_AUSENTE`, `POSSIVEL_PRODUTO_DUPLICADO`, `VINCULO_ORFAO`, `REFERENCIA_INEXISTENTE`.
- **atencao:** `MOTOR_NAO_IDENTIFICADO` (vira **revisao** em `/v1/pecas`), `MULTIPLOS_COMBUSTIVEIS`, `DESCRICAO_COMPOSTA`, `CORRESPONDENCIA_PARCIAL_MODELO`, `MODELO_NAO_ENCONTRADO`, `ANO_FORA_DO_INTERVALO`, `FABRICANTE_NAO_ENCONTRADO`, `FABRICANTE_SEM_VEICULOS`.

### 1.7 Auditoria automática e revisão manual por amostragem

- **Auditoria da base** (`auditar_base`): vínculos órfãos, referências inexistentes (fabricante, tipo, grupo), anos ausentes ou divergentes, motorizações sem código, compostas ou não interpretadas, conflitos de combustível no nível da base, preços ausentes em produtos vinculados e possíveis duplicidades. Esses achados são de **qualidade de dados**: geram alertas, não falhas.
- **Bateria de consultas:** para cada modelo-base, em cada ano das suas faixas (faixa aberta vai até o maior ano final presente na base), chama `motorizacoes` e `combustiveis`. Para cada aplicação chama `pecas.da_aplicacao`, e para cada produto vinculado chama `pecas.obter`.
- **Invariantes** (`auditar_resposta`), que são **falhas** se violadas:
  - **I1.** Cada `ValorRastreado` é relido na base pela evidência, e o valor tem que ser igual ao `original`, com o mesmo tipo.
  - **I2.** Todo `normalizado=None` tem um alerta que cita a mesma evidência.
  - **I3.** `revisao_humana.necessaria` é verdadeiro se, e somente se, existe um alerta de revisão.
  - **I4.** `identificado` é verdadeiro se, e somente se, há 1 candidato. `unico` é verdadeiro se, e somente se, há 1 combustível.
  - **I5.** Toda aplicação devolvida satisfaz de fato os filtros de modelo e ano (rechecado).
  - **I6.** Não há produto repetido numa listagem, e `total` é coerente com a paginação.
- **Amostra para revisão manual:** sorteio determinístico, com semente, estratificado: metade de registros com alertas de revisão e metade de registros limpos. Padrão: 30 itens, semente 42. Cada linha traz consulta, campo, valor exibido, original, evidência e o SQL de conferência pronto, além das colunas do revisor: `Conferido (S/N)`, `Divergência`, `Comentário`, `Revisor`, `Data`.
- **Relatório:** os mesmos dados em `saidas/auditoria/auditoria_<AAAAMMDD-HHMMSS>.json` e `.xlsx`. Abas: `Resumo`, `Falhas`, `Alertas_base`, `Amostra_revisao`, `Metadados` (banco, SHA-256, semente, comando, gerado_em).
- **Fechamento da revisão:** o subcomando `revisao` lê o Excel preenchido e resume conferidos, divergências e pendentes.

### 1.8 Interface de execução

```powershell
# API (Swagger em http://127.0.0.1:8000/docs)
.venv\Scripts\python.exe -m orcamento_pecas servidor [--host 127.0.0.1] [--port 8000] [--banco <caminho>] [--reload]
# equivalente direto:
.venv\Scripts\python.exe -m uvicorn --factory orcamento_pecas.api.app:criar_app

# Auditoria (código de saída 1 se houver falha de invariante)
.venv\Scripts\python.exe -m orcamento_pecas auditoria [--banco <caminho>] [--amostra 30] [--semente 42] [--saida saidas/auditoria]

# Resumo da revisão manual (código de saída 1 se houver divergência)
.venv\Scripts\python.exe -m orcamento_pecas revisao saidas/auditoria/auditoria_<...>.xlsx

# Testes
.venv\Scripts\python.exe -m pytest                 # tudo
.venv\Scripts\python.exe -m pytest -m "not base_real"   # só base de teste
```

O caminho do banco tem esta prioridade: `--banco`, depois a variável `ORCAMENTO_PECAS_DB`, depois `Database/SQLite/db_proj_final.db`. O servidor escuta só em `127.0.0.1` por padrão.

### 1.9 Fora desta versão (roteiro v2, sem detalhar)

- Skill do projeto para análise dos pedidos (com `skill-creator`).
- JSON de orçamento.
- Excel de orçamento.
- Tabela de-para de modelos (abordagem 3).

A v1 entrega as peças que a v2 vai consumir: `motorizacoes`, `combustiveis` e `/v1/pecas?chave_motor=`.

---

## 2. Estrutura de diretórios e arquivos

```text
projeto-final/
├── CLAUDE.md                      (modificar na etapa 9: comandos e correção dos problemas conhecidos)
├── readme.md                      (não alterar: modelo acadêmico, decisão D4)
├── .gitignore                     (modificar na etapa 0: acrescentar, preservando a alteração já existente)
├── pyproject.toml                 (criar: só [tool.pytest.ini_options], com pythonpath ".", marcador base_real)
├── requirements.txt               (criar na etapa 10)
├── Database/ ...                  (existente, não alterar)
├── Documentacao/ ...              (existente, não alterar)
├── docs/
│   ├── superpowers/plans/2026-11-10-api-consulta-v1.md   (este plano)
│   ├── api.md                     (endpoints, parâmetros, exemplos reais, alertas)
│   ├── dados.md                   (dicionário da base, regras de normalização, problemas conhecidos)
│   ├── auditoria.md               (como rodar, como ler o relatório, como fazer a revisão por amostragem)
│   └── pendencias.md              (registro de pendências, criado na etapa 0 e atualizado a cada etapa)
├── orcamento_pecas/
│   ├── __init__.py                (__version__ = "0.1.0")
│   ├── __main__.py                (chama cli.main)
│   ├── cli.py                     (argparse: servidor | auditoria | revisao)
│   ├── config.py                  (resolução do caminho do banco)
│   ├── dados/
│   │   ├── conexao.py             (conexão somente leitura, SHA-256)
│   │   └── repositorio.py         (todo o SQL, parametrizado)
│   ├── dominio/
│   │   ├── normalizacao.py        (texto, modelo, ano, faixa, motorização, preço, número-base)
│   │   ├── alertas.py             (CodigoAlerta, catálogo, criar_alerta, revisao_humana)
│   │   ├── evidencias.py          (fábrica de Evidencia e ValorRastreado a partir de sqlite3.Row)
│   │   └── modelos.py             (modelos Pydantic da seção 1.6)
│   ├── servicos/
│   │   ├── catalogos.py           (fabricantes, grupos, saúde)
│   │   ├── veiculos.py            (busca, detalhe, motorizações, combustíveis)
│   │   └── pecas.py               (da aplicação, por veículo, detalhe)
│   ├── api/
│   │   ├── app.py                 (criar_app: metadados do Swagger, tratamento de erros, rotas)
│   │   ├── dependencias.py        (conexão por requisição, serviços)
│   │   └── rotas/{saude,catalogos,veiculos,pecas}.py
│   └── auditoria/
│       ├── verificacoes.py        (auditar_base, auditar_resposta)
│       ├── bateria.py             (geração determinística das consultas)
│       ├── amostragem.py          (sorteio estratificado com semente)
│       ├── relatorio.py           (modelo do relatório, gravação de JSON e Excel, leitura da revisão)
│       └── executor.py            (executar_auditoria)
├── tests/
│   ├── conftest.py                (fixtures: banco_teste, repo, servicos, cliente_api, banco_real)
│   ├── dados/base_teste.sql       (mesmo DDL da base real e cerca de 30 linhas copiadas dos casos reais relevantes)
│   ├── unit/…                     (ver seção 4)
│   ├── api/…
│   ├── integracao/test_base_real.py   (marcador base_real)
│   └── test_requirements.py
└── saidas/                        (ignorada pelo git: relatórios de auditoria e de validação)
```

---

## 3. Etapas de execução

Cada etapa segue o ciclo TDD (`superpowers:test-driven-development`) e termina com sua verificação. Se a decisão D1 autorizar, cada etapa termina também com um commit na branch.

### Etapa 0 — Preparação do ambiente e do repositório
**Arquivos:** `.gitignore`, `pyproject.toml`, `docs/pendencias.md`, `orcamento_pecas/__init__.py`, `tests/conftest.py` (vazio).
- [ ] Criar a branch `feature/api-consulta-v1` a partir da `main`, sem worktree.
- [ ] Acrescentar ao `.gitignore`: `__pycache__/`, `*.py[cod]`, `.pytest_cache/` e `saidas/`.
- [ ] Instalar no `.venv`: `fastapi`, `uvicorn`, `httpx`, `pytest` e `openpyxl`.
- [ ] Criar o `pyproject.toml` (pytest: `testpaths=["tests"]`, `pythonpath=["."]`, marcador `base_real`).
- [ ] Criar `docs/pendencias.md` com as pendências iniciais da seção 6.
- [ ] Gravar o SHA-256 da base em `saidas/sha256_inicial.txt`.
- **Verificação:** `python --version` mostra 3.13.9. `pip list` mostra os 5 pacotes. `pytest` roda e coleta 0 testes, sem erro.

### Etapa 1 — Acesso somente leitura à base e base de teste
**Arquivos:** `config.py`, `dados/conexao.py`, `dados/repositorio.py`, `tests/dados/base_teste.sql`, `tests/conftest.py`, `tests/unit/test_conexao.py`, `tests/unit/test_repositorio.py`.

**Interfaces produzidas:**
- `caminho_banco(arg: Path | None = None) -> Path`
- `abrir_somente_leitura(caminho: Path) -> sqlite3.Connection`, com `row_factory=sqlite3.Row`. Lança `BancoIndisponivelError` se o arquivo não existir.
- `sha256_arquivo(caminho: Path) -> str`
- Classe `Repositorio(conexao)`, com os métodos:
  - `listar_fabricantes()`, `listar_grupos_produto()`, `contagens()`
  - `listar_aplicacoes(codigo_fabricante: int | None) -> list[Row]` (já com `DescricaoFabricante` e `DescricaoTipoAplicacao`)
  - `obter_aplicacao(codigo: int) -> Row | None`
  - `listar_pecas_das_aplicacoes(codigos: Sequence[int], codigo_grupo: int | None) -> list[Row]` (vem de `qry_produto_por_veiculo.sql`, com `CodigoAplicacao` por linha)
  - `obter_produto(codigo: int) -> Row | None`, `aplicacoes_do_produto(codigo: int) -> list[int]`, `vinculos_orfaos_do_produto(codigo: int) -> list[int]`
  - `ler_valor(tabela: str, chave: Mapping[str, int], coluna: str) -> object` (lista fixa de tabelas e colunas)
  - Consultas de auditoria: `vinculos_orfaos()`, `referencias_inexistentes()`, `listar_produtos_vinculados()`

**Testes principais:**
- `test_escrita_falha_em_modo_somente_leitura`: `INSERT` lança `sqlite3.OperationalError`.
- `test_banco_inexistente_lanca_erro_claro`
- `test_ano_fim_texto_vazio_preservado_como_texto`: `typeof` continua `'text'` e o valor é `''`.
- `test_parametros_maliciosos_sao_literais`: `"' OR 1=1 --"`, `%` e `_` devolvem 0 linhas e não dão erro.
- `test_ler_valor_rejeita_tabela_fora_da_lista`
- `test_pecas_da_aplicacao_equivalem_a_query_sql`: mesmo conjunto de (aplicação, produto) que o `.sql` original na base de teste.

**Verificação:** `pytest tests/unit/test_conexao.py tests/unit/test_repositorio.py` passa.

### Etapa 2 — Normalização determinística
**Arquivos:** `dominio/normalizacao.py`, `tests/unit/test_normalizacao.py`, `tests/unit/test_motorizacao.py`.

**Interfaces produzidas:**
- `normalizar_texto(v: str | None) -> str | None`
- `segmentos_descricao(d: str) -> list[str]`
- `modelos_base(d: str) -> list[str]`
- `corresponde_modelo(descricao: str, modelo: str) -> Correspondencia | None`
- `normalizar_ano_fim(v: object) -> int | None`
- `interpretar_faixa_ano(f: str) -> FaixaInterpretada(inicio, fim, aberta, interpretada)`
- `ano_compativel(ano: int, inicio: int, fim: int | None) -> bool`
- `interpretar_motorizacao(t: str) -> MotorNormalizado`
- `normalizar_preco(v: float | None) -> Decimal | None`
- `numero_produto_base(n: str) -> str`

**Testes principais:**
- Modelo:
  - `"frontier "`, `"Frontier"` e `"FRÔNTIER"` casam `FRONTIER CD SE TDI 4X4` com confiança alta.
  - `"MARCH"` **não** casa `MARCHA X`.
  - `"PATHFINDER"` casa `FRONTIER/ PATHFINDER`.
  - `"KICKS"` casa a descrição com `<br>`.
  - `"SE"` casa como `palavra_interna`, com confiança baixa.
- Faixa de ano:
  - `2005-...` e `2013-…` são abertas.
  - `2020--` é aberta.
  - `2017-2022` é fechada.
  - `abc` não é interpretada.
- Motorização: `test_todas_as_motorizacoes_reais_interpretadas`, parametrizado com os **29 textos distintos** da base real, extraídos por SQL nesta etapa e fixados como literais junto com a chave esperada (inclui os 6 exemplos da seção 1.5).
- Preço:
  - `66.84` vira `Decimal("66.84")`.
  - `None` vira `None`.
  - `numero_produto_base("#NAC_55.455.007") == "55.455.007"`.

**Verificação:** os testes da etapa passam e cobrem todos os 29 textos.

### Etapa 3 — Modelos de dados, evidências e catálogo de alertas
**Arquivos:** `dominio/modelos.py`, `dominio/evidencias.py`, `dominio/alertas.py`, `tests/unit/test_modelos.py`, `tests/unit/test_alertas.py`.

**Interfaces produzidas:**
- Modelos da seção 1.6.
- `valor_de(row: Row, tabela: str, chave: dict[str, int], coluna: str, normalizado: object) -> ValorRastreado`
- `criar_alerta(codigo: CodigoAlerta, evidencias: list[Evidencia], **contexto) -> Alerta`
- `revisao_humana(alertas: list[Alerta]) -> RevisaoHumana`

**Testes principais:**
- `test_none_serializa_como_null_e_nao_como_valor_padrao`
- `test_todo_codigo_tem_severidade_e_mensagem`
- `test_revisao_necessaria_somente_com_alerta_de_revisao`
- `test_decimal_serializa_sem_perder_casas`
- `test_json_preserva_acentos`

**Verificação:** os testes passam, e `Resposta[DadosMotorizacoes].model_json_schema()` é gerado sem erro.

### Etapa 4 — Serviço de veículos (os dois endpoints obrigatórios)
**Arquivos:** `servicos/veiculos.py`, `tests/unit/test_servico_veiculos.py`.

**Interfaces produzidas:** `ServicoVeiculos(repo, fonte: Fonte)`, com os métodos:
- `buscar(modelo, ano, fabricante, combustivel, pagina, limite) -> Resposta[list[Aplicacao]]`
- `obter(codigo: int) -> Resposta[Aplicacao] | None`
- `motorizacoes(modelo: str, ano: int, fabricante: str | None = None, combustivel: str | None = None) -> Resposta[DadosMotorizacoes]`
- `combustiveis(modelo: str, ano: int, fabricante: str | None = None) -> Resposta[DadosCombustiveis]`
- `resolver_aplicacoes(...)`, de uso interno, compartilhado com as peças

**Testes principais (base de teste):**
- `test_frontier_2008_nao_identificado_com_atributos_distintivos`: mais de um candidato, `cilindrada_l` em `atributos_distintivos`.
- `test_filtro_por_combustivel_reduz_candidatos`
- `test_ano_na_borda_da_faixa_e_compativel`
- `test_faixa_aberta_entra_com_alerta_ano_fim_ausente_e_revisao`
- `test_kicks_2018_conflito_de_combustivel`
- `test_modelo_inexistente_lista_modelos_disponiveis`
- `test_ano_fora_lista_faixas`
- `test_fabricante_sem_veiculos` e `test_fabricante_inexistente`
- `test_motor_unico_identificado`

**Verificação:** os testes da etapa passam. Para os candidatos, `identificado` é verdadeiro somente quando há 1 chave.

### Etapa 5 — Serviço de peças e catálogos
**Arquivos:** `servicos/pecas.py`, `servicos/catalogos.py`, `tests/unit/test_servico_pecas.py`, `tests/unit/test_servico_catalogos.py`.

**Interfaces produzidas:**
- `ServicoPecas(repo, veiculos: ServicoVeiculos, fonte)`, com os métodos:
  - `da_aplicacao(codigo_aplicacao: int, grupo: int | None = None, texto: str | None = None) -> Resposta[list[Produto]] | None`
  - `por_veiculo(modelo, ano, chave_motor=None, fabricante=None, combustivel=None, grupo=None, texto=None, pagina=1, limite=50) -> Resposta[list[Produto]]`
  - `obter(codigo_produto: int) -> Resposta[ProdutoDetalhe] | None`
- `ServicoCatalogos(repo, fonte)`, com os métodos `fabricantes()`, `grupos()` e `saude()`.

**Testes principais:**
- `test_pecas_da_aplicacao_sem_preco_geram_revisao`
- `test_possivel_duplicidade_nac_sinalizada_sem_mesclar`: os 2 produtos continuam presentes.
- `test_filtro_grupo_bronzina_exclui_guia_de_valvula_bronze`
- `test_por_veiculo_sem_chave_motor_com_varios_motores_exige_revisao`
- `test_por_veiculo_com_chave_motor_restringe_aplicacoes`
- `test_detalhe_lista_vinculos_orfaos_e_campos_nao_interpretados`
- `test_paginacao_deterministica`

**Verificação:** os testes da etapa passam.

### Etapa 6 — API FastAPI e Swagger
**Arquivos:** `api/app.py`, `api/dependencias.py`, `api/rotas/*.py`, `tests/api/test_api_*.py`, `tests/api/test_openapi.py`.

**Interfaces produzidas:** `criar_app(caminho_banco: Path | None = None) -> FastAPI`. Na partida, valida o banco e calcula o SHA-256. A conexão é aberta e fechada por requisição.

**Testes principais (TestClient sobre a base de teste):**
- 200 e esquema válido em cada endpoint.
- 404 para código inexistente.
- 422 para `ano=abc`, `limite=500` e `modelo` vazio.
- `test_rotas_fixas_nao_capturadas_por_codigo`
- `test_resposta_http_igual_a_do_servico`
- `test_openapi_descreve_todos_endpoints_com_exemplos_e_tags_pt`
- `test_parametro_malicioso_na_api_retorna_vazio`

**Verificação:** os testes passam. `uvicorn` sobe, e `/docs` e `/openapi.json` respondem 200 (via `httpx`).

### Etapa 7 — Auditoria automática, amostragem, relatórios e CLI
**Arquivos:** `auditoria/*.py`, `cli.py`, `__main__.py`, `tests/unit/test_auditoria_*.py`, `tests/unit/test_cli.py`.

**Interfaces produzidas:**
- `auditar_base(repo) -> list[AchadoBase]`
- `auditar_resposta(resposta: Resposta, repo, filtros: dict) -> list[Falha]`
- `gerar_bateria(repo) -> list[Consulta]`
- `sortear_amostra(itens, tamanho: int, semente: int) -> list[ItemAmostra]`
- `executar_auditoria(caminho_banco: Path, tamanho_amostra: int = 30, semente: int = 42, pasta_saida: Path = Path("saidas/auditoria")) -> RelatorioAuditoria`
- `gravar_json(rel, caminho)`, `gravar_excel(rel, caminho)`, `ler_revisao(caminho) -> ResumoRevisao`
- `main(argv: list[str] | None = None) -> int`

**Testes principais:**
- `test_auditoria_base_detecta_anomalias_semeadas`: base de teste com órfão, ano aberto, faixa divergente, composta e sem código.
- `test_evidencia_adulterada_vira_falha_I1`
- `test_ausente_sem_alerta_vira_falha_I2`
- `test_amostra_mesma_semente_mesmo_resultado_e_estratificada`
- `test_excel_tem_abas_e_colunas_do_revisor`
- `test_json_e_excel_consistentes`
- `test_ler_revisao_conta_conferidos_e_divergencias`
- `test_cli_auditoria_codigo_saida`

**Verificação:** `python -m orcamento_pecas auditoria --banco <base_teste>` gera o JSON e o `.xlsx` e sai com 0.

### Etapa 8 — Validação real controlada
**Arquivos:** `tests/integracao/test_base_real.py`. As saídas vão para `saidas/validacao/`, que é ignorada pelo git.

**Casos fixos contra a base real** (valores levantados no perfil de 2026-11-10):

| # | Consulta | Esperado |
|---|---|---|
| V1 | `motorizacoes?modelo=frontier&ano=2008` | 14 aplicações. `identificado=false`. **6 candidatos**: `4.07 TCE SPRINT\|2.8…`, `SPRINT EURO 3\|2.8…`, `YD25ETI\|2.5\|16V\|L4\|DOHC`, `YD25 SELL\|2.5\|16V\|?\|?`, `YD25DDTI+YD25ETI\|2.5…`, `M9T\|2.3\|16V\|L4\|DOHC`. Alertas `MOTOR_NAO_IDENTIFICADO`, `ANO_FIM_AUSENTE` (31393) e `MOTORIZACAO_COMPOSTA` (36311). |
| V2 | `combustiveis?modelo=kicks&ano=2018` | 12 aplicações: FLEX (5) e GASOLINA (7). `MULTIPLOS_COMBUSTIVEIS` e `COMBUSTIVEL_CONFLITANTE` em `HR16DE\|1.6\|16V\|L4\|DOHC`. |
| V3 | `veiculos/35368/pecas?grupo=39` | 6 produtos (6809, 6810, 6811, 11837, 11838, 11839), todos com `preco.normalizado=null`. `PRECO_AUSENTE`, 3 pares em `POSSIVEL_PRODUTO_DUPLICADO` e `revisao_humana.necessaria=true`. |
| V4 | `combustiveis?modelo=frontier&ano=2008` | Só DIESEL. `unico=true`. |
| V5 | `motorizacoes?modelo=xyz&ano=2008` | 0 aplicações. `MODELO_NAO_ENCONTRADO` com os modelos disponíveis. |
| V6 | `motorizacoes?fabricante=fiat&modelo=uno&ano=2010` | `FABRICANTE_SEM_VEICULOS`. |
| V7 | Execução completa | O SHA-256 da base é igual ao de `saidas/sha256_inicial.txt`. |

**Passos:**
- [ ] Rodar `pytest -m base_real`.
- [ ] Subir o servidor e chamar V1 a V6 via HTTP, gravando as respostas em `saidas/validacao/`.
- [ ] Rodar `auditoria` na base real, esperando **0 falhas de invariante**. Os alertas da base ficam listados, com pelo menos 212 vínculos órfãos e 3 anos finais ausentes.
- [ ] Entregar o `.xlsx` da amostra para a revisão manual do usuário. É uma pendência humana e não bloqueia a conclusão técnica.

**Verificação:** todos os casos V1 a V7 batem. Divergência é investigada com `superpowers:systematic-debugging` e nunca é ajustada no teste.

### Etapa 9 — Documentação
**Arquivos:** `docs/api.md`, `docs/dados.md`, `docs/auditoria.md`, `docs/pendencias.md` (atualizar), `CLAUDE.md` (acrescentar a seção "Comandos" e corrigir "registros repetidos" para "registros sobrepostos; duplicatas exatas: 0", incluindo os órfãos e os preços nulos), descrições e exemplos do Swagger.
- **Verificação:** os exemplos de `docs/api.md` são respostas reais gravadas na etapa 8, não escritas à mão. Os links internos funcionam.

### Etapa 10 — Geração do `requirements.txt`
**Arquivos:** `requirements.txt`, `tests/test_requirements.py`.
- [ ] Varrer com `ast` os imports de `orcamento_pecas/` e `tests/` para obter os pacotes de terceiros realmente importados.
- [ ] Acrescentar os pacotes usados indiretamente mas obrigatórios, cada um com comentário de justificativa: `httpx` (necessário ao `TestClient`) e `uvicorn` (servidor).
- [ ] Fixar as versões instaladas (`==`).
- **Testes:**
  - `test_todo_import_de_terceiros_esta_no_requirements`
  - `test_requirements_nao_tem_pacote_sem_uso`
- **Verificação:** `pip check` sem conflitos, `pip install -r requirements.txt --dry-run` no próprio `.venv` sem mudanças, e os dois testes passam.

### Etapa 11 — Revisão final e preparação para o GitHub
- [ ] Usar `superpowers:requesting-code-review` sobre a branch inteira e tratar os achados com `superpowers:receiving-code-review`.
- [ ] Usar `superpowers:verification-before-completion`: `pytest` completo, servidor com `/docs`, `auditoria` na base real e SHA-256 da base inalterado, mostrando a saída real.
- [ ] Conferir o `git status`: nada de `saidas/`, `__pycache__`, `.venv` ou credenciais. `.mcp.json` e `.claude/settings.json` ficam conforme a decisão do usuário (pendência P13).
- [ ] Usar `superpowers:finishing-a-development-branch` para apresentar as opções (merge local na `main` ou PR). **Push e PR só com pedido explícito.**

---

## 4. Testes previstos (resumo)

| Arquivo | Cobre |
|---|---|
| `tests/unit/test_conexao.py` | modo somente leitura, banco ausente, SHA-256 |
| `tests/unit/test_repositorio.py` | consultas, `typeof` do ano, parâmetros maliciosos, equivalência com `qry_produto_por_veiculo.sql` |
| `tests/unit/test_normalizacao.py` | texto, segmentos, modelo, faixa e ano, preço, número-base |
| `tests/unit/test_motorizacao.py` | os 29 textos reais de motorização |
| `tests/unit/test_modelos.py`, `test_alertas.py` | serialização, `null`, catálogo, regra de revisão |
| `tests/unit/test_servico_veiculos.py` | motorizações, combustíveis, busca, alertas |
| `tests/unit/test_servico_pecas.py`, `test_servico_catalogos.py` | peças, preço ausente, duplicidade, órfãos, paginação |
| `tests/api/test_api_*.py`, `test_openapi.py` | HTTP, 404 e 422, ordem das rotas, Swagger completo |
| `tests/unit/test_auditoria_*.py`, `test_cli.py` | invariantes I1–I6, amostragem, JSON e Excel, revisão, CLI |
| `tests/integracao/test_base_real.py` | casos V1 a V7 (marcador `base_real`) |
| `tests/test_requirements.py` | requirements igual aos imports |

## 5. Dependências prováveis

| Pacote | Uso | Tipo |
|---|---|---|
| `fastapi` | API e Swagger | execução |
| `pydantic` | modelos (já vem com o FastAPI, mas é importado diretamente) | execução |
| `uvicorn` | servidor ASGI | execução |
| `openpyxl` | relatório Excel e leitura da revisão | execução |
| `pytest` | testes | desenvolvimento |
| `httpx` | `TestClient` e checagem de `/docs` | desenvolvimento |

Biblioteca padrão: `sqlite3`, `hashlib`, `decimal`, `unicodedata`, `re`, `argparse`, `random`, `json`, `pathlib`, `ast`.

## 6. Pendências iniciais (semente de `docs/pendencias.md`)

| ID | Tipo | Pendência | Evidência |
|---|---|---|---|
| P1 | dado ausente | `PrecoProduto` nulo em 4.047 de 5.944 produtos. As bronzinas do Frontier 2008 estão sem preço. | `PRODUTO.PrecoProduto` |
| P2 | decisão do usuário | Significado de `CodigoSimilar`, `CpoAuxProd5`, `CpoAuxProd25`, `PCs` e `NumeroProdutoPesq`. | `PRODUTO` |
| P3 | decisão do usuário | Moeda e unidade do preço: por peça ou por embalagem (`QtdEmbalagem`)? | `PRODUTO` |
| P4 | ambiguidade | Produtos com prefixo `#NAC_` duplicando outro produto. Qual vale? | ex.: 6809 e 11837 |
| P5 | integridade | 212 vínculos para aplicações inexistentes (excluídas na migração). | `PRODUTO_APLICACAO` |
| P6 | ambiguidade | 3 aplicações sem ano final: o veículo ainda é fabricado ou o dado é desconhecido? | ex.: 31393 |
| P7 | conflito | `FaixaAno` diverge das colunas de ano. | ex.: 32609, 34590 |
| P8 | ambiguidade | Motorizações sem código ou compostas. | ex.: 35374, 36311 |
| P9 | conflito | Kicks 2018 com o mesmo motor em FLEX e GASOLINA. | códigos 153xx × 31383 |
| P10 | cobertura | A base só tem veículos NISSAN. | `APLICACAO.CodigoFabricante` |
| P11 | modelagem | Não há coluna de modelo. As descrições trazem vários modelos ou HTML. | `APLICACAO.DescricaoAplicacao` |
| P12 | documentação | `readme.md` é o modelo acadêmico e cabe ao aluno preenchê-lo. | `readme.md` |
| P13 | versionamento | Versionar ou não `.mcp.json` (fipex, fora do escopo) e `.claude/settings.json`. | `git status` |

## 7. Decisões aprovadas pelo usuário (2026-11-10)

- **D1 — Commits:** só quando o usuário solicitar. Não há commit por etapa.
- **D2 — Ano final ausente:** não excluir da busca. Entra como candidato, com alerta e revisão.
- **D3 — Excel na v1:** relatório de auditoria com a amostra de revisão. O Excel de orçamento fica para a v2.
- **D4 — `readme.md`:** não alterar. A documentação técnica fica em `docs/`.
- **D5 — Execução do plano:** nativa (`superpowers:executing-plans`).
