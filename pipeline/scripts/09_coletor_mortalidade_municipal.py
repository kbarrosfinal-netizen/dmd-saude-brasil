#!/usr/bin/env python3
"""
09_coletor_mortalidade_municipal.py — Coleta mortalidade infantil e nascidos vivos por MUNICÍPIO
Fonte: TabNet DATASUS — SIM 2024 (óbitos infantis) + SINASC 2024 (nascidos vivos)
Calcula: TMI (taxa de mortalidade infantil) por município = óbitos/NV × 1000

Autor: Claude Code / EMET Gestão Brasil
Data: 2026-03-29
"""
import json, os, re, sys, time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, 'pipeline', 'data', 'mortalidade_municipal')
os.makedirs(OUTPUT_DIR, exist_ok=True)
TIMEOUT, DELAY = 120, 2

UFS = {'ac':'AC','al':'AL','am':'AM','ap':'AP','ba':'BA','ce':'CE','df':'DF',
       'es':'ES','go':'GO','ma':'MA','mg':'MG','ms':'MS','mt':'MT','pa':'PA',
       'pb':'PB','pe':'PE','pi':'PI','pr':'PR','rj':'RJ','rn':'RN','ro':'RO',
       'rr':'RR','rs':'RS','sc':'SC','se':'SE','sp':'SP','to':'TO'}

def parse_mun(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='tabdados')
    if not table: return {}
    text = table.get_text()
    matches = re.findall(r'(\d{6})\s+([A-ZÀ-Ú][^\d]+?)([\d.]+)', text)
    return {ibge6: {'nome': nome.strip(), 'val': int(val.replace('.',''))} for ibge6, nome, val in matches}

def post(url, body):
    h = {'Content-Type':'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0','Referer':url}
    r = requests.post(url, data=body, headers=h, timeout=TIMEOUT)
    r.encoding = 'iso-8859-1'
    return r.text

def coletar_uf(uf_lower, ano='24'):
    result = {}
    # Óbitos infantis
    url1 = f'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/inf10{uf_lower}.def'
    body1 = f'Linha=Munic%EDpio&Coluna=--N%E3o-Ativa--&Incremento=%D3bitos_p%2FResid%EAnc&Arquivos=inf{uf_lower}{ano}.dbf&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession='
    try:
        dados = parse_mun(post(url1, body1))
        for ibge6, d in dados.items():
            result[ibge6] = {'nome': d['nome'], 'obitos_inf': d['val']}
    except: pass
    time.sleep(DELAY)

    # Nascidos vivos
    url2 = f'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sinasc/cnv/nv{uf_lower}.def'
    body2 = f'Linha=Munic%EDpio&Coluna=--N%E3o-Ativa--&Incremento=Nascim_p%2Fresid.m%E3e&Arquivos=nv{uf_lower}{ano}.dbf&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession='
    try:
        dados = parse_mun(post(url2, body2))
        for ibge6, d in dados.items():
            if ibge6 in result:
                result[ibge6]['nv'] = d['val']
            else:
                result[ibge6] = {'nome': d['nome'], 'obitos_inf': 0, 'nv': d['val']}
    except: pass

    # TMI
    for d in result.values():
        nv = d.get('nv', 0)
        d['tmi'] = round(d.get('obitos_inf', 0) / nv * 1000, 2) if nv > 0 else 0

    return result

def main():
    ufs_arg = [u.lower() for u in sys.argv[1:]] if len(sys.argv) > 1 else sorted(UFS.keys())
    ts = datetime.now().isoformat()
    print(f'{"="*60}\n  COLETA MORTALIDADE MUNICIPAL — SIM/SINASC 2024\n  UFs: {len(ufs_arg)} | Início: {ts}\n{"="*60}')

    todos = {}
    for i, uf in enumerate(ufs_arg):
        print(f'  [{i+1}/{len(ufs_arg)}] {UFS.get(uf,uf.upper())}...', end=' ', flush=True)
        dados = coletar_uf(uf)
        n = len(dados)
        ob = sum(d.get('obitos_inf', 0) for d in dados.values())
        nv = sum(d.get('nv', 0) for d in dados.values())
        print(f'{n} mun. | {ob:,} óbitos | {nv:,} NV')
        for ibge6, d in dados.items():
            d['uf'] = UFS.get(uf, uf.upper())
            todos[ibge6] = d
        time.sleep(DELAY)

    output = {'fonte': 'TabNet DATASUS SIM/SINASC 2024', 'coletado_em': ts,
              'total_municipios': len(todos), 'municipios': todos}
    f_path = os.path.join(OUTPUT_DIR, 'mortalidade_municipal_2024.json')
    with open(f_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_ob = sum(d.get('obitos_inf', 0) for d in todos.values())
    total_nv = sum(d.get('nv', 0) for d in todos.values())
    tmi_br = total_ob / total_nv * 1000 if total_nv else 0
    print(f'\n{"="*60}\n  RELATÓRIO\n{"="*60}')
    print(f'  Municípios: {len(todos):,} | Óbitos: {total_ob:,} | NV: {total_nv:,} | TMI BR: {tmi_br:.2f}/1kNV')
    print(f'  Arquivo: {f_path}\n{"="*60}')

if __name__ == '__main__':
    main()
