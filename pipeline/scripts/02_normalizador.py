#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  EMET DMD GESTÃO BRASIL — Normalizador v5.1                             ║
║  Script 02 — Integra dados CNES/TabNet ao banco DMD v37                ║
║  Output: dashboard_data.json + dmd_atualizado.csv                      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import os, sys, json, logging, re
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
DATA_DIR  = ROOT / "data"
CNES_DIR  = DATA_DIR / "cnes"
TABNET_DIR= DATA_DIR / "tabnet"
OUT_DIR   = DATA_DIR
LOG_DIR   = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────
def setup_logger() -> logging.Logger:
    log_file = LOG_DIR / f"normalizador_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("normalizador")

# ── Carregar base DMD v37 ──────────────────────────────────────────────
def carregar_base_dmd(log: logging.Logger) -> list:
    """Carrega a base DMD canônica do Excel v37 como lista de dicionários."""
    try:
        import pandas as pd

        # Procurar o arquivo DMD v37
        caminhos = [
            Path("/home/user/dmd-upload/DMD_Gestao_Dados_Saude_v37_Completo.xlsx"),
            DATA_DIR / "DMD_Gestao_Dados_Saude_v37_Completo.xlsx",
            Path("/mnt/user-data/outputs/dmd-pipeline-nacional/dmd_v37.xlsx"),
        ]
        xlsx = None
        for c in caminhos:
            if c.exists():
                xlsx = c
                break

        if xlsx is None:
            log.warning("Base DMD v37 não encontrada — usando dados sintéticos mínimos")
            return []

        df = pd.read_excel(xlsx, sheet_name="BANCO_COMPLETO", dtype=str)
        df = df.fillna("")
        registros = df.to_dict("records")
        log.info(f"✅ Base DMD v37 carregada: {len(registros):,} municípios, {len(df.columns)} colunas")
        return registros

    except Exception as e:
        log.error(f"Erro carregando base DMD: {e}")
        return []

# ── Carregar resumo CNES recente ───────────────────────────────────────
def carregar_resumo_cnes(log: logging.Logger) -> dict:
    """Lê o arquivo coleta_resumo_*.json mais recente."""
    arquivos = sorted(CNES_DIR.glob("coleta_resumo_*.json"), reverse=True)
    if not arquivos:
        log.warning("Nenhum resumo CNES encontrado")
        return {}
    with open(arquivos[0]) as f:
        data = json.load(f)
    log.info(f"Resumo CNES carregado: {arquivos[0].name} ({data.get('competencia','?')})")
    return data

# ── Carregar CAPS TabNet ────────────────────────────────────────────────
def carregar_caps_tabnet(log: logging.Logger) -> dict:
    """Lê o arquivo caps_tabnet_*.json mais recente."""
    arquivos = sorted(TABNET_DIR.glob("caps_tabnet_*.json"), reverse=True)
    if not arquivos:
        log.warning("Nenhum arquivo CAPS TabNet encontrado")
        return {}
    with open(arquivos[0]) as f:
        data = json.load(f)
    # Indexar por código IBGE
    idx = {}
    for r in data.get("registros", []):
        cod = str(r.get("codigo_ibge", "")).strip()[:6]
        if cod:
            idx[cod] = r
    log.info(f"CAPS TabNet indexados: {len(idx)} municípios")
    return idx

# ── Enriquecer registros DMD com dados novos ───────────────────────────
def enriquecer(registros: list, caps_idx: dict, resumo_cnes: dict,
               log: logging.Logger) -> list:
    """Atualiza campos CAPS, leitos, cobertura com dados recentes."""
    comp = resumo_cnes.get("competencia", datetime.now().strftime("%Y%m"))
    fonte_label = f"CNES_{comp}"
    atualizados = 0
    sem_match   = 0

    for rec in registros:
        # Código IBGE (7 dígitos no banco, 6 para matching)
        cod7 = str(rec.get("m", "")).strip()
        cod6 = cod7[:6] if len(cod7) >= 6 else cod7

        # Tentar atualizar CAPS com dados TabNet
        if cod6 in caps_idx:
            caps_data = caps_idx[cod6]
            caps_novo = caps_data.get("caps_total", 0)
            caps_atual = int(rec.get("caps", 0) or 0)
            if caps_novo != caps_atual and caps_novo > 0:
                rec["caps"]      = caps_novo
                rec["fonte_sm"]  = fonte_label
                rec["ultima_atualizacao"] = datetime.now().isoformat()
                atualizados += 1
        else:
            sem_match += 1

        # Atualizar fonte se há dados CNES novos
        if resumo_cnes.get("grupos"):
            grupos_ok = list(resumo_cnes["grupos"].keys())
            if "LT" in grupos_ok and rec.get("leitos_hg", "") == "":
                rec["leitos_hg"]  = "0"
            if not rec.get("obs_raps"):
                rec["obs_raps"] = f"Dados {fonte_label}"

    log.info(f"Enriquecimento: {atualizados} registros atualizados, {sem_match} sem match TabNet")
    return registros

# ── Gerar dashboard_data.json ──────────────────────────────────────────
def gerar_dashboard_json(registros: list, log: logging.Logger) -> Path:
    """Serializa os registros para o JSON consumido pelo dashboard v5."""
    # Agregar por UF
    from collections import defaultdict
    ufs = defaultdict(lambda: {
        "municipios": 0, "pop": 0, "caps": 0, "srt": 0,
        "leitos_sus": 0, "alertas_fiscais": 0, "score_soma": 0.0
    })

    for rec in registros:
        uf = str(rec.get("uf", "??")).strip()
        try:
            ufs[uf]["municipios"] += 1
            ufs[uf]["pop"]        += int(float(rec.get("pop", 0) or 0))
            ufs[uf]["caps"]       += int(float(rec.get("caps", 0) or 0))
            ufs[uf]["srt"]        += int(float(rec.get("srt", 0) or 0))
            ufs[uf]["leitos_sus"] += int(float(rec.get("leitos_total", 0) or 0))
            if str(rec.get("crit", "")).upper() in ("ALTO", "CRÍTICO", "CRITICO"):
                ufs[uf]["alertas_fiscais"] += 1
            sc = float(rec.get("score_v3", rec.get("l", 0)) or 0)
            ufs[uf]["score_soma"] += sc
        except (ValueError, TypeError):
            continue

    ufs_list = []
    for uf, d in sorted(ufs.items()):
        n = d["municipios"] or 1
        ufs_list.append({
            "uf": uf, "municipios": n, "pop": d["pop"],
            "caps": d["caps"], "srt": d["srt"],
            "leitos_sus": d["leitos_sus"],
            "alertas_fiscais": d["alertas_fiscais"],
            "score_medio": round(d["score_soma"] / n, 1)
        })

    dashboard = {
        "meta": {
            "versao": "5.1",
            "gerado_em": datetime.now().isoformat(),
            "total_municipios": len(registros),
            "fonte": "DMD_v37 + CNES_DATASUS"
        },
        "kpis": {
            "total_municipios": len(registros),
            "populacao_total":  sum(d["pop"] for d in ufs.values()),
            "total_caps":       sum(d["caps"] for d in ufs.values()),
            "total_srt":        sum(d["srt"] for d in ufs.values()),
            "total_leitos_sus": sum(d["leitos_sus"] for d in ufs.values()),
            "total_alertas":    sum(d["alertas_fiscais"] for d in ufs.values()),
        },
        "ufs": ufs_list,
        "municipios_sample": registros[:100]  # Primeiros 100 para preview
    }

    out = OUT_DIR / "dashboard_data.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)
    log.info(f"✅ dashboard_data.json gerado: {out} ({out.stat().st_size/1024:.1f} KB)")
    return out

# ── Main ────────────────────────────────────────────────────────────────
def main():
    log = setup_logger()
    log.info("╔══ EMET DMD — Normalizador v5.1 ══╗")

    registros     = carregar_base_dmd(log)
    resumo_cnes   = carregar_resumo_cnes(log)
    caps_idx      = carregar_caps_tabnet(log)

    if registros:
        registros = enriquecer(registros, caps_idx, resumo_cnes, log)
        out_json  = gerar_dashboard_json(registros, log)
        log.info(f"╚══ Normalização concluída → {out_json} ══╝")
    else:
        log.warning("Base DMD vazia — gerando JSON mínimo de placeholder")
        placeholder = {"meta": {"versao": "5.1", "status": "sem_dados"},
                       "kpis": {}, "ufs": []}
        out = OUT_DIR / "dashboard_data.json"
        with open(out, "w") as f:
            json.dump(placeholder, f)

    sys.exit(0)

if __name__ == "__main__":
    main()
