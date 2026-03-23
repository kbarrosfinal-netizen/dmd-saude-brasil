# Pipeline Nacional DMD Saúde Brasil — v3.0
**EMET Gestão Brasil Ltda | Banco DMD Saúde Brasil V40+**

## Visão Geral

Pipeline de alimentação automática do Banco DMD com dados reais de CNES/DATASUS para todos os **27 estados** e **5.570 municípios** do Brasil.

**Objetivo:** 100% de cobertura com dados CNES reais até Julho/2026.

---

## Estrutura

```
pipeline/
├── scripts/
│   ├── 00_ibge_municipios_base.py      # Coleta base IBGE Censo 2022
│   ├── 01_tabnet_caps_coletor.py       # Download CAPS/SRT via TabNet
│   ├── 02_normalizador_validador.py    # Normalização + validação 7 regras
│   ├── 03_relatorio_cobertura.py       # Relatório mensal de cobertura
│   └── 04_orquestrador_pipeline.py     # Orquestrador principal (6 passos)
├── patches/
│   └── {UF}_v3_{MMAAAA}.json          # Patches por UF e competência
├── audits/
│   └── cobertura_nacional_{MMAAAA}.csv # Relatório de cobertura nacional
└── logs/
    └── {FASE}_resumo.json             # Resumo de execução por fase
```

---

## Cronograma de Cobertura

| Fase | UFs | Mês Alvo | Municípios |
|------|-----|----------|------------|
| FASE_1_NORTE | AC, AM, AP, PA, RO, RR, TO | Abril/2026 | 450 |
| FASE_2_NORDESTE | AL, BA, CE, MA, PB, PE, PI, RN, SE | Maio/2026 | 1.794 |
| FASE_3_SUDESTE_SUL | ES, MG, RJ, SP, PR, RS, SC | Junho/2026 | 2.859 |
| FASE_4_CO | DF, GO, MS, MT | Julho/2026 | **5.570 (100%)** |

---

## Cobertura Atual (Baseline 03/2026)

| Indicador | Valor |
|-----------|-------|
| Total de municípios | 5.570 |
| Dados CNES reais | 645 (11,6%) |
| Estimativas | 3.656 (65,6%) |
| Pendentes | 1.269 (22,8%) |
| **Meta Jul/2026** | **5.570 (100%)** |

---

## Como Executar

### Manualmente (local)

```bash
# 1. Coletar base IBGE
python3 pipeline/scripts/00_ibge_municipios_base.py

# 2. Executar fase específica
python3 pipeline/scripts/04_orquestrador_pipeline.py --fase FASE_1_NORTE

# 3. Gerar relatório de cobertura
python3 pipeline/scripts/03_relatorio_cobertura.py
```

### Via GitHub Actions

Acesse [Actions](../../actions/workflows/pipeline-nacional-dmd.yml) → `Run workflow` → selecione a fase desejada.

O pipeline também executa **automaticamente todo dia 18 de cada mês** às 06:00 BRT.

---

## Anti-Padrões (NUNCA fazer)

1. ❌ Copiar dados de uma UF para outra
2. ❌ Usar estimativa quando dado real está disponível
3. ❌ **Sobrescrever dado CNES real com novo patch**
4. ❌ Processar 27 UFs de uma vez
5. ❌ Ignorar município não encontrado (registrar como ORPHAN)
6. ❌ Usar fonte não oficial como substituta
7. ❌ Mudar estrutura JSON sem versionar
8. ❌ Deletar patches anteriores

---

## Fontes de Dados

| Camada | Fonte | Frequência | URL |
|--------|-------|------------|-----|
| CAPS/SRT | CNES TabNet | Mensal (dia 16) | tabnet.datasus.gov.br |
| Leitos | CNES TabNet | Mensal | tabnet.datasus.gov.br |
| ESF/APS | e-Gestor AB | Mensal | egestorab.saude.gov.br |
| Financeiro | SIOPS | Trimestral | siops.datasus.gov.br |
| População | IBGE SIDRA | Anual | servicodados.ibge.gov.br |

---

**EMET Gestão Brasil | DMD Saúde Brasil V40+ | Confidencial — LGPD Art. 46**
