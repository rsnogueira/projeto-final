# CLAUDE.md — Orçamento automatizado de peças de motor

Regras permanentes deste repositório. O procedimento completo de análise dos pedidos de orçamento **não** fica aqui: ele fica na skill do projeto (ver "Uso das skills").

## Objetivo do projeto

Chatbot que fornece orçamentos de peças de motores automotivos a partir de um pedido em linguagem natural, por exemplo: "Preciso de uma bronzina do Frontier 2008."

- Atributos principais do veículo: **fabricante, modelo, ano de fabricação e combustível**.
- Fluxo esperado: interpretar o pedido → identificar o motor com precisão, pedindo informações complementares enquanto houver ambiguidade → buscar as peças na base → gerar JSON com evidências → registrar dados ausentes, ambiguidades e itens para revisão humana → auditar antes de concluir.
- Artefato final principal: **planilha Excel**.

## Escopo

### Dentro da v1
- Microserviço de API em **FastAPI**, servido por **Uvicorn** e documentado via **Swagger** (`/docs`), que expõe as informações do banco.
- Fonte única e fixa: SQLite em `Database/SQLite/db_proj_final.db`.
- Código Python para todas as etapas determinísticas: consulta, normalização, filtragem de motores candidatos, montagem do JSON e do Excel, verificações de auditoria.
- Testes automatizados.
- `requirements.txt` gerado ao final, apenas com as dependências realmente usadas.

### Fora da v1
- Aplicação web ou front-end.
- Servidores MCP, inclusive o `fipex` configurado em `.mcp.json`: não usar como fonte de dados nem no código.
- Chamadas a APIs de LLM no código Python. A interpretação da linguagem natural é feita pelo agente, guiado pela skill do projeto.
- Qualquer fonte de dados além do SQLite.

## Ambiente do projeto

- **Python 3.13**, exclusivamente pelo ambiente virtual existente em `.venv` (hoje 3.13.9).
- **Nunca criar outro ambiente virtual** (`python -m venv`, `virtualenv`, `conda`, `uv venv`, ambientes do `poetry` etc.).
- Sempre usar o interpretador do `.venv`: `.venv\Scripts\python.exe`, e pip via `.venv\Scripts\python.exe -m pip`. Nunca usar o Python global.
- Instalar dependências apenas quando um plano aprovado as exigir.
- Sistema: Windows 11. Terminal principal: PowerShell 5.1 (Git Bash também disponível).
- Stack: FastAPI, Uvicorn, Swagger (gerado pelo FastAPI), pytest para testes.
- Base de dados (modelo ER em `Documentacao/MER/modelo_ER_Proj_v1.png`):
  - `APLICACAO`: veículos (`FaixaAno`, `Motorizacao`, `Combustivel`, `DescricaoAplicacao`, `AnoInicioFabricacao`, `AnoFimFabricacao`).
  - `PRODUTO`: peças (inclui `PrecoProduto`).
  - `PRODUTO_APLICACAO`: relação peça × veículo.
  - `FABRICANTE`, `GRUPOPRODUTO`, `TIPOAPLICACAO`: tabelas de apoio.

## Comandos

```powershell
.venv\Scripts\python.exe -m pytest                        # todos os testes
.venv\Scripts\python.exe -m pytest -m "not base_real"     # sem a base real
.venv\Scripts\python.exe -m orcamento_pecas servidor      # API em http://127.0.0.1:8000/docs
.venv\Scripts\python.exe -m orcamento_pecas auditoria     # relatório JSON e Excel em saidas/auditoria/
.venv\Scripts\python.exe -m orcamento_pecas revisao <arquivo.xlsx>   # resumo da revisão manual
```

Mapa do código: `orcamento_pecas/dados` (conexão e SQL), `dominio` (normalização, alertas, evidências, modelos), `servicos` (regras de negócio), `api` (rotas FastAPI), `auditoria` (invariantes, amostra, relatórios), `cli.py`. Documentação técnica em `docs/` (`api.md`, `dados.md`, `auditoria.md`, `pendencias.md`).

## Processo de trabalho do agente

1. Analisar o objetivo da tarefa.
2. Para toda tarefa relevante (funcionalidade nova, mudança de comportamento, de estrutura, de dependências ou de dados), apresentar um plano e **aguardar aprovação explícita**. Não iniciar a implementação antes disso.
3. Aprovado o plano, executá-lo de forma autônoma até o fim, sem pedir confirmação a cada passo.
4. Interromper e consultar o usuário somente se o plano se mostrar inviável ou incorreto, se surgir uma decisão que cabe ao usuário, ou se for preciso sair do escopo aprovado. Mudança de escopo exige novo plano.
5. Implementar seguindo TDD.
6. Validar e auditar (ver "Validação") antes de declarar a tarefa concluída.
7. Relatar com fidelidade o que foi feito, o que falhou, o que ficou pendente e os itens para revisão humana.

- Restrições explícitas do usuário para uma etapa (ex.: "não crie arquivos", "crie somente X") prevalecem sobre este arquivo e sobre o fluxo de qualquer skill.
- Comunicação com o usuário e documentação em português (pt-BR).

## Uso das skills

- **`superpowers:using-superpowers`**: acionar no início de cada tarefa, para identificar e usar as skills aplicáveis. É a base do desenvolvimento em Python.
- Skills do superpowers por fase:
  - Desenho de funcionalidade nova: `superpowers:brainstorming`
  - Plano: `superpowers:writing-plans`
  - Execução do plano: `superpowers:executing-plans` ou `superpowers:subagent-driven-development`
  - Implementação: `superpowers:test-driven-development`
  - Bugs e falhas de teste: `superpowers:systematic-debugging`
  - Antes de declarar concluído: `superpowers:verification-before-completion`
  - Fim de funcionalidade relevante: `superpowers:requesting-code-review`
- **Skill do projeto para análise dos pedidos de orçamento**:
  - Será criada com `skill-creator:skill-creator`, em `.claude/skills/`.
  - Depois de criada, **toda tarefa do projeto a usa como guia**. Ela concentra o procedimento completo de análise: interpretação do pedido, perguntas complementares, identificação do motor, busca de peças, evidências e auditoria.
  - Mudanças nela são feitas via `skill-creator:skill-creator`, com plano aprovado.
  - Enquanto ela não existir, valem as regras deste arquivo. Não improvisar o procedimento de análise.
- Em caso de conflito: pedido direto do usuário > este CLAUDE.md > skills.

## Regras de engenharia

- Python para tudo que é determinístico: a mesma entrada deve produzir a mesma saída.
- Proibido chamar APIs de LLM no código Python e proibido ter SDK de LLM como dependência.
- **Banco somente leitura**: abrir o SQLite em modo read-only (`mode=ro`). Nunca alterar `db_proj_final.db`, nem para corrigir dados. Correções viram itens para revisão humana.
- SQL sempre parametrizado. Nunca concatenar entrada do usuário em SQL.
- API: todo endpoint com modelos Pydantic de entrada e de saída, descrição e exemplos, para que o Swagger documente o contrato completo.
- Separar rotas da API, regras de negócio e acesso a dados, para que as regras sejam testáveis sem HTTP.
- Type hints em todo código público.
- Ler e gravar texto em UTF-8, preservando acentos (JSON com `ensure_ascii=False`).
- Testes com pytest, em `tests/`. Não dependem de rede. Usam o banco em modo leitura ou bases SQLite de teste criadas pelos próprios testes em diretório temporário.
- JSON e Excel são sempre gerados pelo código, nunca editados à mão.
- Nenhuma dependência sem uso real. Nenhum segredo ou credencial no código.

## Confiabilidade dos dados

- **Nunca inventar, estimar ou completar valores sem evidência na base.**
- Dado ausente = `null`. Nunca usar string vazia, zero ou valor padrão no lugar.
- Preservar sempre, lado a lado, o **valor original** (como está na base) e o **valor normalizado**.
- Todo valor usado no resultado carrega sua evidência: tabela, chave do registro, coluna e valor original.
- Conhecimento do agente e fontes externas (web, MCP) **não são evidência**. No máximo, motivam um item para revisão humana.
- O motor só é considerado identificado quando a base deixa **exatamente um** candidato. Com mais de um, perguntar informações complementares. Nunca escolher por suposição.
- Sinalizar explicitamente conflitos, ambiguidades, duplicidades e baixa confiança.
- Exigir revisão humana quando houver conflito não resolvido, baixa confiança, dado ausente que afete o orçamento, ou preço ausente, zerado ou suspeito.
- Não atribuir significado a colunas desconhecidas sem evidência ou confirmação do usuário. Hoje: `PRODUTO.CpoAuxProd5`, `CpoAuxProd25`, `PCs`, `CodigoSimilar`, `NumeroProdutoPesq`.
- Problemas conhecidos da base, a tratar como conflitos e nunca corrigir em silêncio (medidos em `docs/dados.md`; decisões pendentes em `docs/pendencias.md`):
  - só há veículos Nissan (fabricante 73);
  - não há duplicatas exatas em `APLICACAO`, mas há registros sobrepostos (o mesmo veículo descrito de formas diferentes);
  - há combustíveis conflitantes (ex.: Kicks 2018 aparece como FLEX e como GASOLINA);
  - a maioria dos produtos não tem preço, e os produtos vinculados formam pares "número" × "`#NAC_`número";
  - há 212 vínculos `PRODUTO_APLICACAO` para aplicações inexistentes.

## Validação

Antes de declarar qualquer tarefa concluída:

1. **Testes**: `.venv\Scripts\python.exe -m pytest`, todos passando, com a saída real mostrada.
2. **API**: subir com Uvicorn, confirmar que `/docs` e `/openapi.json` respondem e exercitar os endpoints alterados.
3. **Auditoria**: `.venv\Scripts\python.exe -m orcamento_pecas auditoria` sem falhas de invariante e com o SHA-256 da base inalterado.
4. **Auditoria dos resultados**:
   - todo valor no JSON tem evidência;
   - dados ausentes estão como `null` e registrados;
   - conflitos e ambiguidades estão listados;
   - os itens para revisão humana estão presentes quando exigidos;
   - os totais recalculados batem com os itens;
   - JSON e Excel são consistentes entre si.
5. Falhas são relatadas com a saída do comando, sem omitir nem suavizar.
6. Sem evidência de verificação, não afirmar sucesso.

## Versionamento

- Git, com remoto `origin` (GitHub `rsnogueira/projeto-final`) e branch principal `main`.
- Commit e push **somente quando o usuário pedir**.
- Implementação em branch própria, criada a partir da `main`. A integração acontece após a validação (`superpowers:finishing-a-development-branch`).
- Commits pequenos e coesos, cada um com os testes passando. Mensagens em português, curtas, descrevendo a intenção.
- Nunca versionar `.venv/`, `.claude/settings.local.json`, credenciais ou arquivos temporários.
- `db_proj_final.db` é versionado e não é alterado por código. Qualquer mudança no banco só com autorização explícita.
- `requirements.txt` passa a ser versionado quando for gerado, no final.
