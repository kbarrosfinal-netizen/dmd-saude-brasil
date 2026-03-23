#!/usr/bin/env python3
"""
SCRIPT 00 — BASE IBGE MUNICÍPIOS
DMD Saúde Brasil | EMET Gestão Brasil
Coleta população 2022 de todos os 5.570 municípios via API SIDRA/IBGE
Gera municipios_ibge.json — referência mestra do pipeline
"""

import requests
import json
import re
import unicodedata
import datetime
import hashlib

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────
OUT_JSON = "/home/user/dmd-pipeline-nacional/data/municipios_ibge.json"
LOG_FILE = "/home/user/dmd-pipeline-nacional/logs/00_ibge_base.log"

MUNICIPIOS_IBGE_POR_UF = {
    "AC": 22, "AL": 102, "AM": 62, "AP": 16, "BA": 417, "CE": 184,
    "DF": 1,  "ES": 78,  "GO": 246,"MA": 217,"MG": 853,"MS": 79,
    "MT": 142,"PA": 144,"PB": 223,"PE": 185,"PI": 224,"PR": 399,
    "RJ": 92, "RN": 167,"RO": 52, "RR": 15, "RS": 497,"SC": 295,
    "SE": 75, "SP": 645,"TO": 139
}

FASES = {
    "FASE_1_NORTE":      ["AC","AM","AP","PA","RO","RR","TO"],
    "FASE_2_NORDESTE":   ["AL","BA","CE","MA","PB","PE","PI","RN","SE"],
    "FASE_3_SUDESTE_SUL":["ES","MG","RJ","SP","PR","RS","SC"],
    "FASE_4_CO":         ["DF","GO","MS","MT"],
}

def normalize_name(nome: str) -> str:
    """Remove acentos, maiúsculas, caracteres especiais. Padrão pipeline DMD."""
    nfkd = unicodedata.normalize("NFKD", nome.upper())
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9 ]", "", ascii_str).strip()

def extract_uf_from_name(full_name: str) -> str:
    """Extrai sigla UF do nome completo IBGE ex: 'Manaus - AM' -> 'AM'"""
    m = re.search(r" - ([A-Z]{2})$", full_name)
    return m.group(1) if m else "??"

def log(msg):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ─── COLETA POPULAÇÃO CENSO 2022 ──────────────────────────────────────────
def fetch_populacao_ibge():
    url = "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022?formato=json"
    log(f"Consultando SIDRA: {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    log(f"Registros retornados: {len(data)} (incl. header)")
    return data[1:]  # pular header

# ─── CONSTRUIR TABELA MESTRE ──────────────────────────────────────────────
def build_municipios_table(raw_data):
    municipios = []
    erros = []
    
    for row in raw_data:
        ibge_cod = row["D1C"]  # 7 dígitos
        nome_full = row["D1N"]  # "Município - UF"
        pop_str = row["V"]
        
        uf = extract_uf_from_name(nome_full)
        nome_limpo = nome_full.replace(f" - {uf}", "").strip()
        nome_norm = normalize_name(nome_limpo)
        
        try:
            pop = int(pop_str)
        except:
            pop = 0
            erros.append(f"Pop inválida: {ibge_cod} {nome_full}")
        
        # Determinar fase de execução
        fase = "DESCONHECIDA"
        for f, ufs in FASES.items():
            if uf in ufs:
                fase = f
                break
        
        municipios.append({
            "ibge7": ibge_cod,
            "ibge6": ibge_cod[:6],
            "nome": nome_limpo,
            "nome_norm": nome_norm,
            "uf": uf,
            "pop_2022": pop,
            "fase_pipeline": fase,
        })
    
    return municipios, erros

# ─── VALIDAÇÃO POR UF ─────────────────────────────────────────────────────
def validate_by_uf(municipios):
    contagem = {}
    for m in municipios:
        uf = m["uf"]
        contagem[uf] = contagem.get(uf, 0) + 1
    
    divergencias = []
    for uf, esperado in MUNICIPIOS_IBGE_POR_UF.items():
        obtido = contagem.get(uf, 0)
        status = "✅ OK" if obtido == esperado else f"❌ DIVERGÊNCIA (obtido={obtido})"
        divergencias.append({"uf": uf, "esperado": esperado, "obtido": obtido, "status": status})
    
    return divergencias, contagem

# ─── MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log("="*60)
    log("SCRIPT 00 — BASE IBGE MUNICÍPIOS — INÍCIO")
    log("="*60)
    
    raw = fetch_populacao_ibge()
    municipios, erros = build_municipios_table(raw)
    divergencias, contagem_uf = validate_by_uf(municipios)
    
    # Erros de população
    if erros:
        log(f"ATENÇÃO: {len(erros)} erros de população:")
        for e in erros:
            log(f"  {e}")
    
    # Validação UF
    ok_count = sum(1 for d in divergencias if "OK" in d["status"])
    err_count = len(divergencias) - ok_count
    log(f"Validação por UF: {ok_count}/27 OK | {err_count} divergências")
    
    for d in divergencias:
        if "DIVERGÊNCIA" in d["status"]:
            log(f"  UF {d['uf']}: esperado={d['esperado']}, obtido={d['obtido']}")
    
    # Gerar output JSON
    total_pop = sum(m["pop_2022"] for m in municipios)
    sha = hashlib.sha256(json.dumps(municipios, ensure_ascii=False).encode()).hexdigest()
    
    output = {
        "metadata": {
            "versao": "1.0",
            "gerado_em": datetime.datetime.now().isoformat(),
            "fonte": "IBGE SIDRA Tabela 4714 — Censo Demográfico 2022",
            "total_municipios": len(municipios),
            "total_populacao_brasil": total_pop,
            "validacao_ufs": {"ok": ok_count, "divergencias": err_count},
            "sha256": sha
        },
        "contagem_por_uf": contagem_uf,
        "divergencias_uf": [d for d in divergencias if "DIVERGÊNCIA" in d["status"]],
        "municipios": municipios
    }
    
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    log(f"✅ Arquivo salvo: {OUT_JSON}")
    log(f"   Total municípios: {len(municipios)}")
    log(f"   Pop total Brasil 2022: {total_pop:,}")
    log(f"   SHA-256: {sha[:16]}...")
    log("SCRIPT 00 — CONCLUÍDO")
