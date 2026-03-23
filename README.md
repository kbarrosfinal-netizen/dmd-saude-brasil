# EMET DMD Gestão Brasil — Dashboard Nacional

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-brightgreen)](https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/)
[![Municípios](https://img.shields.io/badge/Munic%C3%ADpios-5.569-blue)](https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/)
[![UFs](https://img.shields.io/badge/UFs-27-orange)](https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/)
[![Banco](https://img.shields.io/badge/Banco-V40%2Bv37%2Bv3-purple)](https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/)

## 🌐 Dashboard ao vivo
**https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/**

## 📊 Versão atual: v9.0 — Banco DMD V40+v37+v3

| Indicador | Valor |
|---|---|
| 🗺️ Municípios | **5.569** (27 UFs) |
| 👥 População | **207,2 M** |
| 🏥 CAPS ativos | **3.731** (CNES 02/2026) |
| 🏠 SRT | **342** |
| 🛏️ Leitos SUS | **424.198** |
| 🩺 Psiquiatras | **12.695** |
| 💰 Alertas fiscais | **324** municípios |
| 🚨 Risco Crítico (v3) | **1.357** municípios |
| 📊 Indicadores por município | **115** colunas |

## 🗂️ Arquivos principais

| Arquivo | Descrição |
|---|---|
| `index.html` | Dashboard V9.0 (GitHub Pages) — 15 MB |
| `dmd_banco_v40_integrado.csv` | Banco completo V40+v37+v3 — 5.569×115 |
| `dmd_banco_v40_compacto.csv` | Banco compacto — 5.569×110 |

## 🔄 Fontes de dados
- **CNES/MS** — CNES 02/2026 (CAPS, SRT, leitos, psiquiatras)
- **IBGE** — Censo 2022 (população, IDH, GINI)
- **SIOPS/FNS** — Gastos per capita em saúde (SIOPS)
- **DATASUS** — SIH/SIA (internações, procedimentos)
- **e-Gestor AB/MS** — ESF, ACS, cobertura AB
- **RNDS/MS** — Vacinação (sarampo, gripe, COVID)

## 🤖 AGENTE DMD
O dashboard inclui o **AGENTE DMD v26** integrado:
- Análise em linguagem natural
- Resumos nacionais e por UF
- Ranking de municípios críticos
- Auditoria fiscal (LC 141/2012)
- Upload e cruzamento de arquivos
- Exportação de relatórios

## 📁 Estrutura do repositório
```
dmd-saude-brasil/
├── index.html                    # Dashboard v9.0 (GitHub Pages)
├── dmd_banco_v40_integrado.csv   # Banco canônico completo
├── dmd_banco_v40_compacto.csv    # Banco compacto
├── releases/
│   └── v9/                       # Release v9.0
├── pipeline/
│   └── scripts/                  # Scripts de coleta e processamento
└── README.md
```

## ⚖️ Disclaimer
> Dados de fontes **100% públicas e auditáveis** (DATASUS, IBGE, SIOPS, CNES/MS, FNS).
> Uso para fins de gestão pública e análise de políticas de saúde.

---
*EMET DMD Gestão Brasil · Dashboard Nacional v9.0 · Última atualização: 23/03/2026*
