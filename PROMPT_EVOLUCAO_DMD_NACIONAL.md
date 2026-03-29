# PROMPT PARA CLAUDE CODE — EVOLUÇÃO DMD SAÚDE BRASIL
## De dashboard básico → Plataforma de Inteligência Nacional em Saúde
**Data: 29/03/2026 | EMET Gestão Brasil Ltda | Karina Barros, CEO**

---

## CONTEXTO

O DMD Saúde Brasil v9.0 atual tem 9 módulos relativamente superficiais (Nacional, Mapa, Ranking, Saúde Mental, Atenção Básica, Fiscal, Vacinação, Risco, Agente IA). No entanto, o banco de dados modelo do **Amazonas** (`Banco_DMD_Saude_05-03-26.xlsx`) possui **73 planilhas** com camadas de análise profundas que precisam ser replicadas nacionalmente para os 5.569 municípios e 27 UFs.

O objetivo é transformar o dashboard de um painel informativo em uma **plataforma de inteligência decisória** que nenhum gestor público brasileiro jamais teve acesso — com dados 100% públicos e auditáveis.

---

## MAPEAMENTO: 73 PLANILHAS DO AMAZONAS → 12 CAMADAS NACIONAIS

### CAMADA 1 — DIAGNÓSTICO MUNICIPAL PROFUNDO (existe parcial, ampliar)
**Planilhas modelo AM:** `DIAGNOSTICO_POR_MUNICIPIO_OMAR` (62 munic × 42 colunas), `MUNICIPAL_62`, `DADOS_POPULACIONAIS_ATUAL`, `CNES_MUNICIPAL_62`

O diagnóstico do AM tem **42 campos por município**. O dashboard nacional tem ~20. Campos que FALTAM no nacional:

| Campo AM | Fonte Nacional | Prioridade |
|----------|---------------|------------|
| `LEITOS_UTI` | CNES/TabNet | P1 |
| `MEDICOS` (absoluto + /1000 hab) | CNES profissionais | P1 |
| `ENFERMEIROS` | CNES profissionais | P1 |
| `PRODUCAO_AIH_ANO` | SIH/DATASUS | P1 |
| `PRODUCAO_AMBULATORIAL_ANO` | SIA/DATASUS | P1 |
| `RECEITA_SUS_ANO_R$` | SIH+SIA/DATASUS | P2 |
| `RECEITA_PER_CAPITA_R$` | Calculado | P2 |
| `FILA_SISREG` | SISREG (estadual) | P3 |
| `GLOSA_%` e `GLOSA_VALOR_R$` | SIH/DATASUS | P2 |
| `MORTALIDADE_INFANTIL` | SIM/DATASUS | P1 |
| `MORTALIDADE_MATERNA` | SIM/DATASUS | P1 |
| `LEITOS_NECESSARIOS_P1631` | Portaria 1.631/2015 | P1 |
| `DEFICIT_LEITOS_ABS` e `%` | Calculado | P1 |
| `DEFICIT_UTI_ABS` e `%` | Calculado | P1 |
| `INVESTIMENTO_NECESSARIO_R$` | Calculado | P2 |
| `CRITICIDADE_GERAL` | Score composto | P1 |

**Ação Claude Code — FASE 1:**
```
Ampliar o objeto MUNIS de ~20 campos para ~42 campos por município.
Fontes: CNES/TabNet (leitos UTI, médicos, enfermeiros), SIH/DATASUS (produção AIH),
SIA/DATASUS (produção ambulatorial), SIM/DATASUS (mortalidade).
Calcular: déficit de leitos (Portaria 1.631/2015), criticidade geral (score composto).
Adicionar ao pipeline de coleta e ao banco CSV canônico.
```

---

### CAMADA 2 — QUALIDADE ASSISTENCIAL (nova)
**Planilhas modelo AM:** `QUALIDADE_ASSISTENCIAL`, `QUALIDADE_PNASS`

Indicadores por UF e por hospital/município:
- **Taxa de mortalidade hospitalar** (óbitos/AIH) — benchmark < 4%
- **Taxa de reinternação 30 dias** — benchmark < 5,6%
- **Tempo médio de permanência (TMP)** — benchmark < 5,5 dias
- **Taxa de ocupação leitos** — ideal 75-85%
- **Taxa de cesáreas** — benchmark OMS < 15%
- **Semáforo de qualidade** (🟢🟡🔴)

**Fonte nacional:** SIH/DATASUS (RD files — dados de internação) + CNES (leitos)

**Ação Claude Code — FASE 2:**
```
Criar aba "QUALIDADE" no dashboard com:
- Cards KPI: mortalidade hospitalar, reinternação 30d, TMP, ocupação (por UF)
- Tabela: ranking de UFs por qualidade assistencial
- Gráfico: scatter plot (mortalidade × ocupação) com benchmark nacional
- Mapa coroplético: qualidade assistencial por UF
Dados: calcular a partir de SIH/DATASUS (AIH, óbitos hospitalares, dias permanência)
```

---

### CAMADA 3 — EFICIÊNCIA OPERACIONAL (nova)
**Planilhas modelo AM:** `EFICIENCIA_OPERACIONAL`, `PARETO_RESUMO`, `PARETO_GLOSA`, `PARETO_GAPS`, `PARETO_ROI`, `PARETO_SCORE_COMBINADO`, `PLANO_ACAO_8020`

O AM tem uma análise Pareto 80/20 sofisticada com score combinado (Glosa 40% + ROI 30% + Qualidade 30%). Nacionalizar:

- **Custo médio por AIH** por UF — benchmark R$ 1.200-2.500
- **Receita SUS per capita** por UF
- **Giro de leito** (internações/leito/mês)
- **Índice de Eficiência Operacional (IEO)** 0-100
- **Análise Pareto:** 20% das UFs que concentram 80% dos problemas

**Fonte nacional:** SIH/DATASUS (valores AIH) + CNES (leitos) + SIOPS (receitas)

**Ação Claude Code — FASE 2:**
```
Criar aba "EFICIÊNCIA" expandida com:
- Cards KPI: custo/AIH médio nacional, giro leito, IEO médio
- Pareto chart: UFs ordenadas por concentração de ineficiência
- Tabela: ranking UFs por IEO (score 0-100)
- Scatter: custo/AIH × ocupação × bolha=volume_aih por UF
```

---

### CAMADA 4 — IDH HOSPITALAR (nova — indicador proprietário DMD)
**Planilha modelo AM:** `IDH_HOSPITALAR_AM`

Índice composto proprietário EMET:
```
IDH-H = D1_Financeiro × 25% + D2_Qualidade × 25% + D3_Eficiência × 20% + D4_Acesso × 15% + D5_Regulação × 15%
```
- 🟢 EXCELENTE ≥ 80 | 🟡 BOM 65-79 | 🟠 REGULAR 50-64 | 🔴 CRÍTICO < 50

**Nacionalizar:** Calcular IDH-H por UF (e futuramente por município).

**Ação Claude Code — FASE 3:**
```
Criar aba "IDH-H" (Índice de Desempenho Hospitalar) com:
- Fórmula: 5 dimensões ponderadas
- Ranking: 27 UFs ordenadas por IDH-H
- Mapa coroplético: IDH-H por UF com escala de cores
- Decomposição: radar chart das 5 dimensões para UF selecionada
- Comparativo: UF selecionada vs média nacional
```

---

### CAMADA 5 — DESERTOS DE SAÚDE (nova)
**Planilhas modelo AM:** `MAPA_DESERTOS_SAUDE`, `GEORREFERENCIAMENTO`

O AM mapeou 62 municípios com classificação de deserto:
- Município sem UTI + sem maternidade + tempo > 6h da capital
- Risco materno, risco infarto/AVC, risco oncológico
- Nível de deserto (crítico/severo/moderado)
- Tempo de deslocamento (estrada/barco/aéreo)
- População vulnerável estimada

**Nacionalizar:** Identificar desertos de saúde em todos os 5.569 municípios.

**Critérios de deserto nacional:**
- 0 leitos UTI + população > 20k
- 0 leitos obstétricos + mais de 100 NV/ano
- Nenhum hospital SUS no raio de 60km
- Cobertura ESF < 40%

**Ação Claude Code — FASE 3:**
```
Criar aba "DESERTOS" com:
- KPI: total de municípios classificados como deserto, população afetada
- Mapa: municípios-deserto destacados no Leaflet
- Tabela: ranking desertos por gravidade
- Filtro: tipo de deserto (UTI, maternidade, atenção básica, combinado)
```

---

### CAMADA 6 — ACESSO E REGULAÇÃO (nova)
**Planilhas modelo AM:** `ACESSO_REGULACAO`, `SISREG_FILA_ESPERA`, `MATRIZ_ORIGEM_DESTINO`

- **Fluxo de pacientes** (origem-destino): autossuficiência vs evasão por UF
- **Fila de espera** por especialidade (dados SISREG estaduais)
- **Cobertura hospitalar** por macrorregião de saúde

**Fonte nacional:** SIH/DATASUS (município de residência × município de internação)

**Ação Claude Code — FASE 4:**
```
Criar aba "ACESSO" com:
- Sankey/flow diagram: fluxo inter-UF de internações
- KPI: % autossuficiência por UF, evasão para capitais
- Tabela: matriz origem-destino simplificada (27×27 UFs)
- Indicador: municípios com >50% de evasão para internações
```

---

### CAMADA 7 — EPIDEMIOLOGIA (nova)
**Planilha modelo AM:** `EPIDEMIOLOGIA_MUNICIPAL`

Perfil epidemiológico por UF:
- **Natalidade:** nascidos vivos, % prematuros, % baixo peso, % pré-natal 7+, % cesáreas
- **Mortalidade:** coeficiente geral, infantil/1k NV, materna/100k, % causas externas
- **Doenças notificáveis:** dengue, tuberculose, hanseníase, malária (para UFs endêmicas)

**Fonte nacional:** SINASC, SIM, SINAN/DATASUS

**Ação Claude Code — FASE 4:**
```
Criar aba "EPIDEMIOLOGIA" com:
- Dashboard: perfil epidemiológico da UF selecionada
- Indicadores: mortalidade infantil, materna, prematuridade
- Comparativo: UF vs média nacional em cada indicador
- Mapa: mortalidade infantil coroplético por UF
```

---

### CAMADA 8 — FINANCEIRO E CONTRATOS (nova)
**Planilhas modelo AM:** `CONTRATOS_PORTAL_SGC` (4.326 contratos), `FINANCEIRO_UG_ANO`, `EXEC_DESP_SUSAM_CEMA` (19.883 empenhos), `TOP_CREDORES`, `CUSTOS_ABC`, `ALTO_CUSTO_APAC`

Esta é a camada mais complexa e politicamente sensível. Para o nacional:
- **Transferências federais** por UF e município (FNS/Fundo a Fundo)
- **Execução orçamentária** em saúde por UF (SIOPS)
- **Custeio ABC** por procedimento (SIGTAP)
- **Alto custo** (TRS, oncologia, transplantes) por UF

**Fonte nacional:** SIOPS/FNS + Portal da Transparência Federal + SIGTAP

**Ação Claude Code — FASE 5:**
```
Expandir aba "FISCAL" para incluir:
- Transferências federais: FNS → UFs → municípios (mapa de calor)
- Top procedimentos: Pareto de gastos SUS por grupo de procedimento
- Alto custo: TRS, onco, transplantes — volume e valor por UF
- Concentração: % do orçamento nos top 10 procedimentos por UF
```

---

### CAMADA 9 — BENCHMARKING COMPARATIVO (nova)
**Planilhas modelo AM:** `BENCHMARKING_NACIONAL`, `BENCHMARKING_NORTE`, `COMPARATIVO_SISREG_AM_BR`, `SERIES_HISTORICAS_2020_2025`, `COMPARATIVO_2024_2025`

O AM compara contra PA, MT, RO, TO e média Brasil. Nacionalizar:
- **Ranking UF** em cada indicador (1º a 27º)
- **Posição relativa** da UF vs média nacional
- **Séries históricas** 2020-2025 (6 anos) para cada indicador
- **Benchmark região**: UF vs média da sua região (N, NE, SE, S, CO)

**Ação Claude Code — FASE 3:**
```
Criar aba "BENCHMARKING" com:
- Seletor de UF → mostra posição em 15+ indicadores
- Spider/radar: UF vs média nacional vs melhor UF vs pior UF
- Linha do tempo: evolução 2020-2025 de indicadores-chave
- Tabela: ranking completo 27 UFs por indicador selecionado
```

---

### CAMADA 10 — GESTÃO DE RISCO (nova)
**Planilhas modelo AM:** `MATRIZ_RISCO_UNIDADES`, `MATRIZ_RISCO_GAPS`, `RISCO_CONSOLIDADO`, `ALERTAS_GESTAO`, `PESTEL_SAUDE_AM`

Expandir o módulo de risco atual (que é só classificação Crítico/Alto/Médio/Baixo) para:
- **Matriz de risco 5×5** (probabilidade × impacto) por UF
- **Dimensões:** Financeiro, Qualidade, Acesso, Operacional, Reputacional
- **Score consolidado** integrado
- **Painel de alertas** com semáforo (🚨 Emergência, 🔴 Crítico, 🟡 Atenção, 🟢 OK)

**Ação Claude Code — FASE 4:**
```
Expandir aba "RISCO" para:
- Matriz 5×5 visual (heatmap probabilidade × impacto)
- Score de risco por UF (decomponível em 5 dimensões)
- Timeline de alertas: alertas ativos ordenados por gravidade
- Top 10 municípios em risco por dimensão
```

---

### CAMADA 11 — COCKPIT EXECUTIVO (nova)
**Planilha modelo AM:** `COCKPIT_EXECUTIVO` (4 radares: Financeiro, Qualidade, Acesso, Eficiência)

Página de resumo executivo "one-page" com todos os KPIs críticos:
- 🎯 4 radares temáticos com KPIs e semáforos
- Total de KPIs no cockpit AM: 32 indicadores com status
- Cada KPI: valor atual + benchmark/meta + status (🟢🟡🔴)

**Ação Claude Code — FASE 5:**
```
Criar aba "COCKPIT" como página de abertura do dashboard:
- Layout: 4 quadrantes (Financeiro, Qualidade, Acesso, Eficiência)
- Cada quadrante: 6-8 KPIs com valor, meta/benchmark, semáforo
- Interação: clicar num KPI → navega para a aba detalhada
- Filtro: Nacional / por UF
```

---

### CAMADA 12 — MÓDULO PREDITIVO (futuro)
**Planilha modelo AM:** `MODULO_PREDITIVO_IA`

Regressão e previsão:
- Previsão de glosa por unidade
- Tendência de ocupação hospitalar
- Projeção de demanda por especialidade
- Alertas antecipados baseados em tendência

**Ação Claude Code — FASE 6 (futuro):**
```
Integrar no AGENTE DMD v26 a capacidade de:
- Projetar tendências dos indicadores (regressão linear simples)
- Gerar alertas antecipados quando indicador cruza threshold
- Responder "qual a projeção de mortalidade infantil do AM para 2027?"
```

---

## ROADMAP DE EXECUÇÃO

### FASE 1 — Ampliar profundidade dos dados municipais (PRIORIDADE IMEDIATA)
- Ampliar MUNIS de ~20 para ~42 campos
- Adicionar: leitos UTI, médicos, enfermeiros, produção AIH/SIA, mortalidade, déficit Portaria 1.631
- **Pipeline:** coletar via TabNet POST (SIH, SIA, SIM, CNES profissionais)
- **Entregável:** banco CSV v41 com 5.569 × 42+ colunas

### FASE 2 — Novas abas: Qualidade + Eficiência (semana 2)
- Aba QUALIDADE: mortalidade hospitalar, reinternação, TMP, ocupação
- Aba EFICIÊNCIA expandida: custo/AIH, Pareto, IEO, giro de leito
- **Entregável:** dashboard v10.0 com 11 módulos

### FASE 3 — IDH-H + Benchmarking + Desertos (semana 3)
- Aba IDH-H: índice proprietário EMET com 5 dimensões
- Aba BENCHMARKING: ranking UF, radar, séries históricas
- Aba DESERTOS: mapeamento nacional de desertos de saúde
- **Entregável:** dashboard v11.0 com 14 módulos

### FASE 4 — Acesso + Epidemiologia + Risco expandido (semana 4)
- Aba ACESSO: fluxo origem-destino, autossuficiência
- Aba EPIDEMIOLOGIA: perfil por UF (natalidade, mortalidade, doenças)
- Aba RISCO expandida: matriz 5×5, score consolidado, alertas
- **Entregável:** dashboard v12.0 com 17 módulos

### FASE 5 — Financeiro expandido + Cockpit (semana 5)
- Aba FISCAL expandida: transferências FNS, SIGTAP, alto custo
- Aba COCKPIT: one-page executivo com 4 radares e 32 KPIs
- **Entregável:** dashboard v13.0 com 19 módulos

### FASE 6 — Módulo preditivo + Polish (semana 6+)
- Projeções no AGENTE DMD
- Testes Playwright completos em todos os módulos
- Otimização de performance (arquivo ~25-30 MB estimado)
- **Entregável:** dashboard v14.0 — versão comercial completa

---

## REGRAS TÉCNICAS PARA TODAS AS FASES

1. **Single-file HTML** — continua sendo um único arquivo
2. **Dados inline comprimidos** — raw deflate (wbits=-15) no MUNIS
3. **Fontes 100% públicas** — CNES, SIH, SIA, SIM, SINASC, SIOPS, IBGE, FNS
4. **Auditável** — toda fonte com data de coleta e URL de verificação
5. **Performance** — lazy load por aba, só renderizar quando visível
6. **Offline first** — funcionar em file:// sem servidor
7. **pt-BR** — todo texto em português brasileiro
8. **Marca EMET** — Navy #0D1B2A + Teal #00C6BD em todas as visualizações

---

## INSTRUÇÃO PARA O CLAUDE CODE

Leia o arquivo `Banco_DMD_Saude_05-03-26.xlsx` (73 planilhas do Amazonas) que está no repositório. 
Este banco é o MODELO de profundidade analítica que queremos replicar nacionalmente.

**Comece pela FASE 1:** Identifique no banco CSV atual (`dmd_banco_v40_integrado.csv`) quais dos 42 campos do diagnóstico municipal do AM já existem e quais faltam. Depois, crie o pipeline de coleta para os campos faltantes usando TabNet POST requests.

Ao final de cada fase, faça commit com a mensagem no formato:
```
feat(camadaN): descrição da camada adicionada
```

Exemplo:
```
feat(camada1): ampliar MUNIS para 42 campos — leitos UTI, médicos, produção, mortalidade
feat(camada2): nova aba Qualidade Assistencial — mortalidade hosp, reinternação, TMP
feat(camada3): IDH-H nacional — índice proprietário EMET com 5 dimensões por UF
```
