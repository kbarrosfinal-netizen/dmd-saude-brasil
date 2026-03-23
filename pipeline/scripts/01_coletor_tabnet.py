#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  EMET DMD GESTÃO BRASIL — Coletor TabNet v5.1                           ║
║  Script 01 — Scraping TabNet para CAPS, SRT e cobertura RAPS por município║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import os, sys, json, logging, time, requests
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "tabnet"
LOG_DIR  = ROOT / "data" / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe"
TIMEOUT    = 60

# ── Logging ────────────────────────────────────────────────────────────
def setup_logger() -> logging.Logger:
    log_file = LOG_DIR / f"tabnet_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("tabnet_coletor")

# ── Query CAPS por município ────────────────────────────────────────────
CAPS_QUERY = {
    "Linha":   "Município",
    "Coluna":  "Tipo_CAPS",
    "Medida":  "Quantidade_aprovada",
    "Arquivos": "cnesxml",
    "pesqmes1": "",
    "SMunic":  "TODAS_AS_CATEGORIAS__",
    "SEstado": "TODAS_AS_CATEGORIAS__",
    "zeronulos": "1",
    "formato": "table",
}

# ── Requisição TabNet ───────────────────────────────────────────────────
def query_tabnet(params: dict, descricao: str,
                 log: logging.Logger) -> list[dict]:
    """Envia POST ao TabNet e parseia a tabela HTML retornada."""
    try:
        resp = requests.post(TABNET_URL, data=params, timeout=TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        # Parse da tabela HTML básico (sem BeautifulSoup)
        rows = []
        in_table = False
        for line in html.split("\n"):
            line = line.strip()
            if "<table" in line.lower():
                in_table = True
            if not in_table:
                continue
            if "<tr" in line.lower():
                # Extrair células
                cells = []
                import re
                tds = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", line, re.I | re.S)
                for td in tds:
                    # Limpar HTML
                    text = re.sub(r"<[^>]+>", "", td).strip()
                    cells.append(text)
                if cells and len(cells) >= 2:
                    rows.append(cells)
            if "</table>" in line.lower():
                break

        log.info(f"  {descricao}: {len(rows)} linhas coletadas do TabNet")
        return rows

    except requests.exceptions.ConnectionError:
        log.warning(f"  TabNet inacessível (possível bloqueio de rede em CI): {descricao}")
        return []
    except Exception as e:
        log.error(f"  Erro TabNet {descricao}: {e}")
        return []

# ── Coletar CAPS ────────────────────────────────────────────────────────
def coletar_caps(log: logging.Logger) -> Path:
    log.info("[TabNet] Coletando CAPS por município...")
    rows = query_tabnet(CAPS_QUERY, "CAPS", log)

    data = {"fonte": "TabNet_CNES", "coletado_em": datetime.now().isoformat(), "registros": []}
    for row in rows[1:]:  # pular cabeçalho
        try:
            mun_code = row[0].split()[0] if row[0] else ""
            mun_name = " ".join(row[0].split()[1:]) if row[0] else ""
            data["registros"].append({
                "codigo_ibge": mun_code,
                "municipio":   mun_name,
                "caps_total":  int(row[-1].replace(".", "").replace(",", "")) if row[-1].isdigit() else 0,
                "raw":         row
            })
        except (IndexError, ValueError):
            continue

    out = DATA_DIR / f"caps_tabnet_{datetime.now().strftime('%Y%m')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"  ✅ CAPS salvo: {out} ({len(data['registros'])} registros)")
    return out

# ── Fallback: usar dados locais se TabNet indisponível ─────────────────
def usar_fallback(log: logging.Logger) -> dict:
    """Se TabNet falhar, usar base DMD v37 já existente como referência."""
    fallback_paths = [
        ROOT / "data" / "dmd_v37_base.json",
        Path("/home/user/dmd-upload/DMD_Gestao_Dados_Saude_v37_Completo.xlsx"),
    ]
    for p in fallback_paths:
        if p.exists():
            log.info(f"  Fallback: usando {p}")
            return {"fallback": str(p), "status": "ok"}
    log.warning("  Nenhum fallback disponível — continuando sem dados TabNet")
    return {"fallback": None, "status": "sem_dados"}

# ── Main ────────────────────────────────────────────────────────────────
def main():
    log = setup_logger()
    log.info("╔══ EMET DMD — Coleta TabNet CAPS/SRT ══╗")

    caps_path = coletar_caps(log)

    if not caps_path.exists() or caps_path.stat().st_size < 100:
        log.warning("Arquivo CAPS vazio ou ausente — ativando fallback")
        fb = usar_fallback(log)
        result = {"status": "fallback", "info": fb}
    else:
        result = {"status": "ok", "caps_file": str(caps_path)}

    # Salvar status
    status_file = LOG_DIR / "tabnet_status.json"
    with open(status_file, "w") as f:
        json.dump({**result, "timestamp": datetime.now().isoformat()}, f, indent=2)

    log.info(f"╚══ Coleta TabNet concluída: {result['status']} ══╝")
    sys.exit(0)

if __name__ == "__main__":
    main()
