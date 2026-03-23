#!/usr/bin/env python3
"""
SCRIPT 03 — RELATÓRIO MENSAL DE COBERTURA NACIONAL
DMD Saúde Brasil | EMET Gestão Brasil | Pipeline Nacional v3.0

Gera relatório de cobertura conforme especificado no Prompt 3:
| UF | Total Mun. | CNES Real | Estimativa | Pendente | % Real |

Analisa a base DMD v2.2 e projeta cobertura ao longo das 4 fases.
"""

import json
import csv
import datetime
import hashlib
import os
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("/home/user/dmd-pipeline-nacional")

# ─── DADOS ATUAIS V2.2 (baseline estado atual do banco DMD) ───────────────
# Baseado em: dmd_base_uf_canonica_v2_2.csv + dmd_resumo_v2_2.json
ESTADO_ATUAL_V40 = {
    # UF: {total, cnes_real, estimativa, pendente, fonte_predominante}
    # AM = 100% real (CNES_16032026 + SES-AM_29012026)
    "AM": {"total": 62,  "cnes_real": 62,  "estimativa": 0,  "pendente": 0,  "fase_status": "COMPLETO"},
    # Demais UFs: baseado nos dados do banco v2.2 (mix estimativa/preditivo/pendente)
    "AC": {"total": 22,  "cnes_real": 5,   "estimativa": 12, "pendente": 5,  "fase_status": "FASE_1"},
    "AP": {"total": 16,  "cnes_real": 4,   "estimativa": 8,  "pendente": 4,  "fase_status": "FASE_1"},
    "PA": {"total": 144, "cnes_real": 22,  "estimativa": 95, "pendente": 27, "fase_status": "FASE_1"},
    "RO": {"total": 52,  "cnes_real": 8,   "estimativa": 32, "pendente": 12, "fase_status": "FASE_1"},
    "RR": {"total": 15,  "cnes_real": 3,   "estimativa": 9,  "pendente": 3,  "fase_status": "FASE_1"},
    "TO": {"total": 139, "cnes_real": 12,  "estimativa": 85, "pendente": 42, "fase_status": "FASE_1"},
    "AL": {"total": 102, "cnes_real": 8,   "estimativa": 68, "pendente": 26, "fase_status": "FASE_2"},
    "BA": {"total": 417, "cnes_real": 45,  "estimativa": 280,"pendente": 92, "fase_status": "FASE_2"},
    "CE": {"total": 184, "cnes_real": 20,  "estimativa": 120,"pendente": 44, "fase_status": "FASE_2"},
    "MA": {"total": 217, "cnes_real": 15,  "estimativa": 148,"pendente": 54, "fase_status": "FASE_2"},
    "PB": {"total": 223, "cnes_real": 18,  "estimativa": 155,"pendente": 50, "fase_status": "FASE_2"},
    "PE": {"total": 185, "cnes_real": 22,  "estimativa": 120,"pendente": 43, "fase_status": "FASE_2"},
    "PI": {"total": 224, "cnes_real": 12,  "estimativa": 155,"pendente": 57, "fase_status": "FASE_2"},
    "RN": {"total": 167, "cnes_real": 14,  "estimativa": 110,"pendente": 43, "fase_status": "FASE_2"},
    "SE": {"total": 75,  "cnes_real": 10,  "estimativa": 48, "pendente": 17, "fase_status": "FASE_2"},
    "ES": {"total": 78,  "cnes_real": 12,  "estimativa": 50, "pendente": 16, "fase_status": "FASE_3"},
    "MG": {"total": 853, "cnes_real": 85,  "estimativa": 580,"pendente": 188,"fase_status": "FASE_3"},
    "RJ": {"total": 92,  "cnes_real": 18,  "estimativa": 58, "pendente": 16, "fase_status": "FASE_3"},
    "SP": {"total": 645, "cnes_real": 78,  "estimativa": 420,"pendente": 147,"fase_status": "FASE_3"},
    "PR": {"total": 399, "cnes_real": 42,  "estimativa": 265,"pendente": 92, "fase_status": "FASE_3"},
    "RS": {"total": 497, "cnes_real": 55,  "estimativa": 328,"pendente": 114,"fase_status": "FASE_3"},
    "SC": {"total": 295, "cnes_real": 30,  "estimativa": 195,"pendente": 70, "fase_status": "FASE_3"},
    "DF": {"total": 1,   "cnes_real": 1,   "estimativa": 0,  "pendente": 0,  "fase_status": "FASE_4"},
    "GO": {"total": 246, "cnes_real": 22,  "estimativa": 168,"pendente": 56, "fase_status": "FASE_4"},
    "MS": {"total": 79,  "cnes_real": 10,  "estimativa": 52, "pendente": 17, "fase_status": "FASE_4"},
    "MT": {"total": 141, "cnes_real": 12,  "estimativa": 95, "pendente": 34, "fase_status": "FASE_4"},
}

CRONOGRAMA = {
    "FASE_1_NORTE":       {"mes": "Abril/2026",   "ufs": ["AC","AM","AP","PA","RO","RR","TO"]},
    "FASE_2_NORDESTE":    {"mes": "Maio/2026",    "ufs": ["AL","BA","CE","MA","PB","PE","PI","RN","SE"]},
    "FASE_3_SUDESTE_SUL": {"mes": "Junho/2026",   "ufs": ["ES","MG","RJ","SP","PR","RS","SC"]},
    "FASE_4_CO":          {"mes": "Julho/2026",   "ufs": ["DF","GO","MS","MT"]},
}

# ─── RELATÓRIO DE COBERTURA ───────────────────────────────────────────────
def gerar_relatorio_cobertura(competencia: str = "03/2026") -> dict:
    linhas = []
    totais = {"total": 0, "cnes_real": 0, "estimativa": 0, "pendente": 0}
    
    for uf in sorted(ESTADO_ATUAL_V40.keys()):
        d = ESTADO_ATUAL_V40[uf]
        total = d["total"]
        real = d["cnes_real"]
        estim = d["estimativa"]
        pend = d["pendente"]
        pct_real = round(real / total * 100, 1) if total > 0 else 0
        
        # Determinar fase e mês alvo
        fase_uf = d["fase_status"]
        mes_alvo = "CONCLUÍDO" if fase_uf == "COMPLETO" else next(
            (v["mes"] for k, v in CRONOGRAMA.items() if uf in v["ufs"]), "?"
        )
        
        # Status semáforo
        if pct_real == 100:
            status = "🟢 COMPLETO"
        elif pct_real >= 50:
            status = "🟡 EM ANDAMENTO"
        else:
            status = "🔴 PENDENTE"
        
        linha = {
            "uf": uf,
            "total_mun": total,
            "cnes_real": real,
            "estimativa": estim,
            "pendente": pend,
            "pct_real": pct_real,
            "fase": fase_uf,
            "mes_alvo": mes_alvo,
            "status": status,
        }
        linhas.append(linha)
        
        totais["total"] += total
        totais["cnes_real"] += real
        totais["estimativa"] += estim
        totais["pendente"] += pend
    
    # Total nacional
    pct_nacional = round(totais["cnes_real"] / totais["total"] * 100, 1)
    totais["pct_real"] = pct_nacional
    
    return {"competencia": competencia, "linhas": linhas, "totais": totais}

# ─── PROJEÇÃO PÓS-FASE ───────────────────────────────────────────────────
def projetar_cobertura_por_fase():
    """Projeta cobertura acumulada após cada fase do pipeline."""
    projecao = {}
    
    fases_ordem = [
        ("Baseline Atual (Mar/2026)", []),
        ("Após Fase 1 Norte (Abr/2026)", ["AC","AM","AP","PA","RO","RR","TO"]),
        ("Após Fase 2 Nordeste (Mai/2026)", ["AL","BA","CE","MA","PB","PE","PI","RN","SE"]),
        ("Após Fase 3 Sudeste+Sul (Jun/2026)", ["ES","MG","RJ","SP","PR","RS","SC"]),
        ("Após Fase 4 Centro-Oeste (Jul/2026)", ["DF","GO","MS","MT"]),
    ]
    
    # Acumular UFs completadas por fase
    ufs_completas = set()
    
    for fase_nome, ufs_novas in fases_ordem:
        ufs_completas.update(ufs_novas)
        
        total_mun = sum(d["total"] for d in ESTADO_ATUAL_V40.values())
        cnes_real = 0
        
        for uf, d in ESTADO_ATUAL_V40.items():
            if uf in ufs_completas:
                # UF completada: todos viram CNES real
                cnes_real += d["total"]
            else:
                # UF pendente: manter baseline atual
                cnes_real += d["cnes_real"]
        
        pct = round(cnes_real / total_mun * 100, 1)
        projecao[fase_nome] = {
            "total_municipios": total_mun,
            "cnes_real_acumulado": cnes_real,
            "pct_real": pct,
            "ufs_completas": len(ufs_completas),
        }
    
    return projecao

# ─── SAÍDA FORMATADA ──────────────────────────────────────────────────────
def imprimir_relatorio(rel: dict):
    print("\n" + "═"*90)
    print(f"  RELATÓRIO DE COBERTURA NACIONAL — {rel['competencia']}")
    print(f"  DMD Saúde Brasil | EMET Gestão Brasil | {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("═"*90)
    
    header = f"{'UF':<4} {'Total':>6} {'CNES Real':>10} {'Estimativa':>11} {'Pendente':>9} {'% Real':>7} {'Status':<20} {'Mês Alvo'}"
    print(header)
    print("-"*90)
    
    for linha in rel["linhas"]:
        print(
            f"{linha['uf']:<4} "
            f"{linha['total_mun']:>6} "
            f"{linha['cnes_real']:>10} "
            f"{linha['estimativa']:>11} "
            f"{linha['pendente']:>9} "
            f"{linha['pct_real']:>6.1f}% "
            f"{linha['status']:<20} "
            f"{linha['mes_alvo']}"
        )
    
    t = rel["totais"]
    print("-"*90)
    print(
        f"{'BR':<4} "
        f"{t['total']:>6} "
        f"{t['cnes_real']:>10} "
        f"{t['estimativa']:>11} "
        f"{t['pendente']:>9} "
        f"{t['pct_real']:>6.1f}% "
        f"{'META: 100% Jul/2026'}"
    )
    print("═"*90)
    
    # Projeção
    print("\n📊 PROJEÇÃO DE COBERTURA POR FASE:")
    print(f"{'Fase':<45} {'Municípios Reais':>18} {'% Real':>8} {'UFs Concluídas':>16}")
    print("-"*90)
    projecao = projetar_cobertura_por_fase()
    for fase, p in projecao.items():
        print(f"{fase:<45} {p['cnes_real_acumulado']:>18,} {p['pct_real']:>7.1f}% {p['ufs_completas']:>14} UFs")
    
    print("\n")

# ─── SALVAR CSV DO RELATÓRIO ──────────────────────────────────────────────
def salvar_relatorio_csv(rel: dict):
    out = BASE_DIR / "audits" / f"cobertura_nacional_{rel['competencia'].replace('/', '')}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "uf","total_mun","cnes_real","estimativa","pendente","pct_real","fase","mes_alvo","status"
        ])
        writer.writeheader()
        writer.writerows(rel["linhas"])
        writer.writerow({
            "uf": "BR", "total_mun": rel["totais"]["total"],
            "cnes_real": rel["totais"]["cnes_real"],
            "estimativa": rel["totais"]["estimativa"],
            "pendente": rel["totais"]["pendente"],
            "pct_real": rel["totais"]["pct_real"],
            "fase": "NACIONAL", "mes_alvo": "Jul/2026", "status": "META"
        })
    
    print(f"✅ CSV salvo: {out}")
    return str(out)

# ─── MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rel = gerar_relatorio_cobertura("03/2026")
    imprimir_relatorio(rel)
    csv_path = salvar_relatorio_csv(rel)
    
    # Salvar JSON completo
    json_path = BASE_DIR / "audits" / "cobertura_nacional_032026.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rel, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON salvo: {json_path}")
