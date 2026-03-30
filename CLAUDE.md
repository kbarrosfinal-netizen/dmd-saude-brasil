# DMD Saude Brasil — CLAUDE.md

## Projeto

Dashboard single-file HTML de inteligencia em saude publica brasileira. Produto da EMET Gestao Brasil Ltda (Karina Barros, CEO).
Cobertura: 27 UFs, 5.569 municipios, 115 colunas no banco canonico.
Versao atual: **V43** (nomenclatura interna). Hospedado no GitHub Pages + Netlify.
Objetivo comercial: plataforma B2G para secretarias de saude, TCEs e MPs — modelo Inexigibilidade Art. 74, III, Lei 14.133/2021.

## Idioma

Todo codigo, comentarios, commits e comunicacao devem ser em **portugues brasileiro**.
Nomes de variaveis e funcoes internas podem usar ingles quando sao termos tecnicos padrao (ex: `initMapa`, `switchMod`).

## Arquitetura

### Dashboard (`index.html`)
- Arquivo unico (~17.5k linhas, 4.8 MB) com HTML + CSS + JS inline
- **23 modulos** renderizados como `<div class="shell-module">`, alternados via `switchMod()`:
  - `mod-nacional` — Brasil visao geral
  - `mod-am` — Amazonas detalhado (modulo modelo)
  - `mod-oss` — OSS / Contratos AM
  - `mod-scorev2` — Score V2 ranking nacional
  - `mod-infra` — Infraestrutura CNES
  - `mod-dc` — Doencas Cronicas
  - `mod-sih` — Internacoes SIH/AIH
  - `mod-icsap` — Internacoes Sensiveis a APS
  - `mod-sv3` — Score V3 / Matriz de Risco Fiscal 5x5
  - `mod-mapa` — Mapa coropletico (Leaflet)
  - `mod-leitos` — Deficit de Leitos (Portaria 1.631/2015)
  - `mod-series` — Series Temporais CNES 2020-25
  - `mod-projecao` — Projecao 2027-2030 (regressao linear SIH)
  - `mod-eficiencia` — Indice de Eficiencia Estadual
  - `mod-saudemental` — Saude Mental / RAPS
  - `mod-qualidade` — Qualidade Assistencial (mort hosp, TMP, reinternacao)
  - `mod-idhh` — IDH Hospitalar (indicador proprietario EMET, 5 dimensoes)
  - `mod-benchmark` — Benchmarking comparativo 27 UFs
  - `mod-desertos` — Desertos de Saude (UTI, obstétrico, APS)
  - `mod-acesso` — Acesso e Regulacao (autossuficiencia, fluxo inter-UF)
  - `mod-epidemiologia` — Epidemiologia (natalidade, mortalidade, SINASC)
  - `mod-financeiro` — Financeiro SIH 2025 (receita, custo/AIH, glosa)
  - `mod-cockpit` — Cockpit Executivo (4 quadrantes, 24+ KPIs com semaforo)
- Dados de municipios embarcados como base64 raw-deflate (`MUNIS_FULL_B64`)
- Cada modulo tem funcao `init*()` chamada sob demanda no primeiro acesso

### AGENTE DMD
- Motor IA inline — AGENTE DMD V31 (script `agente-dmd-v31-js`)
- API Anthropic (Claude Sonnet 4) com streaming
- Funcoes: analise em linguagem natural, ranking criticos, auditoria fiscal, upload de arquivos
- Fallback `iaLocalAnswer()` para operacao em `file://` (offline)
- Header obrigatorio: `anthropic-dangerous-direct-browser-access`

### Dependencias CDN
- **Chart.js** — graficos (bar, scatter, doughnut, line, radar, bubble)
- **Leaflet 1.9.4** — mapa coropletico interativo
- **SheetJS** — importacao Excel
- **html2pdf.js** — exportacao PDF executivo com KPIs e semaforos
- **Google Fonts** — Barlow, Space Grotesk, DM Serif Display, DM Mono, DM Sans

### Pipeline (`pipeline/`)
- Python 3.x com pandas, pysus, beautifulsoup4
- Scripts em `pipeline/scripts/`:
  - `00_coletor_cnes.py` — CNES leitos, equipes, profissionais
  - `00_ibge_municipios_base.py` — base IBGE municipios
  - `01_coletor_tabnet.py` — CAPS, ESF, ICSAP via TabNet POST
  - `01_tabnet_caps_coletor.py` — CAPS especifico
  - `02_normalizador.py` / `02_normalizador_validador.py` — validacao e normalizacao
  - `03_gerar_dashboard.py` — gera MUNIS_FULL_B64 para o HTML
  - `03_relatorio_cobertura.py` — auditoria de cobertura
  - `04_orquestrador.py` / `04_orquestrador_pipeline.py` — orquestracao
  - `05_coletor_datasus_nacional.py` — SIH 2025 + SIM/SINASC 2024 nacionais
  - `08_coletor_sih_municipal.py` — SIH 2025 por municipio (3.135 reais)
  - `09_coletor_mortalidade_municipal.py` — TMI municipal real 5.570 municipios
- Patches V3 por UF em `pipeline/patches/{UF}_v3_{MMAAAA}.json`
  - Existentes: AC, AM, AP, PA, RO, RR, TO (regiao Norte — 7 UFs)
  - **FALTAM patches para 20 UFs**: AL, BA, CE, DF, ES, GO, MA, MG, MS, MT, PB, PE, PI, PR, RJ, RN, RS, SC, SE, SP
- Auditorias em `pipeline/audits/`
- Dependencias em `pipeline/requirements.txt`

### Dados
- `dmd_banco_v40_integrado.csv` — banco canonico 5.569 x 115 colunas
- `dmd_banco_v40_compacto.csv` — versao compacta 5.569 x 110
- `dmd_base_canonica_integrada_v2_2.xlsx` — base canonica Excel (121 variaveis)

## Banco de Dados — Campos Existentes (115 colunas)

| Alias | Campo completo | Fonte |
|-------|---------------|-------|
| `m` | municipio | IBGE |
| `pop` | populacao | IBGE Censo 2022 |
| `l` | leitos_sus | CNES |
| `u` | uti_sus | CNES |
| `e` | esf_equipes | e-Gestor AB |
| `g` | gasto_sus | SIOPS |
| `mi` | mortalidade_infantil | SIM/SINASC |
| `mm` | mortalidade_materna | SIM |
| `dl` | deficit_leitos | Calculado (P.1631) |
| `du` | deficit_uti | Calculado |
| `mac` | macrorregiao | IBGE |
| `crit` | criticidade | Score composto |
| `idh` | idh_municipal | IBGE Censo 2022 |
| `leitos_sus_1k`, `medicos_1k`, `enfermeiros_1k` | indicadores per capita | CNES |
| `score_v3`, `rank_v3`, `risco_v3` | Score V3 e ranking | Calculado |
| `cob_sarampo`, `cob_gripe`, `cob_covid` | cobertura vacinal | RNDS/MS |
| `mort_cv_100k`, `mort_dm_100k`, `mort_has_100k` | mortalidade cronicas | DATASUS SIM |
| `ibge_7` | cod_ibge 7 digitos | IBGE |
| `versao_banco` | versao do banco | Interno |

## Modelo Amazonas — 76 Planilhas (Referencia Nacional)

O banco AM (`Banco_DMD_Saude_05-03-26.xlsx`) tem **76 planilhas** mapeadas em **12 camadas** que devem ser replicadas nacionalmente:

| Camada | Planilhas AM | Modulo Dashboard | Status |
|--------|-------------|-----------------|--------|
| 1 — Diagnostico Municipal | DIAGNOSTICO_POR_MUNICIPIO, MUNICIPAL_62 | mod-nacional, mod-am | ✅ Parcial (115 campos) |
| 2 — Qualidade Assistencial | QUALIDADE_ASSISTENCIAL, QUALIDADE_PNASS | mod-qualidade | ✅ Modulo criado |
| 3 — Eficiencia Operacional | EFICIENCIA_OPERACIONAL, PARETO_* | mod-eficiencia | ✅ Modulo criado |
| 4 — IDH Hospitalar | IDH_HOSPITALAR_AM | mod-idhh | ✅ Modulo criado |
| 5 — Desertos de Saude | MAPA_DESERTOS_SAUDE | mod-desertos | ✅ Modulo criado |
| 6 — Acesso e Regulacao | ACESSO_REGULACAO, SISREG, MATRIZ_OD | mod-acesso | ✅ Modulo criado |
| 7 — Epidemiologia | EPIDEMIOLOGIA_MUNICIPAL | mod-epidemiologia | ✅ Modulo criado |
| 8 — Financeiro/Contratos | CONTRATOS_SGC, FINANCEIRO_UG | mod-financeiro, mod-oss | ✅ Parcial |
| 9 — Benchmarking | BENCHMARKING_NACIONAL, SERIES_HISTORICAS | mod-benchmark, mod-series | ✅ Modulo criado |
| 10 — Gestao de Risco | MATRIZ_RISCO, ALERTAS_GESTAO | mod-sv3 | ✅ Modulo criado |
| 11 — Cockpit Executivo | COCKPIT_EXECUTIVO | mod-cockpit | ✅ Modulo criado |
| 12 — Preditivo | MODULO_PREDITIVO_IA | mod-projecao | ✅ Modulo criado |

**GAP ATUAL**: Todos os 23 modulos existem no dashboard, mas os dados reais nas camadas 2-12 ainda sao majoritariamente calculos sobre os 115 campos existentes. Para chegar ao nivel do AM, faltam campos adicionais no banco para todos os 27 estados.

## Campos que FALTAM no banco nacional (gap AM → Nacional)

| Campo | Fonte | Prioridade |
|-------|-------|-----------|
| `medicos_abs` | CNES profissionais | P1 |
| `enfermeiros_abs` | CNES profissionais | P1 |
| `producao_aih_ano` | SIH/DATASUS | P1 |
| `producao_amb_ano` | SIA/DATASUS | P1 |
| `receita_sus_ano` | SIH+SIA | P1 |
| `receita_per_capita` | Calculado | P1 |
| `glosa_pct` / `glosa_valor` | SIH | P2 |
| `leitos_necessarios_p1631` | Portaria 1.631 | P1 |
| `investimento_necessario` | Calculado | P2 |
| `tmi_real` (persistido) | SIM/SINASC 2024 | P1 — coletado, falta persistir |
| `tmm_real` | SIM/SINASC | P1 |
| `leitos_obst` | CNES tipo 4 | P2 |
| `nascimentos_nv` | SINASC | P1 |
| `prematuros_pct` | SINASC | P2 |
| `cesareas_pct` | SIH | P2 |
| `mort_hospitalar_pct` | SIH/RD | P2 |
| `tmp_medio` | SIH/RD | P2 |
| `ocupacao_leitos_pct` | SIH+CNES | P2 |

## Convencoes de Codigo

### HTML/CSS/JS
- Tudo inline no `index.html` — nao separar em arquivos
- CSS usa variaveis customizadas (`--bg2`, `--teal`, `--dim`, `--lit`, `--fm`, etc.)
- Design system escuro (background `#04080F`, accent `#00C6BD`)
- Paleta INPI: Navy `#0D1B2A` + Teal `#00C6BD`
- Modulos seguem padrao: `<div id="mod-{nome}" class="shell-module">` com `mod-header` + `mod-body`
- Funcoes de inicializacao: `init{Nome}()`, chamadas em `switchMod()`
- Export CSV disponivel em cada modulo via `document.createElement('a')`
- Export PDF via html2pdf.js — botao "Relatorio PDF" em modulos analiticos
- Graficos Chart.js armazenados em `window.chart*` e destruidos antes de recriar

### Compressao de dados municipais
- **SEMPRE** usar raw deflate (`wbits=-15`) — NUNCA gzip ou deflate padrao
- Compressao Python: `zlib.compress(data, wbits=-15)` → base64
- Descompressao browser: `DecompressionStream('deflate-raw')` → parse JSON

### Pipeline Python
- Scripts numerados sequencialmente
- Patches JSON por UF e competencia — nunca sobrescrever dado real com patch
- Validacao obrigatoria antes de integracao
- Processar UFs individualmente — nunca as 27 de uma vez

## Anti-Padroes (NUNCA fazer)

1. Separar `index.html` em multiplos arquivos — o produto eh single-file por design
2. Copiar dados de uma UF para outra
3. Usar estimativa quando dado real esta disponivel
4. Sobrescrever dado CNES real com novo patch
5. Processar 27 UFs de uma vez no pipeline
6. Deletar patches anteriores
7. Usar fonte de dados nao oficial
8. Mudar estrutura JSON de patches sem versionar
9. Remover ou alterar valores auditados sem justificativa explicita
10. Adicionar dependencias JS locais — usar CDN
11. Alterar a logica do AGENTE DMD sem instrucao explicita
12. Usar gzip ou deflate padrao — sempre raw deflate (wbits=-15)

## Fontes de Dados

| Fonte | Descricao | Cadencia |
|-------|-----------|----------|
| CNES/MS | Leitos, equipes, profissionais | Mensal |
| SIOPS/FNS | Orcamentos em saude, LC 141/2012 | Anual |
| IBGE | Censo 2022 — populacao, IDH, GINI | Decenal |
| DATASUS SIH/SIA | Internacoes, procedimentos, valores | Mensal |
| e-Gestor AB/MS | ESF, ACS, cobertura AB | Mensal |
| RNDS/MS | Vacinacao | Mensal |
| DATASUS SIM | Mortalidade geral e infantil | Anual |
| DATASUS SINASC | Nascidos vivos, prematuridade | Anual |
| DATASUS SINAN | Doencas notificaveis | Mensal |
| DATASUS TabNet | CAPS, SRT, leitos por tipo | Mensal |

## Versionamento

- Versao no comentario HTML do `<head>` (ex: `DMD SAUDE BRASIL V43`)
- Commits referenciam a versao (ex: `feat(modulo): DMD V43 — descricao`)
- `releases/` contem historico de versoes anteriores

## Testes e Validacao

- Pipeline: `pytest` para scripts Python
- Dashboard: validacao manual — verificar KPIs, graficos, export CSV e PDF
- Auditoria de cobertura via `03_relatorio_cobertura.py`
- Verificar que dados nao estao inflados comparando com fontes oficiais

## Deploy

- **GitHub Pages**: `index.html` na raiz — https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/
- **Netlify**: deploy automatico (trigger via `chore: trigger Netlify rebuild`)
- Arquivo `.nojekyll` presente para servir como site estatico
