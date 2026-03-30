#!/usr/bin/env python3
"""
11_encoder_munis_v41.py — Atualiza MUNIS_FULL_B64 no index.html com dados V41

Estratégia:
  1. Decodifica MUNIS existente (preserva todos os campos, inclusive AM com 146 campos)
  2. Lê banco V41 (128 colunas) com os 13 novos campos
  3. Mescla por ibge_7: atualiza campos novos nos municípios já existentes
  4. Re-comprime com gzip e substitui MUNIS_FULL_B64 no index.html

Novos campos mesclados (se ainda não existirem no MUNIS):
  medicos_abs, enfermeiros_abs, leitos_necessarios_p1631,
  deficit_leitos_pct (atualiza), deficit_uti_pct (atualiza),
  producao_aih_ano, receita_sus_ano, receita_per_capita,
  custo_medio_aih, obitos_hosp, letalidade_hosp_pct,
  nascimentos_nv, tmi_real

Autor: Claude Code / EMET Gestão Brasil
Data: 2026-03-30
"""

import base64
import csv
import gzip
import json
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_FILE = os.path.join(BASE_DIR, 'index.html')
CSV_V41 = os.path.join(BASE_DIR, 'dmd_banco_v41_integrado.csv')

# Campos V41 a mesclar no MUNIS (só adiciona se não existir ou for 0)
CAMPOS_NOVOS = [
    'medicos_abs', 'enfermeiros_abs', 'leitos_necessarios_p1631',
    'deficit_leitos_pct', 'deficit_uti_pct',
    'producao_aih_ano', 'receita_sus_ano', 'receita_per_capita',
    'custo_medio_aih', 'obitos_hosp', 'letalidade_hosp_pct',
    'nascimentos_nv', 'tmi_real',
    # P2 — campos adicionais V41.1
    'glosa_pct', 'glosa_valor', 'producao_amb_ano', 'leitos_obst',
    'prematuros_pct', 'cesareas_pct', 'mort_hospitalar_pct',
    'tmp_medio', 'ocupacao_leitos_pct', 'investimento_necessario',
    # Paridade AM — campos derivados + CNES
    'deficit_leitos_abs', 'deficit_uti_abs', 'uti_necessario', 'uti_1k',
    'leitos_uti', 'densidade_pop', 'criticidade_geral', 'nivel_criticidade',
    'acao_prioritaria', 'estab_total', 'hospitais_count', 'ubs_count',
    'upa_spa_count', 'policlinicas_count', 'prof_total',
    # Proxy regulação (calibrado SISREG AM)
    'fila_estimada', 'tempo_espera_estimado',
]

# Campos que devem SEMPRE ser atualizados (dado mais recente)
CAMPOS_SEMPRE_ATUALIZAR = {
    'producao_aih_ano', 'receita_sus_ano', 'receita_per_capita',
    'custo_medio_aih', 'obitos_hosp', 'letalidade_hosp_pct',
    'nascimentos_nv', 'tmi_real',
    'glosa_pct', 'glosa_valor', 'producao_amb_ano', 'mort_hospitalar_pct',
    'tmp_medio', 'ocupacao_leitos_pct', 'investimento_necessario',
    'deficit_leitos_abs', 'deficit_uti_abs', 'uti_necessario', 'uti_1k',
    'leitos_uti', 'criticidade_geral', 'nivel_criticidade', 'acao_prioritaria',
    'estab_total', 'hospitais_count', 'ubs_count', 'upa_spa_count',
    'policlinicas_count', 'prof_total',
    'fila_estimada', 'tempo_espera_estimado',
}


def safe_num(val):
    """Converte string para número preservando tipo."""
    if val is None or val == '':
        return 0
    s = str(val).replace(',', '.').strip()
    try:
        f = float(s)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return val


def main():
    ts = datetime.now().isoformat()
    print('=' * 60)
    print('  ENCODER MUNIS V41 — DMD Saúde Brasil')
    print(f'  Início: {ts}')
    print('=' * 60)

    # ── 1. Backup do index.html ──────────────────────────────
    backup = HTML_FILE + '.bak_v40'
    if not os.path.exists(backup):
        shutil.copy2(HTML_FILE, backup)
        print(f'\n[1/5] Backup criado: {backup}')
    else:
        print(f'\n[1/5] Backup já existe: {backup}')

    # ── 2. Carregar index.html ───────────────────────────────
    print('[2/5] Carregando index.html...')
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    marker_start = 'var MUNIS_FULL_B64 = "'
    marker_end = '";'
    idx_start = html.find(marker_start)
    if idx_start == -1:
        raise ValueError('MUNIS_FULL_B64 não encontrado no index.html')
    idx_b64_start = idx_start + len(marker_start)
    idx_b64_end = html.find(marker_end, idx_b64_start)
    b64_atual = html[idx_b64_start:idx_b64_end]
    print(f'  B64 atual: {len(b64_atual):,} chars')

    # ── 3. Decodificar MUNIS atual ───────────────────────────
    print('[3/5] Decodificando MUNIS atual...')
    raw = base64.b64decode(b64_atual)
    data = gzip.decompress(raw)
    munis_por_uf = json.loads(data.decode('utf-8'))

    # Construir índice ibge6→município para merge rápido
    ibge6_idx = {}  # ibge6 → (uf, posição na lista)
    for uf, lista in munis_por_uf.items():
        for i, mun in enumerate(lista):
            # ibge_cod pode ser int ou float; ibge_7 pode existir
            ibge7 = str(mun.get('ibge_7', mun.get('ibge_cod', ''))).replace('.0', '').strip()
            ibge6 = ibge7[:6] if len(ibge7) >= 7 else ibge7
            if ibge6:
                ibge6_idx[ibge6] = (uf, i)

    total_mun = sum(len(v) for v in munis_por_uf.values())
    print(f'  MUNIS: {total_mun:,} municípios em {len(munis_por_uf)} UFs')
    print(f'  Índice ibge6: {len(ibge6_idx):,} entradas')

    # ── 4. Mesclar dados V41 ─────────────────────────────────
    print('[4/5] Mesclando dados V41...')
    with open(CSV_V41, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        v41_rows = list(reader)

    merged = 0
    not_found = 0
    campos_adicionados = {c: 0 for c in CAMPOS_NOVOS}

    for row in v41_rows:
        ibge7 = str(row.get('ibge_7', row.get('ibge_cod', ''))).replace('.0', '').strip()
        ibge6 = ibge7[:6] if len(ibge7) >= 7 else ibge7

        if ibge6 not in ibge6_idx:
            not_found += 1
            continue

        uf, pos = ibge6_idx[ibge6]
        mun = munis_por_uf[uf][pos]

        for campo in CAMPOS_NOVOS:
            val = safe_num(row.get(campo, 0))
            # Atualiza se: campo não existe, ou campo está zerado, ou é campo de atualização forçada
            if campo not in mun or mun[campo] == 0 or campo in CAMPOS_SEMPRE_ATUALIZAR:
                if val != 0 or campo in CAMPOS_SEMPRE_ATUALIZAR:
                    mun[campo] = val
                    campos_adicionados[campo] += 1

        merged += 1

    print(f'  Municípios mesclados: {merged:,}')
    print(f'  Não encontrados: {not_found}')
    print(f'  Campos atualizados:')
    for campo, n in campos_adicionados.items():
        print(f'    {campo:30s}: {n:,} municípios')

    # Atualizar comentário da versão
    for uf in munis_por_uf:
        for mun in munis_por_uf[uf]:
            if mun.get('ciclo_atualizacao') != 'V41':
                if 'ciclo_atualizacao' in mun or merged > 0:
                    mun['versao_banco'] = 'v41+v40+v37+v3'

    # ── 5. Re-comprimir e substituir no HTML ─────────────────
    print('[5/5] Re-comprimindo e atualizando index.html...')
    json_bytes = json.dumps(munis_por_uf, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    compressed = gzip.compress(json_bytes, compresslevel=9)
    new_b64 = base64.b64encode(compressed).decode('ascii')

    print(f'  JSON: {len(json_bytes)/1024/1024:.2f} MB')
    print(f'  Comprimido: {len(compressed)/1024:.1f} KB')
    print(f'  B64 novo: {len(new_b64):,} chars (era {len(b64_atual):,})')

    # Substituir no HTML
    new_html = html[:idx_b64_start] + new_b64 + html[idx_b64_end:]

    # Atualizar comentário da versão do banco
    new_html = new_html.replace(
        'dados em MUNIS_FULL_B64 (DMD V42, 115 campos)',
        'dados em MUNIS_FULL_B64 (DMD V43, 128 campos)'
    )
    new_html = new_html.replace(
        'dados em MUNIS_FULL_B64 (DMD V43, 115 campos)',
        'dados em MUNIS_FULL_B64 (DMD V43, 128 campos)'
    )

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)

    # Relatório final
    print(f'\n{"=" * 60}')
    print('  RELATÓRIO ENCODER V41')
    print(f'{"=" * 60}')
    print(f'  MUNIS atualizado: {total_mun:,} municípios')
    print(f'  Colunas no banco: 128 (era 115)')
    print(f'  Novos campos: {len(CAMPOS_NOVOS)}')
    print(f'  index.html: {os.path.getsize(HTML_FILE)/1024/1024:.2f} MB')
    print(f'  Backup: {backup}')
    print(f'{"=" * 60}')
    print()
    print('  Próximos passos:')
    print('  1. Testar index.html localmente (file:// e http://)')
    print('  2. Verificar KPIs nos módulos analíticos')
    print('  3. git add + commit + push')


if __name__ == '__main__':
    main()
