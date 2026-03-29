# PLANO DE EVOLUÇÃO DMD SAÚDE BRASIL — 6 FASES
## De V43 (15 módulos, 115 campos) → V49 (21+ módulos, ~160 campos)
**Data: 29/03/2026 | EMET Gestão Brasil Ltda**

---

## ESTADO ATUAL (V43)

| Dimensão | Valor |
|----------|-------|
| Módulos | 15 ativos |
| Campos por município | 115 |
| Municípios | 5.569 |
| Tamanho index.html | 4.6 MB (~16.6k linhas) |
| Banco CSV | dmd_banco_v40_integrado.csv (3.9 MB) |
| Pipeline scripts | 10 scripts Python (00_ a 04_) |
| Dados CNES reais | 645 municípios (11.6%) |
| Estimativas | 3.656 municípios (65.6%) |

---

## FASE 1 — AMPLIAR PROFUNDIDADE DOS DADOS MUNICIPAIS

### Objetivo
Ampliar de 115 para ~130 campos por município, adicionando indicadores que existem no banco modelo AM mas faltam no nacional.

### Análise de Gap: Campos que FALTAM

| Campo | Fonte | Método de Coleta | Viabilidade | Prioridade |
|-------|-------|------------------|-------------|------------|
| `medicos_abs` | CNES profissionais | PySUS grupo PF | ✅ Alta — PySUS já coleta EP | P1 |
| `enfermeiros_abs` | CNES profissionais | PySUS grupo PF | ✅ Alta | P1 |
| `producao_aih_ano` | SIH/DATASUS | TabNet POST `sih/cnv/nihr*.def` | ✅ Alta — formato conhecido | P1 |
| `producao_amb_ano` | SIA/DATASUS | TabNet POST `sia/cnv/qa*.def` | ✅ Alta | P1 |
| `mortalidade_infantil` | SIM/DATASUS | TabNet POST `sim/cnv/inf*.def` | ✅ Alta — dados anuais | P1 |
| `mortalidade_materna` | SIM/DATASUS | TabNet POST `sim/cnv/mat*.def` | ⚠️ Média — baixa freq, calc 100k NV | P1 |
| `leitos_necessarios_p1631` | Calculado | `pop × 2.5 / 1000` | ✅ Trivial | P1 |
| `deficit_leitos_abs` | Calculado | `max(0, necessarios - leitos_sus)` | ✅ Trivial | P1 |
| `deficit_leitos_pct` | Calculado | `deficit / necessarios × 100` | ✅ Trivial | P1 |
| `deficit_uti_abs` | Calculado | Portaria: `pop × 0.1 / 1000 - uti_sus` | ✅ Trivial | P1 |
| `deficit_uti_pct` | Calculado | `deficit / necessarios × 100` | ✅ Trivial | P1 |
| `receita_sus_ano` | SIH+SIA | Soma valores pagos AIH + BPA | ⚠️ Média — requer cruzamento | P2 |
| `receita_per_capita` | Calculado | `receita_sus_ano / pop` | ✅ Trivial (depende receita) | P2 |
| `glosa_pct` | SIH/DATASUS | `(apresentado - aprovado) / apresentado` | ⚠️ Média — precisa campos extras | P2 |
| `glosa_valor` | SIH/DATASUS | `apresentado - aprovado` | ⚠️ Média | P2 |
| `criticidade_geral` | Calculado | Score composto 0-100 (5 dimensões) | ✅ Alta — fórmula proprietária | P1 |
| `investimento_necessario` | Calculado | `deficit_leitos × custo_leito_medio` | ⚠️ Média — precisa benchmark custo | P2 |

### Campos que JÁ EXISTEM (não precisam ser coletados)

| Campo AM | Campo equivalente no banco V43 |
|----------|-------------------------------|
| LEITOS_UTI | `uti_sus` ✅ |
| MEDICOS /1000 hab | `medicos_1k` ✅ |
| ENFERMEIROS /1000 hab | `enfermeiros_1k` ✅ |
| LEITOS_NECESSARIOS | Parcial — `mod-leitos` já calcula com P.1631 mas não persiste no CSV |
| DEFICIT_LEITOS | Parcial — calculado no frontend, não está no banco |
| MORTALIDADE (crônicas) | `mort_cv_100k`, `mort_dm_100k`, `mort_has_100k` ✅ |

### Entregáveis FASE 1

1. **Novo script pipeline:** `pipeline/scripts/05_coletor_sih_sia.py`
   - POST TabNet para SIH (produção AIH por município)
   - POST TabNet para SIA (produção ambulatorial por município)
   - Output: JSON com produção/valores por IBGE6

2. **Novo script pipeline:** `pipeline/scripts/06_coletor_mortalidade.py`
   - POST TabNet para SIM (mortalidade infantil, materna)
   - Cálculo: taxa por 1k NV (infantil), taxa por 100k NV (materna)

3. **Atualização:** `pipeline/scripts/02_normalizador_validador.py`
   - Novas regras de validação para campos adicionados
   - Cálculos derivados: déficit P.1631, criticidade geral

4. **Banco CSV v41:** `dmd_banco_v41_integrado.csv`
   - 5.569 × ~130 colunas
   - Novos campos incorporados

5. **Atualização index.html:**
   - Re-encode MUNIS_FULL_B64 com campos novos
   - Atualizar módulos existentes para usar novos dados
   - mod-leitos: adicionar dados persistidos de déficit
   - mod-nacional: exibir novos KPIs (mortalidade infantil, produção AIH)

### Estimativa de Esforço
- Pipeline (3 scripts): ~500 linhas Python
- Normalização: ~100 linhas adições
- Dashboard: ~200 linhas alterações
- **Total: ~800 linhas | 1-2 sessões de trabalho**

### Riscos
- TabNet pode estar fora do ar → fallback: dados anuais pré-baixados
- SIM (mortalidade) tem defasagem de ~2 anos → usar último disponível (2023/2024)
- SIA (ambulatorial) tem volume muito grande → agregar por município antes de baixar

---

## FASE 2 — NOVAS ABAS: QUALIDADE + EFICIÊNCIA EXPANDIDA

### Objetivo
Dois novos/expandidos módulos no dashboard: Qualidade Assistencial (novo) e Eficiência expandida.

### 2A — MÓDULO QUALIDADE ASSISTENCIAL (`mod-qualidade`)

**Indicadores por UF (27 UFs):**

| Indicador | Fórmula | Benchmark | Fonte |
|-----------|---------|-----------|-------|
| Taxa mortalidade hospitalar | `óbitos_hosp / total_aih × 100` | < 4% | SIH/RD |
| Taxa reinternação 30d | `reint_30d / total_aih × 100` | < 5.6% | SIH/RD |
| Tempo médio permanência (TMP) | `total_dias / total_aih` | < 5.5 dias | SIH/RD |
| Taxa ocupação leitos | `dias_perm / (leitos × 365) × 100` | 75-85% | SIH + CNES |
| Taxa cesáreas | `cesareas / partos × 100` | < 15% OMS | SIH/RD |

**Viabilidade de dados:**
- ✅ Todos calculáveis a partir do SIH/DATASUS (arquivos RD — Reduzidas de AIH)
- ✅ PySUS já baixa arquivos RD via `pysus.online_data.SIH.download()`
- ⚠️ Reinternação 30d requer cruzamento por CPF/CNS — disponível no RD mas pesado
- ⚠️ Volume: ~12 milhões de AIH/ano → processar por UF, não nacional de uma vez

**Componentes do módulo:**
1. **6 cards KPI** — cada indicador com valor nacional + semáforo
2. **Tabela ranking** — 27 UFs ordenadas por qualidade composta (sortable)
3. **Scatter plot** — mortalidade hospitalar × ocupação × bolha=volume AIH
4. **Seletor UF** — detalhamento por estado selecionado

**Esforço:** ~400 linhas HTML/CSS/JS no index.html + ~300 linhas pipeline

### 2B — EFICIÊNCIA EXPANDIDA (`mod-eficiencia` existente)

**Expansões sobre o módulo atual (6 dimensões → 8 dimensões):**

| Nova dimensão | O que adiciona |
|---------------|----------------|
| Custo médio por AIH | `valor_total_aih / qtd_aih` por UF — benchmark R$1.200-2.500 |
| Giro de leito | `aih_aprovadas / leitos_sus / 12` — rotatividade mensal |

**Novos componentes visuais:**
1. **Pareto chart** — 20% das UFs que concentram 80% da ineficiência
2. **Scatter expandido** — custo/AIH × ocupação × bolha=volume por UF
3. **IEO score** — Índice de Eficiência Operacional 0-100 (fórmula composta)

**Esforço:** ~250 linhas alterações no mod-eficiencia existente

### Pipeline FASE 2
- **Novo script:** `pipeline/scripts/07_processar_sih_rd.py`
  - Baixa arquivos RD do SIH via PySUS
  - Agrega por UF: óbitos, dias_perm, reinternações, cesáreas, valores
  - Output: `sih_qualidade_uf.json`
- **Integração:** Dados agregados por UF (não municipal) para manter performance

### Estimativa FASE 2
- Pipeline SIH/RD: ~400 linhas Python
- mod-qualidade (novo): ~600 linhas HTML/CSS/JS
- mod-eficiencia (expansão): ~250 linhas
- **Total: ~1.250 linhas | 2-3 sessões**

### Riscos
- Arquivos RD do SIH são pesados (~500MB/ano) → processar streaming por UF
- Reinternação 30d exige match por paciente → pode simplificar para proxy (readmissão)
- Dados SIH mais recentes: competência 10-12/2025 (defasagem ~3-4 meses)

---

## FASE 3 — IDH-H + BENCHMARKING + DESERTOS DE SAÚDE

### 3A — IDH HOSPITALAR (`mod-idhh`) — Indicador Proprietário EMET

**Fórmula:**
```
IDH-H = D1_Financeiro × 0.25 + D2_Qualidade × 0.25 + D3_Eficiência × 0.20 + D4_Acesso × 0.15 + D5_Regulação × 0.15
```

**Dimensões e sub-indicadores:**

| Dimensão | Peso | Sub-indicadores | Fonte |
|----------|------|-----------------|-------|
| D1 Financeiro | 25% | Receita SUS pc, % execução, glosa% | SIOPS + SIH |
| D2 Qualidade | 25% | Mort hospitalar, reinternação, TMP | SIH/RD (FASE 2) |
| D3 Eficiência | 20% | Custo/AIH, giro leito, ocupação | SIH + CNES (FASE 2) |
| D4 Acesso | 15% | Leitos/1k, ESF%, cobertura vacinal | CNES + e-Gestor (V43) |
| D5 Regulação | 15% | Autossuficiência AIH, evasão% | SIH (município res × int) |

**Classificação:**
- 🟢 EXCELENTE ≥ 80 | 🟡 BOM 65-79 | 🟠 REGULAR 50-64 | 🔴 CRÍTICO < 50

**Componentes visuais:**
1. **Ranking 27 UFs** com score IDH-H + classificação colorida
2. **Mapa coroplético** — IDH-H por UF (cores degradê verde→vermelho)
3. **Radar chart** — 5 dimensões para UF selecionada vs média nacional
4. **Decomposição** — barra empilhada mostrando contribuição de cada dimensão

**Dependências:** Requer dados de FASE 1 (produção, mortalidade) + FASE 2 (qualidade, eficiência)

**Esforço:** ~500 linhas HTML/CSS/JS | Dados: calculado a partir de fases anteriores

### 3B — BENCHMARKING COMPARATIVO (`mod-benchmark`)

**Funcionalidade:**
- Seletor de UF → posição em 15+ indicadores
- Radar: UF vs média nacional vs melhor UF vs pior UF
- Séries históricas 2020-2025 (requer dados retrospectivos)
- Ranking completo 27 UFs por indicador selecionado

**Viabilidade dados históricos:**
- ⚠️ Séries 2020-2025: requer coleta retrospectiva de TabNet (6 anos × indicadores)
- ✅ Rankings atuais: já disponíveis no banco V43 (rank_v3, rank_regiao_v3)
- ✅ Comparativo regional: dados de `regiao` já no banco

**Pipeline adicional:**
- Script para coletar dados históricos CNES 2020-2025 (leitos, ESF, CAPS) — já parcialmente em mod-series
- Reutilizar dados de `mod-series` que já tem séries temporais CNES 2020-25

**Esforço:** ~600 linhas HTML/CSS/JS + ~200 linhas pipeline retrospectivo

### 3C — DESERTOS DE SAÚDE (`mod-desertos`)

**Critérios de classificação (por município):**

| Critério | Condição | Classificação |
|----------|----------|---------------|
| Deserto UTI | `uti_sus == 0 AND pop > 20000` | Deserto UTI |
| Deserto Obstétrico | `leitos_obst == 0 AND nascimentos > 100/ano` | Deserto Obstétrico |
| Deserto APS | `esf_pct < 40%` | Deserto APS |
| Deserto Hospital | `leitos_sus == 0 AND pop > 10000` | Deserto Hospitalar |
| Combinado | 2+ critérios simultâneos | Deserto Severo/Crítico |

**Dados necessários que FALTAM:**
- `leitos_obst` (obstétricos) — CNES/TabNet leitos por tipo → **novo campo**
- `nascimentos` (NV/ano) — SINASC/DATASUS → **novo campo**
- Distância até hospital mais próximo — **cálculo geoespacial complexo, P3**

**Viabilidade:**
- ✅ UTI e APS: dados já existem (`uti_sus`, `esf_pct`)
- ⚠️ Obstétrico: precisa coletar leitos tipo 4 (obstétrico) do CNES — viável
- ⚠️ Nascimentos: SINASC via TabNet — viável mas dados anuais (2023/2024)
- ❌ Distância/raio 60km: exigiria cálculo haversine entre todos os municípios — simplificar para "município sem hospital SUS"

**Simplificação proposta:** Usar critérios que já temos (UTI, APS, leitos) + adicionar obstétrico/nascimentos.

**Componentes visuais:**
1. **KPIs** — total desertos, população afetada, % do total
2. **Mapa Leaflet** — municípios-deserto como círculos vermelhos
3. **Tabela** — ranking por gravidade (sortable)
4. **Filtro** — tipo de deserto (UTI, obstétrico, APS, hospitalar, combinado)

**Esforço:** ~700 linhas HTML/CSS/JS + ~200 linhas pipeline (obstétrico + NV)

### Estimativa FASE 3 Total
- mod-idhh: ~500 linhas
- mod-benchmark: ~600 linhas
- mod-desertos: ~700 linhas
- Pipeline: ~400 linhas
- **Total: ~2.200 linhas | 3-4 sessões**

---

## FASE 4 — ACESSO + EPIDEMIOLOGIA + RISCO EXPANDIDO

### 4A — ACESSO E REGULAÇÃO (`mod-acesso`)

**Indicador-chave: Autossuficiência hospitalar por UF**
```
Autossuficiência = AIH_residentes_internados_na_UF / AIH_total_residentes × 100
```

**Dados:** SIH/DATASUS — campo "município de residência" vs "município de internação"
- ✅ Viável via TabNet POST (tabela cruzada residência × internação)
- ⚠️ Matriz 27×27 UFs exige processamento significativo
- ❌ Sankey/flow diagram é complexo em Chart.js → usar diagrama simplificado (setas entre UFs)

**Componentes visuais:**
1. **KPIs** — autossuficiência nacional, UFs com > 30% evasão
2. **Chord/Matrix simplificada** — fluxo inter-UF (top 10 fluxos)
3. **Tabela** — ranking autossuficiência 27 UFs
4. **Barra empilhada** — para UF selecionada: % local vs % evasão vs % importação

**Esforço:** ~500 linhas HTML/CSS/JS + ~300 linhas pipeline

### 4B — EPIDEMIOLOGIA (`mod-epidemiologia`)

**Indicadores por UF:**

| Indicador | Fonte | Disponibilidade |
|-----------|-------|-----------------|
| Mortalidade infantil/1k NV | SIM/SINASC | ✅ — já previsto FASE 1 |
| Mortalidade materna/100k NV | SIM/SINASC | ✅ — já previsto FASE 1 |
| % Prematuros | SINASC | ✅ via TabNet |
| % Baixo peso ao nascer | SINASC | ✅ via TabNet |
| % Pré-natal 7+ consultas | SINASC | ✅ via TabNet |
| % Cesáreas | SINASC/SIH | ✅ — já previsto FASE 2 |
| Incidência dengue/100k | SINAN | ⚠️ — dados podem ter defasagem |
| Incidência tuberculose | SINAN | ⚠️ |
| Incidência hanseníase | SINAN | ⚠️ |

**Componentes visuais:**
1. **Perfil epidemiológico** — dashboard da UF selecionada com 9 indicadores
2. **Mapa** — mortalidade infantil coroplético por UF
3. **Comparativo** — UF vs média nacional (barras horizontais pareadas)
4. **Linha do tempo** — evolução 2020-2024 dos indicadores-chave

**Esforço:** ~600 linhas HTML/CSS/JS + ~300 linhas pipeline (SINASC + SINAN)

### 4C — RISCO EXPANDIDO (expansão `mod-sv3`)

**Expansão da Matriz de Risco Fiscal existente para Matriz 5×5:**

| Dimensão de Risco | Indicadores | Já existe? |
|-------------------|-------------|------------|
| Financeiro | glosa%, execução orç., alerta fiscal | ✅ Parcial |
| Qualidade | mort hospitalar, reinternação, TMP | ❌ Novo (FASE 2) |
| Acesso | leitos/1k, ESF%, evasão | ✅ Parcial |
| Operacional | giro leito, ocupação, custo/AIH | ❌ Novo (FASE 2) |
| Reputacional | mort infantil, cobertura vacinal, dengue | ✅ Parcial |

**Score consolidado:** média ponderada 5 dimensões → classificação 5 níveis

**Componentes visuais adicionais:**
1. **Heatmap 5×5** — probabilidade × impacto visual
2. **Score consolidado** por UF com decomposição
3. **Timeline de alertas** — alertas ativos ordenados por gravidade
4. **Top 10 municípios** em risco por dimensão

**Esforço:** ~400 linhas alterações no mod-sv3 existente

### Estimativa FASE 4 Total
- mod-acesso: ~800 linhas (módulo + pipeline)
- mod-epidemiologia: ~900 linhas (módulo + pipeline)
- mod-sv3 expandido: ~400 linhas
- **Total: ~2.100 linhas | 3-4 sessões**

---

## FASE 5 — FINANCEIRO EXPANDIDO + COCKPIT EXECUTIVO

### 5A — FINANCEIRO EXPANDIDO (expansão módulos existentes)

**Dados novos:**

| Dado | Fonte | Viabilidade |
|------|-------|-------------|
| Transferências FNS por UF | Portal FNS (fns.saude.gov.br) | ⚠️ Média — scraping ou download manual |
| Execução orçamentária SIOPS | SIOPS/FNS | ⚠️ Média — relatórios PDF/CSV |
| Top procedimentos SIGTAP | SIGTAP/DATASUS | ✅ Alta — tabela de procedimentos |
| Alto custo (TRS, onco) | SIA/APAC | ⚠️ Média — dados agregados por UF |

**Componentes:**
1. **Transferências FNS** — mapa de calor por UF (R$ per capita)
2. **Pareto procedimentos** — top 20 procedimentos por gasto
3. **Alto custo** — TRS, onco, transplantes (volume e valor por UF)
4. **Concentração** — % orçamento nos top 10 procedimentos

**Esforço:** ~600 linhas HTML/CSS/JS + ~400 linhas pipeline

### 5B — COCKPIT EXECUTIVO (`mod-cockpit`)

**Layout: 4 quadrantes temáticos**

| Quadrante | KPIs | Dados de |
|-----------|------|----------|
| 💰 Financeiro | Receita SUS pc, glosa%, exec orç., custo/AIH, transferência FNS pc | FASE 1+5 |
| 🏥 Qualidade | Mort hospitalar, reinternação, TMP, ocupação, cesáreas, IDH-H | FASE 2+3 |
| 🚪 Acesso | Leitos/1k, ESF%, cobertura vacinal, autossuficiência, desertos | FASE 1+3+4 |
| ⚙️ Eficiência | IEO, giro leito, score V3, criticidade, risco consolidado | FASE 1+2+4 |

**Cada KPI exibe:**
- Valor atual nacional
- Meta/benchmark de referência
- Semáforo (🟢🟡🔴)
- Sparkline de tendência (últimos 6 meses se disponível)
- Clique → navega para módulo detalhado

**Total de KPIs no cockpit:** 24-32 indicadores

**Interação:**
- Filtro: Nacional / por UF (seletor dropdown)
- Clicar em KPI → `switchMod()` para o módulo correspondente

**Esforço:** ~800 linhas HTML/CSS/JS (composição de dados de todas as fases anteriores)

### Estimativa FASE 5 Total
- Financeiro expandido: ~1.000 linhas
- Cockpit executivo: ~800 linhas
- **Total: ~1.800 linhas | 2-3 sessões**

---

## FASE 6 — MÓDULO PREDITIVO + POLISH

### 6A — Projeções no AGENTE DMD

**Capacidades:**
- Regressão linear simples em indicadores com série histórica
- Alertas antecipados quando indicador cruza threshold
- Responder perguntas do tipo "qual a projeção de X para 2027?"

**Implementação:** Integrar ao agente IA existente (se houver) ou criar componente JS simples com regressão linear.

**Esforço:** ~300 linhas JS

### 6B — Testes e Performance

**Testes Playwright:**
- Navegação entre todos os módulos
- Renderização de gráficos em cada aba
- Export CSV funcional
- Filtros e seletores operacionais

**Performance:**
- Lazy load rigoroso (só renderizar aba visível)
- Compressão otimizada do MUNIS_FULL_B64
- Considerar split do JSON por UF se > 10MB

**Esforço:** ~400 linhas testes + otimizações

### Estimativa FASE 6 Total
- Preditivo: ~300 linhas
- Testes: ~400 linhas
- Polish/performance: ~200 linhas
- **Total: ~900 linhas | 1-2 sessões**

---

## RESUMO CONSOLIDADO

| Fase | Módulos | Linhas estimadas | Sessões | Dependências |
|------|---------|-----------------|---------|--------------|
| **FASE 1** | Ampliar dados municipais | ~800 | 1-2 | Nenhuma |
| **FASE 2** | mod-qualidade + eficiência expandida | ~1.250 | 2-3 | FASE 1 |
| **FASE 3** | mod-idhh + mod-benchmark + mod-desertos | ~2.200 | 3-4 | FASE 1+2 |
| **FASE 4** | mod-acesso + mod-epidemiologia + risco expandido | ~2.100 | 3-4 | FASE 1+2 |
| **FASE 5** | Financeiro expandido + mod-cockpit | ~1.800 | 2-3 | FASE 1-4 |
| **FASE 6** | Preditivo + testes + polish | ~900 | 1-2 | FASE 1-5 |
| **TOTAL** | **6 novos módulos + 4 expandidos** | **~9.050** | **12-18** | — |

### Resultado Final Projetado (V49)
- **21+ módulos** (15 atuais + 6 novos)
- **~160 campos** por município (115 atuais + ~45 novos)
- **index.html:** ~25-30k linhas (~8-12 MB estimado)
- **Pipeline:** 14+ scripts Python

---

## GRAFO DE DEPENDÊNCIAS

```
FASE 1 (dados base)
  ├── FASE 2 (qualidade + eficiência)
  │     ├── FASE 3 (IDH-H + benchmark + desertos)
  │     └── FASE 4 (acesso + epidemiologia + risco)
  │           └── FASE 5 (financeiro + cockpit)
  │                 └── FASE 6 (preditivo + polish)
  └── FASE 3 (desertos usa dados FASE 1 diretamente)
```

**FASE 3 e FASE 4 podem ser executadas em paralelo** (ambas dependem de FASE 1+2, mas não entre si).

---

## FONTES DE DADOS — MAPA DE VIABILIDADE

| Fonte | Método | Scripts existentes? | Complexidade |
|-------|--------|-------------------|--------------|
| CNES (leitos, profissionais) | PySUS + FTP DATASUS | ✅ `00_coletor_cnes.py` | Baixa |
| TabNet (CAPS, ESF) | POST HTTP | ✅ `01_coletor_tabnet.py` | Baixa |
| SIH/DATASUS (AIH, internações) | PySUS `download()` ou TabNet | ❌ Novo | Média |
| SIA/DATASUS (ambulatorial) | PySUS ou TabNet | ❌ Novo | Média |
| SIM/DATASUS (mortalidade) | TabNet POST | ❌ Novo | Baixa |
| SINASC (nascidos vivos) | TabNet POST | ❌ Novo | Baixa |
| SINAN (doenças notificáveis) | TabNet POST | ❌ Novo | Média |
| SIOPS/FNS (orçamento) | Download CSV/API | ❌ Novo | Alta |
| FNS (transferências) | Scraping/Download | ❌ Novo | Alta |
| SIGTAP (procedimentos) | Download tabela | ❌ Novo | Baixa |

**Conclusão:** 70% dos dados são coletáveis via TabNet POST (padrão já dominado). Os 30% restantes (SIOPS, FNS) exigem métodos alternativos e podem ser priorizados para fases posteriores.

---

## PRÓXIMOS PASSOS

Após aprovação deste plano:
1. **Iniciar FASE 1** — criar scripts de coleta SIH/SIA/SIM
2. Calcular campos derivados (déficit P.1631, criticidade)
3. Gerar banco CSV v41
4. Re-encode MUNIS_FULL_B64
5. Atualizar módulos existentes com novos dados
6. Commit: `feat(camada1): ampliar MUNIS para ~130 campos`
