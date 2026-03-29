#!/usr/bin/env python3
"""
08_coletor_sih_municipal.py — Coleta SIH por MUNICÍPIO para todas as 27 UFs
Fonte: TabNet DATASUS — SIH 2025 (jan-dez)

Coleta: AIH aprovadas + Valor total + Óbitos hospitalares por município
Calcula: custo_medio_aih, letalidade_hosp por município

Autor: Claude Code / EMET Gestão Brasil
Data: 2026-03-29
"""

import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, 'pipeline', 'data', 'sih_municipal')
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMEOUT = 120
DELAY = 2

UF_SIGLAS = {
    'ac':'AC','al':'AL','am':'AM','ap':'AP','ba':'BA','ce':'CE','df':'DF',
    'es':'ES','go':'GO','ma':'MA','mg':'MG','ms':'MS','mt':'MT','pa':'PA',
    'pb':'PB','pe':'PE','pi':'PI','pr':'PR','rj':'RJ','rn':'RN','ro':'RO',
    'rr':'RR','rs':'RS','sc':'SC','se':'SE','sp':'SP','to':'TO'
}


def parse_municipios(html):
    """Parseia tabela TabNet com dados por município (formato: '120010 Acrelândia4.315')."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='tabdados')
    if not table:
        return {}
    text = table.get_text()
    matches = re.findall(r'(\d{6})\s+([A-ZÀ-Ú][^\d]+?)([\d.]+)', text)
    result = {}
    for ibge6, nome, val in matches:
        nome = nome.strip()
        val_clean = val.replace('.', '')
        try:
            result[ibge6] = {'nome': nome, 'val': int(val_clean)}
        except ValueError:
            pass
    return result


def post_tabnet(url, body):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (DMD-Pipeline/2.0)',
        'Referer': url,
    }
    resp = requests.post(url, data=body, headers=headers, timeout=TIMEOUT)
    resp.encoding = 'iso-8859-1'
    return resp.text


def coletar_uf(uf_lower, ano='2025'):
    """Coleta 3 métricas SIH por município para uma UF (12 meses somados)."""
    url = f'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/qi{uf_lower}.def'
    arqs = '&'.join([f'Arquivos=qi{uf_lower}{ano[2:]}{str(m).zfill(2)}.dbf' for m in range(1, 13)])
    base = f'Linha=Munic%EDpio&Coluna=--N%E3o-Ativa--&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession=&{arqs}'

    metricas = {}

    # AIH aprovadas
    try:
        html = post_tabnet(url, f'{base}&Incremento=AIH_aprovadas')
        dados = parse_municipios(html)
        for ibge6, d in dados.items():
            metricas[ibge6] = {'nome': d['nome'], 'aih_qtd': d['val']}
    except Exception as e:
        print(f'    ERRO AIH: {e}')
    time.sleep(DELAY)

    # Valor total
    try:
        html = post_tabnet(url, f'{base}&Incremento=Valor_total')
        dados = parse_municipios(html)
        for ibge6, d in dados.items():
            if ibge6 in metricas:
                metricas[ibge6]['aih_valor'] = d['val']
    except Exception as e:
        print(f'    ERRO Valor: {e}')
    time.sleep(DELAY)

    # Óbitos
    try:
        html = post_tabnet(url, f'{base}&Incremento=%D3bitos')
        dados = parse_municipios(html)
        for ibge6, d in dados.items():
            if ibge6 in metricas:
                metricas[ibge6]['obitos_hosp'] = d['val']
    except Exception as e:
        print(f'    ERRO Óbitos: {e}')

    # Calcular derivados
    for ibge6, d in metricas.items():
        qtd = d.get('aih_qtd', 0)
        if qtd > 0:
            d['custo_medio_aih'] = round(d.get('aih_valor', 0) / qtd, 2)
            d['letalidade_hosp'] = round(d.get('obitos_hosp', 0) / qtd * 100, 3)
        else:
            d['custo_medio_aih'] = 0
            d['letalidade_hosp'] = 0

    return metricas


def main():
    timestamp = datetime.now().isoformat()
    ufs_arg = [u.lower() for u in sys.argv[1:]] if len(sys.argv) > 1 else sorted(UF_SIGLAS.keys())

    print('=' * 60)
    print('  COLETA SIH MUNICIPAL — TabNet DATASUS 2025')
    print(f'  UFs: {len(ufs_arg)} | Início: {timestamp}')
    print('=' * 60)

    todos = {}
    total_mun = 0
    total_aih = 0

    for i, uf_lower in enumerate(ufs_arg):
        uf_upper = UF_SIGLAS.get(uf_lower, uf_lower.upper())
        print(f'  [{i+1}/{len(ufs_arg)}] {uf_upper}...', end=' ', flush=True)

        metricas = coletar_uf(uf_lower, '2025')
        n = len(metricas)
        aih = sum(d.get('aih_qtd', 0) for d in metricas.values())
        print(f'{n} mun. | {aih:,} AIH')

        for ibge6, d in metricas.items():
            d['uf'] = uf_upper
            d['ibge6'] = ibge6
            todos[ibge6] = d

        total_mun += n
        total_aih += aih
        time.sleep(DELAY)

    # Salvar JSON consolidado
    output = {
        'fonte': 'TabNet DATASUS — SIH 2025 por município de internação',
        'coletado_em': timestamp,
        'total_municipios': total_mun,
        'total_aih': total_aih,
        'municipios': todos,
    }
    output_file = os.path.join(OUTPUT_DIR, 'sih_municipal_2025.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n{"=" * 60}')
    print(f'  RELATÓRIO COLETA SIH MUNICIPAL')
    print(f'{"=" * 60}')
    print(f'  Municípios com dados: {total_mun:,}')
    print(f'  Total AIH 2025:       {total_aih:,}')
    print(f'  Arquivo: {output_file}')
    print(f'{"=" * 60}')

    return output_file


if __name__ == '__main__':
    main()
