#!/usr/bin/env python3
"""
05_coletor_datasus_nacional.py — Coleta dados reais do DATASUS TabNet
Fontes oficiais: SIH (internações), SIM (mortalidade), SINASC (nascidos vivos)

Coleta por UF agregada (27 UFs) para alimentar módulos analíticos.
Todos os dados são 100% públicos e auditáveis.

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
OUTPUT_DIR = os.path.join(BASE_DIR, 'pipeline', 'data', 'datasus_nacional')
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMEOUT = 120
DELAY = 3

UF_NOME_SIGLA = {
    'Rondônia': 'RO', 'Acre': 'AC', 'Amazonas': 'AM', 'Roraima': 'RR',
    'Pará': 'PA', 'Amapá': 'AP', 'Tocantins': 'TO', 'Maranhão': 'MA',
    'Piauí': 'PI', 'Ceará': 'CE', 'Rio Grande do Norte': 'RN',
    'Paraíba': 'PB', 'Pernambuco': 'PE', 'Alagoas': 'AL',
    'Sergipe': 'SE', 'Bahia': 'BA', 'Minas Gerais': 'MG',
    'Espírito Santo': 'ES', 'Rio de Janeiro': 'RJ', 'São Paulo': 'SP',
    'Paraná': 'PR', 'Santa Catarina': 'SC', 'Rio Grande do Sul': 'RS',
    'Mato Grosso do Sul': 'MS', 'Mato Grosso': 'MT', 'Goiás': 'GO',
    'Distrito Federal': 'DF',
}


UF_CODES = {
    '11':'Rondônia','12':'Acre','13':'Amazonas','14':'Roraima','15':'Pará',
    '16':'Amapá','17':'Tocantins','21':'Maranhão','22':'Piauí','23':'Ceará',
    '24':'Rio Grande do Norte','25':'Paraíba','26':'Pernambuco','27':'Alagoas',
    '28':'Sergipe','29':'Bahia','31':'Minas Gerais','32':'Espírito Santo',
    '33':'Rio de Janeiro','35':'São Paulo','41':'Paraná','42':'Santa Catarina',
    '43':'Rio Grande do Sul','50':'Mato Grosso do Sul','51':'Mato Grosso',
    '52':'Goiás','53':'Distrito Federal'
}

def parse_tabnet_uf(html):
    """Parseia HTML do TabNet extraindo dados por UF usando posições no texto concatenado."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='tabdados')
    if not table:
        return {}

    text = table.get_text()

    # Encontrar posição de cada UF no texto
    positions = []
    for cod, nome in UF_CODES.items():
        pattern = cod + ' ' + re.escape(nome)
        match = re.search(pattern, text)
        if match:
            positions.append((match.start(), match.end(), cod, nome))

    positions.sort(key=lambda x: x[0])

    resultados = {}
    for i, (start, end, cod, nome) in enumerate(positions):
        next_start = positions[i+1][0] if i+1 < len(positions) else len(text)
        val_text = text[end:next_start].replace('.', '').replace(',', '.').strip()
        try:
            resultados[nome] = float(val_text) if '.' in val_text else int(val_text)
        except ValueError:
            resultados[nome] = 0

    return resultados


def tabnet_post(url, body):
    """Faz POST ao TabNet e retorna HTML."""
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': url.replace('tabcgi.exe', 'deftohtm.exe'),
    }
    resp = requests.post(url, data=body, headers=headers, timeout=TIMEOUT)
    resp.encoding = 'iso-8859-1'
    return resp.text


# ═══════════════════════════════════════════════════════════
# COLETA SIH — Internações hospitalares 2024
# ═══════════════════════════════════════════════════════════

def coletar_sih(ano='2024'):
    """Coleta 4 métricas SIH por UF: AIH aprovadas, valor, dias permanência, óbitos.
    Soma os 12 meses do ano."""
    url = 'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/qiuf.def'
    base = 'Linha=Unidade_da_Federa%E7%E3o&Coluna=--N%E3o-Ativa--&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession='

    # Arquivos: qiufAAMM.dbf — todos os 12 meses
    arquivos = '&'.join([f'Arquivos=qiuf{ano[2:]}{str(m).zfill(2)}.dbf' for m in range(1, 13)])

    metricas = {
        'aih_qtd': 'AIH_aprovadas',
        'aih_valor': 'Valor_total',
        'dias_perm': 'Dias_de_perman%EAncia',
        'obitos_hosp': '%D3bitos',
    }

    resultados = {}
    for campo, incremento in metricas.items():
        print(f"  SIH {campo}...", end=' ', flush=True)
        body = f'{base}&Incremento={incremento}&{arquivos}'
        try:
            html = tabnet_post(url, body)
            dados = parse_tabnet_uf(html)
            for nome, val in dados.items():
                if nome not in resultados:
                    resultados[nome] = {}
                resultados[nome][campo] = val
            print(f"{len(dados)} UFs")
        except Exception as e:
            print(f"ERRO: {e}")
        time.sleep(DELAY)

    # Derivados
    for nome, d in resultados.items():
        qtd = d.get('aih_qtd', 0)
        if qtd > 0:
            d['custo_medio_aih'] = round(d.get('aih_valor', 0) / qtd, 2)
            d['tmp'] = round(d.get('dias_perm', 0) / qtd, 1)
            d['letalidade_hosp'] = round(d.get('obitos_hosp', 0) / qtd * 100, 3)

    return resultados


# ═══════════════════════════════════════════════════════════
# COLETA SIM — Mortalidade infantil + materna 2022
# ═══════════════════════════════════════════════════════════

def coletar_mortalidade(ano='2022'):
    """Coleta óbitos infantis e maternos por UF. Usa Linha=UF (sem região)."""
    resultados = {}

    # Infantil
    print(f"  SIM infantil...", end=' ', flush=True)
    url_inf = 'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/inf10uf.def'
    body_inf = f'Linha=Unidade_da_Federa%E7%E3o&Coluna=--N%E3o-Ativa--&Incremento=%D3bitos_p%2FResid%EAnc&Arquivos=infuf{ano[2:]}.dbf&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession='
    try:
        html = tabnet_post(url_inf, body_inf)
        dados = parse_tabnet_uf(html)
        for nome, val in dados.items():
            resultados[nome] = {'obitos_infantis': int(val)}
        print(f"{len(dados)} UFs")
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(DELAY)

    # Materna
    print(f"  SIM materna...", end=' ', flush=True)
    url_mat = 'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/mat10uf.def'
    body_mat = f'Linha=Unidade_da_Federa%E7%E3o&Coluna=--N%E3o-Ativa--&Incremento=%D3bitos_maternos&Arquivos=matuf{ano[2:]}.dbf&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession='
    try:
        html = tabnet_post(url_mat, body_mat)
        dados = parse_tabnet_uf(html)
        for nome, val in dados.items():
            if nome in resultados:
                resultados[nome]['obitos_maternos'] = int(val)
            else:
                resultados[nome] = {'obitos_infantis': 0, 'obitos_maternos': int(val)}
        print(f"{len(dados)} UFs")
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(DELAY)

    # SINASC — nascidos vivos
    print(f"  SINASC NV...", end=' ', flush=True)
    url_nv = 'http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sinasc/cnv/nvuf.def'
    body_nv = f'Linha=Unidade_da_Federa%E7%E3o&Coluna=--N%E3o-Ativa--&Incremento=Nascim_p%2Fresid.m%E3e&Arquivos=nvuf{ano[2:]}.dbf&pesqmes1=Digite+o+texto+e+tecle+ENTER&SMession=&formato=table&mosession='
    try:
        html = tabnet_post(url_nv, body_nv)
        dados = parse_tabnet_uf(html)
        for nome, val in dados.items():
            if nome in resultados:
                resultados[nome]['nascidos_vivos'] = int(val)
            else:
                resultados[nome] = {'obitos_infantis': 0, 'obitos_maternos': 0, 'nascidos_vivos': int(val)}
        print(f"{len(dados)} UFs")
    except Exception as e:
        print(f"ERRO: {e}")

    # Calcular taxas
    for nome, d in resultados.items():
        nv = d.get('nascidos_vivos', 0)
        if nv > 0:
            d['tmi'] = round(d.get('obitos_infantis', 0) / nv * 1000, 2)
            d['tmm'] = round(d.get('obitos_maternos', 0) / nv * 100000, 1)

    return resultados


# ═══════════════════════════════════════════════════════════
# CONSOLIDAÇÃO
# ═══════════════════════════════════════════════════════════

def main():
    timestamp = datetime.now().isoformat()
    print("=" * 60)
    print("  COLETA DATASUS NACIONAL — DMD Saúde Brasil")
    print(f"  Início: {timestamp}")
    print("=" * 60)

    print("\n[1/2] SIH 2024 — Internações hospitalares")
    sih = coletar_sih('2024')

    print("\n[2/2] SIM/SINASC 2022 — Mortalidade")
    mort = coletar_mortalidade('2022')

    # Consolidar por sigla
    consolidado = {}
    for nome, sigla in UF_NOME_SIGLA.items():
        d = {'uf': sigla, 'uf_nome': nome}
        if nome in sih:
            d.update(sih[nome])
        if nome in mort:
            d.update(mort[nome])
        consolidado[sigla] = d

    # Salvar
    output = {
        'fonte': 'DATASUS TabNet — dados oficiais do Ministério da Saúde',
        'coletado_em': timestamp,
        'competencias': {
            'sih': '2024 (jan-dez) — Procedimentos hospitalares do SUS',
            'mortalidade_infantil': '2022 — SIM/DATASUS (último consolidado)',
            'mortalidade_materna': '2022 — SIM/DATASUS',
            'nascidos_vivos': '2022 — SINASC/DATASUS',
        },
        'urls_fonte': {
            'sih': 'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qiuf.def',
            'sim_infantil': 'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/inf10uf.def',
            'sim_materna': 'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/mat10uf.def',
            'sinasc': 'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinasc/cnv/nvuf.def',
        },
        'ufs': consolidado,
    }

    output_file = os.path.join(OUTPUT_DIR, 'datasus_consolidado_nacional.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Relatório
    print("\n" + "=" * 60)
    print("  RELATÓRIO DE COLETA — DADOS REAIS DATASUS")
    print("=" * 60)

    ufs_sih = sum(1 for d in consolidado.values() if d.get('aih_qtd', 0) > 0)
    ufs_mort = sum(1 for d in consolidado.values() if d.get('tmi', 0) > 0)
    total_aih = sum(d.get('aih_qtd', 0) for d in consolidado.values())
    total_valor = sum(d.get('aih_valor', 0) for d in consolidado.values())
    total_obitos_inf = sum(d.get('obitos_infantis', 0) for d in consolidado.values())
    total_nv = sum(d.get('nascidos_vivos', 0) for d in consolidado.values())

    print(f"  UFs com dados SIH:         {ufs_sih}/27")
    print(f"  UFs com mortalidade:        {ufs_mort}/27")
    print(f"  Total AIH 2024:             {total_aih:>12,}")
    print(f"  Valor total 2024:           R$ {total_valor:>14,.2f}")
    print(f"  Óbitos infantis 2022:       {total_obitos_inf:>12,}")
    print(f"  Nascidos vivos 2022:        {total_nv:>12,}")
    print(f"  TMI Brasil 2022:            {total_obitos_inf/total_nv*1000:.2f} /1k NV" if total_nv else "")

    print(f"\n  Amostra (SP):")
    sp = consolidado.get('SP', {})
    for k, v in sorted(sp.items()):
        if k not in ('uf', 'uf_nome'):
            print(f"    {k:25s} = {v:>15,}" if isinstance(v, int) else f"    {k:25s} = {v}")

    print(f"\n  Arquivo salvo: {output_file}")
    print("=" * 60)

    return output_file


if __name__ == '__main__':
    main()
