# Auditoria automática e revisão manual por amostragem

## Como rodar

```powershell
.venv\Scripts\python.exe -m orcamento_pecas auditoria [--banco <caminho>] [--amostra 30] [--semente 42] [--saida saidas/auditoria]
```

O comando gera `saidas/auditoria/auditoria_<AAAAMMDD-HHMMSS>.json` e `.xlsx`, com o mesmo conteúdo. A pasta `saidas/` não é versionada.

Códigos de saída:
- `0`: nenhuma falha de invariante;
- `1`: há falhas;
- `2`: o banco não foi encontrado.

Na base real (2026-11-10), a auditoria executou 1.202 consultas e conferiu 57.814 valores, inclusive as evidências citadas nos alertas, com **0 falhas**, em cerca de 34 s.

## O que é verificado

**1. Qualidade da base.** São alertas, e não fazem o comando falhar:
- os alertas de cada aplicação (anos, faixa, motorização, descrição, referências);
- conflitos de combustível no nível da base (mesmo modelo-base e mesmo motor, com anos sobrepostos e combustíveis diferentes);
- vínculos órfãos e referências inexistentes;
- preço e dados ausentes nos produtos vinculados;
- possíveis duplicidades.

**2. Bateria de consultas.** Para cada modelo-base, em cada ano das suas faixas (a faixa aberta vai até o maior ano final da base), roda:
- `motorizacoes` e `combustiveis`;
- `/v1/pecas`: sem chave de motor, com cada chave candidata e com cada combustível;
- `motorizacoes` filtrada por cada combustível.

Depois roda a busca de veículos por modelo, o detalhe e as peças de cada aplicação e o detalhe de cada produto vinculado.

**3. Invariantes.** Valem para toda resposta da bateria. Qualquer violação é **falha**:

| Invariante | O que garante |
|---|---|
| I0 | Toda consulta da bateria teve resposta, e o arquivo do banco não mudou durante a auditoria (SHA-256 antes e depois). |
| I1 | Cada evidência, relida na base, confere com o valor original devolvido (mesmo valor e mesmo tipo). Vale para os valores e para as evidências citadas nos alertas. |
| I2 | Todo `normalizado: null` tem um alerta que cita a mesma evidência. |
| I3 | `revisao_humana` é coerente com os alertas de severidade revisão. |
| I4 | `identificado` é verdadeiro só com exatamente 1 candidato, e `unico` só com exatamente 1 combustível. |
| I5 | Toda aplicação devolvida satisfaz de fato os filtros de modelo, ano e combustível (rechecado a partir dos valores devolvidos). |
| I6 | As listagens não têm itens repetidos, e `total`, `pagina` e `limite` são coerentes. |

## A planilha

| Aba | Conteúdo |
|---|---|
| `Resumo` | Consultas, valores conferidos, falhas por invariante, alertas da base por código e tamanho da população e da amostra. |
| `Falhas` | Cada violação, com a consulta, o detalhe e a evidência. |
| `Alertas_base` | Uma linha por evidência de cada alerta de qualidade da base. |
| `Amostra_revisao` | A amostra para revisão manual (ver abaixo). |
| `Metadados` | Data, banco, SHA-256 inicial e final, semente, tamanho da amostra, comando e versão. |

## Revisão manual por amostragem

**Como a amostra é sorteada:**
- A população é o conjunto de valores rastreados distintos (tabela, chave e coluna) que aparecem nas respostas da bateria.
- O sorteio é determinístico (a mesma semente gera a mesma amostra) e estratificado: metade com alerta de revisão e metade limpa. Quando um estrato não tem itens suficientes, o outro completa.

**Como revisar:**
1. Abra a aba `Amostra_revisao`. Cada linha traz a consulta (rota do Swagger), o campo, o valor exibido, o valor original (em JSON, para distinguir `""` de `null`) e a evidência, além do **SQL de conferência**, pronto para rodar em qualquer cliente SQLite.
2. Para cada linha, rode o SQL e compare o resultado com o "Valor original". Confira também se o "Valor exibido" (normalizado) faz sentido.
3. Preencha as colunas do revisor:
   - `Conferido (S/N)`: `S` ou `Sim` se confere, `N` ou `Não` se não confere. Qualquer outro valor é listado como **inválido**;
   - `Divergência`: preencher sempre que houver diferença (qualquer texto ali conta como divergência);
   - `Comentário`, `Revisor` e `Data`.
4. Salve a planilha e gere o resumo:

```powershell
.venv\Scripts\python.exe -m orcamento_pecas revisao saidas/auditoria/auditoria_<...>.xlsx
```

O resumo traz conferidos, divergências, pendentes e inválidos, em JSON. O comando sai com `1` se houver divergência ou valor inválido. Toda divergência deve virar uma pendência em [pendencias.md](pendencias.md) e ser investigada antes de qualquer correção.
