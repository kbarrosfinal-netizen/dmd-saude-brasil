# DMD Saúde Brasil — Painel Integrado Nacional

Dashboard de inteligência de dados para gestão da saúde pública brasileira.
Cobertura: 5.569 municípios, 27 unidades federativas, 115 indicadores por município.

**Dashboard ao vivo:** https://kbarrosfinal-netizen.github.io/dmd-saude-brasil/

## Sobre

O DMD Saúde Brasil é um produto da EMET Gestão Brasil Ltda que consolida dados de 6 fontes federais públicas (CNES, SIOPS, IBGE, DATASUS, e-Gestor AB, RNDS) em um painel analítico interativo para gestores públicos, secretarias de saúde, tribunais de contas e órgãos de controle.

O painel permite:
- Diagnóstico municipal de saúde (leitos, CAPS, ESF, psiquiatras, UTI)
- Alertas fiscais e risco ao erário (glosas SIH, execução orçamentária, LC 141/2012)
- Comparativo entre estados e municípios
- Score de criticidade por município (1.357 em risco crítico)
- Agente de IA analítico integrado (chat em linguagem natural)

## Versão atual

Banco DMD V41 — CNES 02/2026 — Março/2026

| Indicador | Valor |
|-----------|-------|
| Municípios | 5.569 |
| UFs | 27 |
| Indicadores/município | 115 |
| CAPS ativos | 3.731 |
| Leitos SUS | 424.198 |
| Alertas fiscais | 324 municípios |
| Risco crítico | 1.357 municípios |

## Fontes de dados

Todas as fontes são públicas, gratuitas e auditáveis:

| Fonte | Descrição | Cadência |
|-------|-----------|----------|
| CNES/MS | Cadastro Nacional de Estabelecimentos de Saúde | Mensal |
| SIOPS/FNS | Orçamentos Públicos em Saúde | Anual |
| IBGE | Censo 2022 — população, IDH, GINI | Decenal |
| DATASUS | SIH/SIA — internações, procedimentos | Mensal |
| e-Gestor AB/MS | ESF, ACS, cobertura atenção básica | Mensal |
| RNDS/MS | Vacinação | Mensal |

## Estrutura do repositório

```
dmd-saude-brasil/
├── index.html                    # Dashboard (GitHub Pages)
├── dmd_banco_v40_integrado.csv   # Banco canônico — 5.569 × 115
├── pipeline/                     # Scripts de coleta e processamento
├── releases/                     # Histórico de versões
└── README.md
```

## Licença

Todos os direitos reservados. EMET Gestão Brasil Ltda.
Dados de fontes públicas federais — uso permitido para gestão pública e análise de políticas de saúde.

## Contato

EMET Gestão Brasil Ltda — Manaus, AM  
diretoria@dmdsaude.com.br
