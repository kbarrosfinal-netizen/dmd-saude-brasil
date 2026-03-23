#!/usr/bin/env python3
"""
SCRIPT 01 — COLETOR CAPS/CNES TabNet
DMD Saúde Brasil | EMET Gestão Brasil | Pipeline Nacional v3.0

Coleta CAPS ativos por município via TabNet DATASUS
Tipo de estab: 70-76 (CAPS I, CAPS II, CAPS III, CAPSi, CAPSad, CAPSad III, CAPSad IV)
Modo: via requests POST ao CGI do TabNet
"""

import requests
import re
import json
import csv
import datetime
import hashlib
import unicodedata
import time
import os
from pathlib import Path

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────
BASE_DIR = Path("/home/user/dmd-pipeline-nacional")
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "01_tabnet_caps.log"

COMPETENCIA = "03/2026"  # MM/AAAA

# Mapeamento tipos CAPS (TabNet)
CAPS_TIPOS = {
    "70": "CAPS I",
    "71": "CAPS II",
    "72": "CAPS III",
    "73": "CAPSi",
    "74": "CAPSad",
    "75": "CAPSad III",
    "76": "CAPSad IV",
    "67": "SRT",   # Serviço Residencial Terapêutico
}

# UFs por código IBGE (2 dígitos)
UF_CODIGOS = {
    "AC": "12", "AL": "27", "AM": "13", "AP": "16", "BA": "29",
    "CE": "23", "DF": "53", "ES": "32", "GO": "52", "MA": "21",
    "MG": "31", "MS": "50", "MT": "51", "PA": "15", "PB": "25",
    "PE": "26", "PI": "22", "PR": "41", "RJ": "33", "RN": "24",
    "RO": "11", "RR": "14", "RS": "43", "SC": "42", "SE": "28",
    "SP": "35", "TO": "17",
}

FASE_1_NORTE = ["AC", "AM", "AP", "PA", "RO", "RR", "TO"]

# ─── UTILITÁRIOS ──────────────────────────────────────────────────────────
def normalize(nome: str) -> str:
    nfkd = unicodedata.normalize("NFKD", nome.upper())
    return re.sub(r"[^A-Z0-9 ]", "", "".join(c for c in nfkd if not unicodedata.combining(c))).strip()

def log(msg, level="INFO"):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}][{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ─── TABNET CGI POST ──────────────────────────────────────────────────────
TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe"

def build_tabnet_payload_caps(uf_sigla: str, uf_cod: str, tipo_codigo: str) -> dict:
    """
    Constrói payload para consulta TabNet CNES Estabelecimentos
    Linha: Município | Coluna: Tipo Estabelecimento | Conteúdo: Quantidade
    Filtros: UF selecionada + Tipo específico (CAPS/SRT)
    """
    return {
        "Linha": "Município",
        "Coluna": "--Nenhuma--",
        "Incremento": "Estabelecimentos",
        "Arquivos": "estabbr.def",
        "pesqmes1": "Digite o texto e clique na lupa",
        "SMunic": "TODAS_AS_CATEGORIAS__",
        "SMunicgestor": "TODAS_AS_CATEGORIAS__",
        "SCapital": "TODAS_AS_CATEGORIAS__",
        "SRegsaud": "TODAS_AS_CATEGORIAS__",
        "SMacsaud": "TODAS_AS_CATEGORIAS__",
        "SMicr": "TODAS_AS_CATEGORIAS__",
        "SRmetrop": "TODAS_AS_CATEGORIAS__",
        "STerCidadania": "TODAS_AS_CATEGORIAS__",
        "SMesorregPNDR": "TODAS_AS_CATEGORIAS__",
        "SAmazLegal": "TODAS_AS_CATEGORIAS__",
        "SSemiarido": "TODAS_AS_CATEGORIAS__",
        "SFaixFront": "TODAS_AS_CATEGORIAS__",
        "SZonFront": "TODAS_AS_CATEGORIAS__",
        "SMunExtrPobr": "TODAS_AS_CATEGORIAS__",
        "SEnsPesq": "TODAS_AS_CATEGORIAS__",
        "SNatJur": "TODAS_AS_CATEGORIAS__",
        "SEsfJur": "TODAS_AS_CATEGORIAS__",
        "SEsfAdm": "TODAS_AS_CATEGORIAS__",
        "SNatureza": "TODAS_AS_CATEGORIAS__",
        "STipoUnid": tipo_codigo,  # ex: "70" para CAPS I
        "STipoGestao": "TODAS_AS_CATEGORIAS__",
        "SUF": uf_cod,             # ex: "13" para AM
        "zeran": "1",
        "formato": "table",
        "mostre": "Mostra",
    }

def parse_tabnet_html(html: str, uf: str, tipo: str) -> list:
    """
    Parse da tabela HTML retornada pelo TabNet
    Retorna lista de {'municipio': str, 'ibge6': str, 'count': int}
    """
    resultados = []
    
    # Encontrar tabela de resultados
    # TabNet retorna tabela com class="tabdados" ou similar
    pattern = r'<td[^>]*>(\d{6})\s+([^<]+)</td>\s*<td[^>]*>(\d+)</td>'
    matches = re.findall(pattern, html, re.IGNORECASE)
    
    for m in matches:
        ibge6, nome, count = m
        resultados.append({
            "ibge6": ibge6.strip(),
            "municipio_tabnet": nome.strip(),
            "count": int(count),
            "tipo": tipo,
            "uf": uf,
        })
    
    # Fallback: padrão alternativo
    if not matches:
        # Tenta padrão sem código IBGE
        pattern2 = r'<td[^>]*class="[^"]*linha[^"]*"[^>]*>([^<]{3,50})</td>\s*<td[^>]*>(\d+)</td>'
        matches2 = re.findall(pattern2, html, re.IGNORECASE)
        for nome, count in matches2:
            resultados.append({
                "ibge6": "",
                "municipio_tabnet": nome.strip(),
                "count": int(count),
                "tipo": tipo,
                "uf": uf,
            })
    
    return resultados

def fetch_caps_por_uf(uf_sigla: str, tipo_codigo: str) -> dict:
    """Faz requisição ao TabNet e retorna dados CAPS/SRT por município."""
    uf_cod = UF_CODIGOS.get(uf_sigla, "")
    tipo_nome = CAPS_TIPOS.get(tipo_codigo, f"TIPO_{tipo_codigo}")
    
    log(f"Consultando TabNet: UF={uf_sigla} Tipo={tipo_nome} ({tipo_codigo})")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DMD-Pipeline/3.0; EMET-Saude-Brasil)",
            "Referer": "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/estabbr.def",
            "Accept": "text/html,application/xhtml+xml",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = build_tabnet_payload_caps(uf_sigla, uf_cod, tipo_codigo)
        
        r = requests.post(
            f"{TABNET_URL}?cnes/cnv/estabbr.def",
            data=payload,
            headers=headers,
            timeout=30
        )
        
        log(f"  Status HTTP: {r.status_code} | Tamanho: {len(r.content):,} bytes")
        
        if r.status_code != 200:
            return {"status": "HTTP_ERROR", "code": r.status_code, "data": []}
        
        resultados = parse_tabnet_html(r.text, uf_sigla, tipo_nome)
        log(f"  Municípios encontrados: {len(resultados)}")
        
        return {
            "status": "OK",
            "uf": uf_sigla,
            "tipo": tipo_nome,
            "tipo_cod": tipo_codigo,
            "competencia": COMPETENCIA,
            "total_municipios_com_dado": len(resultados),
            "data": resultados,
            "html_size": len(r.text),
        }
        
    except requests.Timeout:
        log(f"  TIMEOUT para UF={uf_sigla} Tipo={tipo_nome}", "WARN")
        return {"status": "TIMEOUT", "data": []}
    except Exception as e:
        log(f"  ERRO: {e}", "ERROR")
        return {"status": "ERROR", "message": str(e), "data": []}

# ─── AGREGAÇÃO POR MUNICÍPIO ──────────────────────────────────────────────
def agregar_caps_municipio(resultados_por_tipo: list) -> dict:
    """
    Agrega resultados de múltiplos tipos CAPS em dicionário por município
    Chave: ibge6 (ou nome normalizado como fallback)
    """
    agregado = {}  # ibge6 -> {caps, srt, tipos_lista}
    
    for resultado in resultados_por_tipo:
        if resultado["status"] != "OK":
            continue
        
        tipo_nome = resultado["tipo"]
        
        for item in resultado["data"]:
            ibge6 = item["ibge6"]
            nome = item["municipio_tabnet"]
            count = item["count"]
            
            key = ibge6 if ibge6 else normalize(nome)
            
            if key not in agregado:
                agregado[key] = {
                    "ibge6": ibge6,
                    "municipio_tabnet": nome,
                    "municipio_norm": normalize(nome),
                    "caps_total": 0,
                    "srt_total": 0,
                    "tipos_caps": [],
                }
            
            if tipo_nome == "SRT":
                agregado[key]["srt_total"] += count
            else:
                agregado[key]["caps_total"] += count
                if count > 0 and tipo_nome not in agregado[key]["tipos_caps"]:
                    agregado[key]["tipos_caps"].append(tipo_nome)
    
    return agregado

# ─── SALVAR CSV POR UF ────────────────────────────────────────────────────
def salvar_csv_caps(uf: str, agregado: dict, competencia_str: str):
    comp_fmt = competencia_str.replace("/", "")  # "032026"
    filename = DATA_DIR / f"norte" / f"{uf}_CAPS_{comp_fmt}.csv"
    filename.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ibge6", "municipio_tabnet", "municipio_norm",
            "caps_total", "srt_total", "tipos_caps"
        ])
        writer.writeheader()
        for key, row in agregado.items():
            writer.writerow({
                **row,
                "tipos_caps": "|".join(row["tipos_caps"])
            })
    
    log(f"  CSV salvo: {filename} ({len(agregado)} registros)")
    return str(filename)

# ─── MAIN ─────────────────────────────────────────────────────────────────
def processar_uf_fase1(uf: str) -> dict:
    """Processa uma UF completa — todos os tipos CAPS + SRT"""
    log(f"\n{'='*60}")
    log(f"INICIANDO UF: {uf}")
    log(f"{'='*60}")
    
    resultados = []
    tipos_para_buscar = list(CAPS_TIPOS.keys())  # 70-76 + 67
    
    for tipo_cod in tipos_para_buscar:
        result = fetch_caps_por_uf(uf, tipo_cod)
        resultados.append(result)
        time.sleep(1.5)  # Rate limiting respeitoso ao TabNet
    
    # Agregar
    agregado = agregar_caps_municipio(resultados)
    
    # Salvar CSV
    csv_path = salvar_csv_caps(uf, agregado, COMPETENCIA)
    
    # Patch JSON preliminar
    patch = {
        "competencia": COMPETENCIA,
        "uf": uf,
        "gerado_em": datetime.datetime.now().isoformat(),
        "fonte": "CNES_TabNet_Mar2026",
        "total_municipios_com_caps": sum(1 for v in agregado.values() if v["caps_total"] > 0),
        "total_caps": sum(v["caps_total"] for v in agregado.values()),
        "total_srt": sum(v["srt_total"] for v in agregado.values()),
        "status_coleta": {t: resultados[i]["status"] for i, t in enumerate(tipos_para_buscar)},
        "municipios": [
            {
                "ibge6": v["ibge6"],
                "nome": v["municipio_tabnet"],
                "caps": v["caps_total"],
                "srt": v["srt_total"],
                "caps_tipos": "|".join(v["tipos_caps"]),
            }
            for v in agregado.values()
        ]
    }
    
    patch_path = BASE_DIR / "patches" / f"{uf}_CAPS_{COMPETENCIA.replace('/', '')}_patch.json"
    with open(patch_path, "w", encoding="utf-8") as f:
        json.dump(patch, f, ensure_ascii=False, indent=2)
    
    log(f"Patch salvo: {patch_path}")
    log(f"UF {uf}: {patch['total_caps']} CAPS | {patch['total_srt']} SRT")
    
    return patch

if __name__ == "__main__":
    log("="*60)
    log("SCRIPT 01 — COLETOR CAPS/CNES TABNET — FASE 1 NORTE")
    log("="*60)
    
    resultados_fase1 = {}
    
    for uf in FASE_1_NORTE:
        patch = processar_uf_fase1(uf)
        resultados_fase1[uf] = {
            "caps_total": patch["total_caps"],
            "srt_total": patch["total_srt"],
            "municipios_com_caps": patch["total_municipios_com_caps"],
            "status": "OK" if all(v == "OK" for v in patch["status_coleta"].values()) else "PARCIAL"
        }
        time.sleep(3)  # Pausa entre UFs
    
    log("\n" + "="*60)
    log("RESUMO FASE 1 — NORTE")
    log("="*60)
    for uf, r in resultados_fase1.items():
        log(f"  {uf}: {r['caps_total']} CAPS | {r['srt_total']} SRT | Status: {r['status']}")
    
    with open(BASE_DIR / "logs" / "fase1_norte_resumo.json", "w") as f:
        json.dump(resultados_fase1, f, indent=2)
