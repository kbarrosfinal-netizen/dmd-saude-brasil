#!/usr/bin/env python3
"""
10_integrador_banco_v41.py — Gera banco V41 com ~128 campos por município
Integra banco V40 (115 campos) com dados SIH 2025 e SIM/SINASC 2024 municipais.

Novos campos adicionados (13):
  De cálculo:     medicos_abs, enfermeiros_abs, leitos_necessarios_p1631,
                  deficit_leitos_pct, deficit_uti_pct, receita_per_capita
  De SIH 2025:    producao_aih_ano, receita_sus_ano, custo_medio_aih,
                  obitos_hosp, letalidade_hosp_pct
  De SIM/SINASC:  nascimentos_nv, tmi_real

Cobertura SIH: 3.135 municípios com dados reais, restantes ficam 0
Cobertura TMI: 5.570 municípios com dados reais

Autor: Claude Code / EMET Gestão Brasil
Data: 2026-03-30
"""

import csv
import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'pipeline', 'data')

INPUT_CSV = os.path.join(BASE_DIR, 'dmd_banco_v40_integrado.csv')
OUTPUT_CSV = os.path.join(BASE_DIR, 'dmd_banco_v41_integrado.csv')

SIH_JSON = os.path.join(DATA_DIR, 'sih_municipal', 'sih_municipal_2025.json')
MORT_JSON = os.path.join(DATA_DIR, 'mortalidade_municipal', 'mortalidade_municipal_2024.json')


def carregar_sih():
    """Carrega SIH 2025 municipal. Chave: ibge6 (string 6 dígitos)."""
    if not os.path.exists(SIH_JSON):
        print(f'  AVISO: {SIH_JSON} não encontrado — campos SIH serão 0')
        return {}
    with open(SIH_JSON, encoding='utf-8') as f:
        d = json.load(f)
    dados = d.get('municipios', {})
    print(f'  SIH 2025: {len(dados):,} municípios carregados')
    return dados


def carregar_mortalidade():
    """Carrega mortalidade municipal 2024. Chave: ibge6 (string 6 dígitos)."""
    if not os.path.exists(MORT_JSON):
        print(f'  AVISO: {MORT_JSON} não encontrado — campos TMI serão 0')
        return {}
    with open(MORT_JSON, encoding='utf-8') as f:
        d = json.load(f)
    dados = d.get('municipios', {})
    print(f'  Mortalidade 2024: {len(dados):,} municípios carregados')
    return dados


def ibge7_to_ibge6(ibge7_str):
    """Converte ibge_7 (7 dígitos) para ibge6 (6 dígitos removendo dígito verificador)."""
    s = str(ibge7_str).strip().replace('.0', '').replace(' ', '')
    if len(s) == 7:
        return s[:6]
    if len(s) == 6:
        return s
    # tenta pegar de ibge_cod (pode ser float como 1300029.0)
    try:
        return str(int(float(s)))[:6]
    except Exception:
        return s[:6] if len(s) >= 6 else s


def safe_float(val, default=0.0):
    try:
        return float(str(val).replace(',', '.'))
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(float(str(val).replace(',', '.')))
    except (ValueError, TypeError):
        return default


def main():
    ts = datetime.now().isoformat()
    print('=' * 60)
    print('  INTEGRADOR BANCO V41 — DMD Saúde Brasil')
    print(f'  Início: {ts}')
    print('=' * 60)

    # Carregar fontes externas
    print('\n[1/4] Carregando fontes externas...')
    sih = carregar_sih()
    mort = carregar_mortalidade()

    # Carregar banco V40
    print('\n[2/4] Carregando banco V40...')
    with open(INPUT_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames_v40 = reader.fieldnames
        rows_v40 = list(reader)
    print(f'  V40: {len(rows_v40):,} municípios × {len(fieldnames_v40)} colunas')

    # Novos campos
    novos_campos = [
        'medicos_abs',
        'enfermeiros_abs',
        'leitos_necessarios_p1631',
        'deficit_leitos_pct',
        'deficit_uti_pct',
        'producao_aih_ano',
        'receita_sus_ano',
        'receita_per_capita',
        'custo_medio_aih',
        'obitos_hosp',
        'letalidade_hosp_pct',
        'nascimentos_nv',
        'tmi_real',
    ]
    fieldnames_v41 = fieldnames_v40 + novos_campos

    # Processar
    print('\n[3/4] Calculando e integrando campos...')
    rows_v41 = []
    stats = {
        'sih_matched': 0,
        'sih_zero': 0,
        'mort_matched': 0,
        'mort_zero': 0,
    }

    for row in rows_v40:
        # Obter ibge6 para join
        ibge6 = ibge7_to_ibge6(row.get('ibge_7', '') or row.get('ibge_cod', ''))

        pop = safe_float(row.get('pop', 0))
        leitos_sus = safe_float(row.get('leitos_sus', 0))
        uti_sus = safe_float(row.get('uti_sus', 0))
        medicos_1k = safe_float(row.get('medicos_1k', 0))
        enfermeiros_1k = safe_float(row.get('enfermeiros_1k', 0))

        # ── Campos calculados ───────────────────────────────────
        medicos_abs = round(medicos_1k * pop / 1000) if pop > 0 else 0
        enfermeiros_abs = round(enfermeiros_1k * pop / 1000) if pop > 0 else 0
        leitos_nec = round(pop * 2.5 / 1000, 1) if pop > 0 else 0
        deficit_l_abs = max(0, leitos_nec - leitos_sus)
        deficit_l_pct = round(deficit_l_abs / leitos_nec * 100, 1) if leitos_nec > 0 else 0
        leitos_uti_nec = round(pop * 0.1 / 1000, 2) if pop > 0 else 0
        deficit_u_abs = max(0, leitos_uti_nec - uti_sus)
        deficit_u_pct = round(deficit_u_abs / leitos_uti_nec * 100, 1) if leitos_uti_nec > 0 else 0

        # ── Campos SIH 2025 ─────────────────────────────────────
        sih_mun = sih.get(ibge6, {})
        if sih_mun:
            producao_aih_ano = sih_mun.get('aih_qtd', 0)
            receita_sus_ano = sih_mun.get('aih_valor', 0)
            receita_per_capita = round(receita_sus_ano / pop, 2) if pop > 0 else 0
            custo_medio_aih = sih_mun.get('custo_medio_aih', 0)
            obitos_hosp = sih_mun.get('obitos_hosp', 0)
            letalidade_hosp_pct = sih_mun.get('letalidade_hosp', 0)
            stats['sih_matched'] += 1
        else:
            producao_aih_ano = 0
            receita_sus_ano = 0
            receita_per_capita = 0
            custo_medio_aih = 0
            obitos_hosp = 0
            letalidade_hosp_pct = 0
            stats['sih_zero'] += 1

        # ── Campos SIM/SINASC 2024 ──────────────────────────────
        mort_mun = mort.get(ibge6, {})
        if mort_mun:
            nascimentos_nv = mort_mun.get('nv', 0)
            tmi_real = mort_mun.get('tmi', 0)
            stats['mort_matched'] += 1
        else:
            nascimentos_nv = 0
            tmi_real = 0
            stats['mort_zero'] += 1

        # Compor nova linha
        new_row = dict(row)
        new_row['medicos_abs'] = medicos_abs
        new_row['enfermeiros_abs'] = enfermeiros_abs
        new_row['leitos_necessarios_p1631'] = leitos_nec
        new_row['deficit_leitos_pct'] = deficit_l_pct
        new_row['deficit_uti_pct'] = deficit_u_pct
        new_row['producao_aih_ano'] = producao_aih_ano
        new_row['receita_sus_ano'] = receita_sus_ano
        new_row['receita_per_capita'] = receita_per_capita
        new_row['custo_medio_aih'] = custo_medio_aih
        new_row['obitos_hosp'] = obitos_hosp
        new_row['letalidade_hosp_pct'] = letalidade_hosp_pct
        new_row['nascimentos_nv'] = nascimentos_nv
        new_row['tmi_real'] = tmi_real

        rows_v41.append(new_row)

    # Salvar V41
    print('\n[4/4] Salvando banco V41...')
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_v41)
        writer.writeheader()
        writer.writerows(rows_v41)

    # Relatório
    print(f'\n{"=" * 60}')
    print('  RELATÓRIO — BANCO V41')
    print(f'{"=" * 60}')
    print(f'  Municípios:               {len(rows_v41):,}')
    print(f'  Colunas V40 → V41:        {len(fieldnames_v40)} → {len(fieldnames_v41)}')
    print(f'  Novos campos:             {len(novos_campos)}')
    print()
    print(f'  SIH 2025 com dados reais: {stats["sih_matched"]:,} ({stats["sih_matched"]/len(rows_v41)*100:.1f}%)')
    print(f'  SIH sem dados (zerado):   {stats["sih_zero"]:,}')
    print()
    print(f'  TMI real com dados:       {stats["mort_matched"]:,} ({stats["mort_matched"]/len(rows_v41)*100:.1f}%)')
    print(f'  TMI sem dados (zerado):   {stats["mort_zero"]:,}')
    print()
    print(f'  Novos campos adicionados:')
    for c in novos_campos:
        print(f'    + {c}')
    print()
    print(f'  Arquivo gerado: {OUTPUT_CSV}')
    print(f'{"=" * 60}')

    # Validação rápida
    print('\n  Validação amostra (SP capital — ibge6 355030):')
    sp_cap = next((r for r in rows_v41 if ibge7_to_ibge6(r.get('ibge_7','')) == '355030'), None)
    if sp_cap:
        campos_chave = ['m', 'pop', 'medicos_abs', 'enfermeiros_abs',
                        'leitos_necessarios_p1631', 'producao_aih_ano',
                        'receita_sus_ano', 'receita_per_capita',
                        'nascimentos_nv', 'tmi_real']
        for c in campos_chave:
            print(f'    {c:30s} = {sp_cap.get(c, "?")}')
    else:
        print('    (SP capital não encontrada no sample)')


if __name__ == '__main__':
    main()
