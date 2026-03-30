#!/usr/bin/env python3
"""
12_gerador_patches_v3.py — Gera patches V3 para as 20 UFs sem patch

Para cada UF faltante, lê o banco V41 e produz:
  pipeline/patches/{UF}_v3_032026.json

Campos por município no patch:
  m, ibge, pop, caps, caps_tipo, srt, psiq_cad, psiq_hab,
  leitos_sus, uti, esf_pct, lq, def_psiq, alerta_fiscal,
  vacuo_hab, fonte_sm

Regras de derivação para campos sem dado direto:
  uti      → uti_sus se > 0; senão round(u × pop / 1000)
  esf_pct  → esf_pct se > 0; senão campo 'e' (cobertura AB%)
  fonte_sm → 'CNES_Mar2026' se dados reais; 'ESTIMATIVA_V41_Mar2026' se calculado

UFs faltantes: AL BA CE DF ES GO MA MG MS MT PB PE PI PR RJ RN RS SC SE SP

Autor: Claude Code / EMET Gestão Brasil
Data: 2026-03-30
"""

import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_V41  = os.path.join(BASE_DIR, 'dmd_banco_v41_integrado.csv')
PATCH_DIR = os.path.join(BASE_DIR, 'pipeline', 'patches')

UFS_FALTANTES = [
    'AL','BA','CE','DF','ES','GO','MA','MG','MS','MT',
    'PB','PE','PI','PR','RJ','RN','RS','SC','SE','SP'
]

# UFs com dados CNES reais já no banco (patches existentes — não sobrescrever)
UFS_COM_PATCH = {'AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'}

UTI_ESF_DIR = os.path.join(BASE_DIR, 'pipeline', 'data', 'uti_esf_municipal')


def safe_float(val, default=0.0):
    try:
        return float(str(val).replace(',', '.').strip() or default)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(float(str(val).replace(',', '.').strip() or default))
    except (ValueError, TypeError):
        return default


def safe_bool(val):
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ('true', '1', 'yes', 'sim', 't')


def carregar_uti_esf_real(uf):
    """Carrega dados reais coletados pelo script 13 (se disponíveis)."""
    uf_file = os.path.join(UTI_ESF_DIR, f'uti_esf_{uf}_2026.json')
    if not os.path.exists(uf_file):
        return {}
    with open(uf_file, encoding='utf-8') as f:
        d = json.load(f)
    return d.get('municipios', {})


def derivar_uti(row, uti_esf_real=None, ibge6=None):
    """UTI absoluto: prioridade: dados reais coletados > uti_sus > u×pop/1k."""
    # 1. Dados reais do script 13
    if uti_esf_real and ibge6 and ibge6 in uti_esf_real:
        val = safe_float(uti_esf_real[ibge6].get('uti_sus', 0))
        if val > 0:
            return int(val), True
    # 2. Coluna uti_sus do banco
    uti_sus = safe_float(row.get('uti_sus', 0))
    if uti_sus > 0:
        return int(uti_sus), True
    # 3. Calcula de u (leitos UTI por 1000 hab)
    u = safe_float(row.get('u', 0))
    pop = safe_float(row.get('pop', 0))
    if u > 0 and pop > 0:
        return round(u * pop / 1000), False
    return 0, False


def derivar_esf_pct(row, uti_esf_real=None, ibge6=None):
    """ESF%: prioridade: dados reais coletados > esf_pct > campo 'e'."""
    # 1. Dados reais do script 13
    if uti_esf_real and ibge6 and ibge6 in uti_esf_real:
        val = safe_float(uti_esf_real[ibge6].get('esf_pct', 0))
        if val > 0:
            return val, True
    # 2. esf_pct do banco
    esf_pct = safe_float(row.get('esf_pct', 0))
    if esf_pct > 0:
        return esf_pct, True
    # 3. Campo 'e' (cobertura AB estimada)
    e = safe_float(row.get('e', 0))
    return e, False


def gerar_patch_uf(uf, rows_uf, uti_esf_real=None):
    """Gera estrutura de patch para uma UF."""
    ts = datetime.now().isoformat()
    municipios = []
    n_reais = 0
    n_estimados = 0

    for row in rows_uf:
        ibge7 = str(row.get('ibge_7', row.get('ibge_cod', ''))).replace('.0', '').strip()
        ibge6_key = ibge7[:6] if len(ibge7) >= 7 else ibge7
        uti_val, uti_real = derivar_uti(row, uti_esf_real, ibge6_key)
        esf_val, esf_real = derivar_esf_pct(row, uti_esf_real, ibge6_key)

        # Determinar fonte
        fonte_base = str(row.get('versao_banco', '')).strip()
        if uti_real and esf_real:
            fonte_sm = 'CNES_Mar2026'
            n_reais += 1
        else:
            partes = []
            if not uti_real:
                partes.append('uti=calc')
            if not esf_real:
                partes.append('esf=estim')
            fonte_sm = f'ESTIMATIVA_V41_Mar2026 ({", ".join(partes)})'
            n_estimados += 1

        # ibge: usar ibge_7 (7 dígitos) como string limpa
        ibge_raw = ibge7

        # caps_tipo: campo pode não existir para todas as UFs
        caps_tipo = str(row.get('caps_tipo', '')).strip()
        if caps_tipo in ('nan', 'None', 'none'):
            caps_tipo = ''

        mun = {
            'm':           str(row.get('m', '')).strip(),
            'ibge':        ibge_raw,
            'pop':         safe_int(row.get('pop', 0)),
            'caps':        safe_int(row.get('caps', 0)),
            'caps_tipo':   caps_tipo,
            'srt':         safe_int(row.get('srt', 0)),
            'psiq_cad':    safe_int(row.get('psiq_cad', 0)),
            'psiq_hab':    safe_int(row.get('psiq_hab', 0)),
            'leitos_sus':  safe_int(row.get('leitos_sus', 0)),
            'uti':         uti_val,
            'esf_pct':     round(esf_val, 1),
            'lq':          safe_float(row.get('lq', row.get('lq_1k', 0))),
            'def_psiq':    safe_int(row.get('def_psiq', 0)),
            'alerta_fiscal': safe_bool(row.get('alerta_fiscal', False)),
            'vacuo_hab':   safe_bool(row.get('vacuo_hab', False)),
            'fonte_sm':    fonte_sm,
        }
        municipios.append(mun)

    patch = {
        'versao':             '3.0',
        'competencia':        '03/2026',
        'uf':                 uf,
        'gerado_em':          ts,
        'gerado_por':         '12_gerador_patches_v3.py',
        'banco_base':         'dmd_banco_v41_integrado.csv',
        'total_municipios':   len(municipios),
        'total_reais':        n_reais,
        'total_estimados':    n_estimados,
        'total_substituiveis': n_estimados,
        'total_orfaos':       0,
        'municipios':         municipios,
    }
    return patch


def main():
    ts = datetime.now().isoformat()
    # Filtrar UFs a processar
    ufs_arg = [u.upper() for u in sys.argv[1:]] if len(sys.argv) > 1 else UFS_FALTANTES
    ufs_arg = [u for u in ufs_arg if u not in UFS_COM_PATCH]

    print('=' * 60)
    print('  GERADOR DE PATCHES V3 — 20 UFs')
    print(f'  UFs a processar: {len(ufs_arg)}')
    print(f'  Início: {ts}')
    print('=' * 60)

    # Carregar banco V41
    print(f'\nCarregando {CSV_V41}...')
    with open(CSV_V41, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Agrupar por UF
    por_uf = defaultdict(list)
    for row in rows:
        por_uf[row['uf']].append(row)
    print(f'  Total: {len(rows):,} municípios em {len(por_uf)} UFs\n')

    # Gerar patches
    resumo = []
    for uf in ufs_arg:
        rows_uf = por_uf.get(uf, [])
        if not rows_uf:
            print(f'  {uf}: IGNORADO (sem municípios no banco)')
            continue

        uti_esf_real = carregar_uti_esf_real(uf)
        if uti_esf_real:
            print(f'    → dados reais UTI/ESF disponíveis: {len(uti_esf_real)} municípios')
        patch = gerar_patch_uf(uf, rows_uf, uti_esf_real)

        # Verificar se patch já existe (não sobrescrever patches reais)
        patch_file = os.path.join(PATCH_DIR, f'{uf}_v3_032026.json')
        if os.path.exists(patch_file):
            with open(patch_file, encoding='utf-8') as f:
                existing = json.load(f)
            if existing.get('total_reais', 0) > patch.get('total_reais', 0):
                print(f'  {uf}: IGNORADO (patch existente tem mais dados reais)')
                continue

        with open(patch_file, 'w', encoding='utf-8') as f:
            json.dump(patch, f, ensure_ascii=False, indent=4)

        n_reais = patch['total_reais']
        n_est   = patch['total_estimados']
        print(f'  {uf}: {len(rows_uf):>4} muns | reais={n_reais:>4} | estimados={n_est:>4} → {patch_file.split("/")[-1]}')
        resumo.append((uf, len(rows_uf), n_reais, n_est))

    # Relatório
    print(f'\n{"=" * 60}')
    print('  RELATÓRIO')
    print(f'{"=" * 60}')
    total_mun = sum(r[1] for r in resumo)
    total_reais = sum(r[2] for r in resumo)
    total_est = sum(r[3] for r in resumo)
    print(f'  Patches gerados:      {len(resumo)}/20')
    print(f'  Total municípios:     {total_mun:,}')
    print(f'  Dados reais:          {total_reais:,} ({total_reais/total_mun*100:.1f}%)')
    print(f'  Estimativas:          {total_est:,} ({total_est/total_mun*100:.1f}%)')
    print()
    print('  UFs com maior cobertura real:')
    for uf, n, r, e in sorted(resumo, key=lambda x: -x[2]):
        pct = r/n*100
        bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
        print(f'    {uf}: {bar} {pct:.0f}%  ({r}/{n})')
    print(f'{"=" * 60}')
    print()
    print('  Próximo passo: coletar dados CNES reais para UFs com')
    print('  alta estimativa → substituir patches por dados reais.')


if __name__ == '__main__':
    main()
