#!/usr/bin/env python3
"""
13_coletor_uti_esf_municipal.py — Coleta UTI + ESF por município via CNES/TabNet

Fontes 100% públicas e auditáveis (Ministério da Saúde):
  UTI: CNES/DATASUS — Leitos SUS por tipo — http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/leit{UF}.def
  ESF: e-Gestor AB/MS — Equipes ESF por município — http://tabnet.datasus.gov.br/cgi/deftohtm.exe?esf/cnv/esf{UF}.def

Coleta: 27 UFs × 2 indicadores (UTI absoluto, cobertura ESF%)
Output: pipeline/data/uti_esf_municipal/uti_esf_{UF}_2026.json

Após coleta: re-executar 12_gerador_patches_v3.py para atualizar patches com dados reais.

Autor: Claude Code / EMET Gestão Brasil
Data: 2026-03-30
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
OUTPUT_DIR = os.path.join(BASE_DIR, 'pipeline', 'data', 'uti_esf_municipal')
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMEOUT = 120
DELAY = 2

UFS = {
    'ac':'AC','al':'AL','am':'AM','ap':'AP','ba':'BA','ce':'CE','df':'DF',
    'es':'ES','go':'GO','ma':'MA','mg':'MG','ms':'MS','mt':'MT','pa':'PA',
    'pb':'PB','pe':'PE','pi':'PI','pr':'PR','rj':'RJ','rn':'RN','ro':'RO',
    'rr':'RR','rs':'RS','sc':'SC','se':'SE','sp':'SP','to':'TO'
}

# Apenas 20 UFs sem patch real (pode sobrescrever passando args)
UFS_PRIORITARIAS = ['al','ba','ce','df','es','go','ma','mg','ms','mt',
                    'pb','pe','pi','pr','rj','rn','rs','sc','se','sp']


def post_tabnet(url, body):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (DMD-Pipeline/2.0)',
        'Referer': url,
    }
    resp = requests.post(url, data=body, headers=headers, timeout=TIMEOUT)
    resp.encoding = 'iso-8859-1'
    return resp.text


def parse_municipios(html):
    """Parseia tabela TabNet: extrai ibge6 → valor."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='tabdados')
    if not table:
        return {}
    text = table.get_text()
    # Padrão: código 6 dígitos + nome + número
    matches = re.findall(r'(\d{6})\s+([A-ZÀ-Ú][^\d]+?)([\d.]+)', text)
    result = {}
    for ibge6, nome, val in matches:
        val_clean = val.replace('.', '')
        try:
            result[ibge6] = {'nome': nome.strip(), 'val': int(val_clean)}
        except ValueError:
            pass
    return result


def coletar_uti_municipios(uf_lower):
    """
    Coleta leitos UTI SUS por município.
    Fonte: CNES/DATASUS — Leitos por Especialidade
    URL: tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/leit{uf}.def
    Filtro: Tipo_de_Leito = UTI (código 74/75/76/77/78)
    """
    url = f'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/leit{uf_lower}.def'
    # Linha=Município, filtrar leitos UTI (especialidade 074..078)
    body = (
        'Linha=Munic%EDpio'
        '&Coluna=--N%E3o-Ativa--'
        '&Incremento=Leitos_SUS'
        '&pesqmes1=Digite+o+texto+e+tecle+ENTER'
        '&SMession='
        '&formato=table'
        '&mosession='
        # Especialidade: UTI adulto (074), UTI pediátrica (075), UTI neonatal (076,077,078)
        '&SLeito_Especialidade=074&SLeito_Especialidade=075&SLeito_Especialidade=076'
        '&SLeito_Especialidade=077&SLeito_Especialidade=078'
    )
    try:
        html = post_tabnet(url, body)
        dados = parse_municipios(html)
        return {k: v['val'] for k, v in dados.items()}
    except Exception as e:
        print(f'    ERRO UTI: {e}')
        return {}


def coletar_esf_municipios(uf_lower):
    """
    Coleta cobertura ESF% por município.
    Fonte: e-Gestor AB / Ministério da Saúde
    URL: tabnet.datasus.gov.br/cgi/tabcgi.exe?esf/cnv/esf{uf}.def
    Incremento: cobertura_esf_%
    """
    url = f'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?esf/cnv/esf{uf_lower}.def'
    body = (
        'Linha=Munic%EDpio'
        '&Coluna=--N%E3o-Ativa--'
        '&Incremento=Cobertura_ESF_%25'
        '&pesqmes1=Digite+o+texto+e+tecle+ENTER'
        '&SMession='
        '&formato=table'
        '&mosession='
    )
    try:
        html = post_tabnet(url, body)
        dados = parse_municipios(html)
        # Cobertura vem como inteiro × 10 (ex: 650 = 65.0%)
        return {k: round(v['val'] / 10, 1) for k, v in dados.items()}
    except Exception as e:
        print(f'    ERRO ESF: {e}')
        return {}


def coletar_uf(uf_lower):
    """Coleta UTI + ESF para uma UF e consolida por ibge6."""
    uf_upper = UFS.get(uf_lower, uf_lower.upper())

    print(f'  UTI...', end=' ', flush=True)
    uti = coletar_uti_municipios(uf_lower)
    print(f'{len(uti)} mun.', end='  |  ', flush=True)
    time.sleep(DELAY)

    print(f'ESF...', end=' ', flush=True)
    esf = coletar_esf_municipios(uf_lower)
    print(f'{len(esf)} mun.', flush=True)
    time.sleep(DELAY)

    # Consolidar
    ibges = set(uti.keys()) | set(esf.keys())
    consolidado = {}
    for ibge6 in ibges:
        consolidado[ibge6] = {
            'uf':      uf_upper,
            'uti_sus': uti.get(ibge6, 0),
            'esf_pct': esf.get(ibge6, 0.0),
            'fonte':   'CNES_Mar2026',
        }
    return consolidado


def main():
    ts = datetime.now().isoformat()
    ufs_arg = [u.lower() for u in sys.argv[1:]] if len(sys.argv) > 1 else UFS_PRIORITARIAS

    print('=' * 60)
    print('  COLETA UTI + ESF MUNICIPAL — CNES/e-Gestor AB')
    print(f'  Fontes: DATASUS TabNet (100% públicas e auditáveis)')
    print(f'  UFs: {len(ufs_arg)} | Início: {ts}')
    print('=' * 60)

    todos = {}
    total_uti = 0
    total_esf = 0

    for i, uf in enumerate(ufs_arg):
        uf_upper = UFS.get(uf, uf.upper())
        print(f'\n  [{i+1}/{len(ufs_arg)}] {uf_upper}...')
        dados = coletar_uf(uf)

        n_uti = sum(1 for d in dados.values() if d['uti_sus'] > 0)
        n_esf = sum(1 for d in dados.values() if d['esf_pct'] > 0)
        total_uti += n_uti
        total_esf += n_esf

        for ibge6, d in dados.items():
            todos[ibge6] = d

        # Salvar por UF para permitir retomada
        uf_file = os.path.join(OUTPUT_DIR, f'uti_esf_{uf_upper}_2026.json')
        with open(uf_file, 'w', encoding='utf-8') as f:
            json.dump({'uf': uf_upper, 'coletado_em': ts,
                       'fonte_uti': 'CNES/DATASUS TabNet — leitos especializados',
                       'fonte_esf': 'e-Gestor AB/MS — cobertura ESF',
                       'municipios': dados}, f, ensure_ascii=False, indent=2)
        print(f'    → {n_uti} mun c/ UTI real | {n_esf} mun c/ ESF real | salvo em {os.path.basename(uf_file)}')

    # Arquivo consolidado
    output = {
        'fonte': 'CNES/DATASUS + e-Gestor AB — Ministério da Saúde',
        'auditavel_em': [
            'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/leit{UF}.def',
            'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?esf/cnv/esf{UF}.def',
        ],
        'coletado_em': ts,
        'total_municipios': len(todos),
        'municipios': todos,
    }
    output_file = os.path.join(OUTPUT_DIR, 'uti_esf_nacional_2026.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n{"=" * 60}')
    print('  RELATÓRIO')
    print(f'{"=" * 60}')
    print(f'  Municípios coletados: {len(todos):,}')
    print(f'  Com UTI real:         {total_uti:,}')
    print(f'  Com ESF real:         {total_esf:,}')
    print(f'  Arquivo:              {output_file}')
    print()
    print('  Próximo passo:')
    print('  python3 pipeline/scripts/12_gerador_patches_v3.py')
    print('  (re-gera patches com dados reais)')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
