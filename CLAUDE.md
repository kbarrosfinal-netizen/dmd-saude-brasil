# DMD Saude Brasil — CLAUDE.md

## Projeto

Dashboard single-file HTML de inteligencia em saude publica brasileira. Produto da EMET Gestao Brasil Ltda.
Cobertura: 27 UFs, 5.569 municipios, 115+ indicadores por municipio.
Versao atual: V43. Hospedado no GitHub Pages.

## Idioma

Todo codigo, comentarios, commits e comunicacao devem ser em **portugues brasileiro**.
Nomes de variaveis e funcoes internas podem usar ingles quando sao termos tecnicos padrao (ex: `initMapa`, `switchMod`).

## Arquitetura

### Dashboard (`index.html`)
- Arquivo unico (~16k linhas) com HTML + CSS + JS inline
- **16 modulos** renderizados como `<div class="shell-module">`, alternados via `switchMod()`:
  - `mod-nacional` — Brasil visao geral
  - `mod-am` — Amazonas detalhado
  - `mod-oss` — OSS / Contratos AM
  - `mod-scorev2` — Score V2 ranking nacional
  - `mod-infra` — Infraestrutura CNES
  - `mod-dc` — Doencas Cronicas
  - `mod-sih` — Internacoes SIH/AIH
  - `mod-icsap` — Internacoes Sensiveis a APS
  - `mod-sv3` — Score V3 Vulnerabilidade
  - `mod-mapa` — Mapa coropletico (Leaflet)
  - `mod-leitos` — Deficit de Leitos
  - `mod-series` — Series Temporais CNES 2020-25
  - `mod-projecao` — Projecao 2027-2030
  - `mod-eficiencia` — Indice de Eficiencia Estadual
  - `mod-saudemental` — Saude Mental / RAPS
  - Saude Mental Nacional (secao dentro de mod-oss)
- Dados de municipios embarcados como base64 gzip (`MUNIS_FULL_B64`)
- Cada modulo tem funcao `init*()` chamada sob demanda no primeiro acesso

### Dependencias CDN
- **Chart.js** — graficos (bar, scatter, doughnut, line)
- **Leaflet 1.9.4** — mapa coropletico interativo
- **Google Fonts** — Barlow, Space Grotesk, DM Serif Display, DM Mono, DM Sans

### Pipeline (`pipeline/`)
- Python 3.x com pandas, pysus, beautifulsoup4
- Scripts numerados `00_` a `04_` em `pipeline/scripts/`
- Patches por UF em `pipeline/patches/{UF}_v3_{MMAAAA}.json`
- Auditorias em `pipeline/audits/`
- Dependencias em `pipeline/requirements.txt`

### Dados
- `dmd_banco_v40_integrado.csv` — banco canonico 5.569 x 115
- `dmd_banco_v40_compacto.csv` — versao compacta
- `dmd_base_canonica_integrada_v2_2.xlsx` — base canonica Excel

## Convencoes de Codigo

### HTML/CSS/JS
- Tudo inline no `index.html` — nao separar em arquivos
- CSS usa variaveis customizadas (`--bg2`, `--teal`, `--dim`, `--lit`, `--fm`, etc.)
- Design system escuro (background `#04080F`, accent `#00C6BD`)
- Modulos seguem padrao: `<div id="mod-{nome}" class="shell-module">` com `mod-header` + `mod-body`
- Funcoes de inicializacao: `init{Nome}()`, chamadas em `switchMod()`
- Export CSV disponivel em cada modulo via `document.createElement('a')`
- Graficos Chart.js armazenados em `window.chart*` e destruidos antes de recriar

### Pipeline Python
- Scripts numerados sequencialmente
- Patches JSON por UF e competencia — nunca sobrescrever dado real com patch
- Validacao obrigatoria antes de integracao

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

## Fontes de Dados

| Fonte | Descricao | Cadencia |
|-------|-----------|----------|
| CNES/MS | Cadastro Nacional de Estabelecimentos de Saude | Mensal |
| SIOPS/FNS | Orcamentos Publicos em Saude | Anual |
| IBGE | Censo 2022 — populacao, IDH, GINI | Decenal |
| DATASUS SIH/SIA | Internacoes, procedimentos | Mensal |
| e-Gestor AB/MS | ESF, ACS, cobertura atencao basica | Mensal |
| RNDS/MS | Vacinacao | Mensal |
| DATASUS SIM | Mortalidade, doencas cronicas | Anual |
| DATASUS TabNet | CAPS, SRT, leitos | Mensal |

## Versionamento

- Versao do banco no comentario HTML do `<head>` (ex: `DMD SAUDE BRASIL V43`)
- Commits devem referenciar a versao (ex: `feat: DMD V43 — descricao`)
- `releases/` contem historico de versoes anteriores

## Testes e Validacao

- Pipeline: `pytest` para scripts Python
- Dashboard: validacao manual — verificar KPIs, graficos, export CSV
- Auditoria de cobertura via `03_relatorio_cobertura.py`
- Verificar que dados nao estao inflados comparando com fontes oficiais

## Deploy

GitHub Pages servindo `index.html` da raiz.
URL: https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/
Arquivo `.nojekyll` presente para servir como site estatico.
