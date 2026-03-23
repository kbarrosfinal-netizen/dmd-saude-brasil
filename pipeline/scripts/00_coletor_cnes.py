#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  EMET DMD GESTÃO BRASIL — Coletor CNES v5.1                             ║
║  Script 00 — Coleta automática mensal CNES via PySUS + FTP DATASUS     ║
║  Grupos: ST (Estabelecimentos), LT (Leitos), SR (Serviços), EP (Equipes)║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import os, sys, json, logging, ftplib, gzip, io, hashlib, re
from datetime import datetime, timedelta
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cnes"
LOG_DIR  = ROOT / "data" / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

FTP_HOST  = "ftp.datasus.gov.br"
FTP_BASE  = "/dissemin/publicos/CNES/200508_/Dados"
GRUPOS    = {"ST": "Estabelecimentos", "LT": "Leitos",
             "SR": "Serviços Especializados", "EP": "Equipes"}
UFS_ALL   = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
             "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
             "RO","RR","RS","SC","SE","SP","TO"]

# ── Logging ────────────────────────────────────────────────────────────
def setup_logger(comp: str) -> logging.Logger:
    log_file = LOG_DIR / f"cnes_{comp}.log"
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO, format=fmt,
        handlers=[logging.FileHandler(log_file, encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("cnes_coletor")

# ── Competência: mês anterior ──────────────────────────────────────────
def get_competencia(offset: int = 1) -> tuple:
    hoje  = datetime.today()
    tgt   = (hoje.replace(day=1) - timedelta(days=offset * 28))
    return tgt.year, tgt.month, f"{tgt.year}{tgt.month:02d}"

# ── Método 1: PySUS ────────────────────────────────────────────────────
def coletar_pysus(ano: int, mes: int, grupos: list, ufs: list,
                  log: logging.Logger) -> dict:
    try:
        from pysus.online_data.CNES import CNES
        import pandas as pd
    except ImportError:
        log.warning("PySUS não instalado — tentando FTP direto")
        return {}

    resultados = {}
    cnes = CNES()
    for grupo in grupos:
        log.info(f"[PySUS] Baixando grupo {grupo} ({GRUPOS.get(grupo,'?')})...")
        try:
            cnes.load(grupo)
            files = cnes.get_files(grupo, uf=ufs, year=ano, month=mes)
            if not files:
                log.warning(f"  Nenhum arquivo disponível para {grupo} {ano}/{mes:02d}")
                continue
            parquets = cnes.download(files)
            dfs = []
            for pq in parquets:
                try:
                    df = pd.read_parquet(pq)
                    dfs.append(df)
                except Exception as e:
                    log.warning(f"  Erro lendo parquet {pq}: {e}")
            if dfs:
                df_merged = pd.concat(dfs, ignore_index=True)
                out_path = DATA_DIR / f"CNES_{grupo}_{ano}{mes:02d}.parquet"
                df_merged.to_parquet(out_path, index=False)
                resultados[grupo] = {"path": str(out_path),
                                     "rows": len(df_merged),
                                     "cols": len(df_merged.columns)}
                log.info(f"  ✅ {grupo}: {len(df_merged):,} registros → {out_path.name}")
        except Exception as e:
            log.error(f"  ❌ Falha PySUS grupo {grupo}: {e}")

    return resultados

# ── Método 2: FTP Direto ───────────────────────────────────────────────
def coletar_ftp(ano: int, mes: int, grupos: list, ufs: list,
                log: logging.Logger) -> dict:
    resultados = {}
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=60)
        ftp.login()
        log.info(f"[FTP] Conectado a {FTP_HOST}")
    except Exception as e:
        log.error(f"Falha ao conectar FTP: {e}")
        return {}

    for grupo in grupos:
        grupo_dir = f"{FTP_BASE}/{grupo}"
        try:
            ftp.cwd(grupo_dir)
            files = ftp.nlst()
            # Filtrar arquivos do mês/ano e UFs desejadas
            # Padrão: {GRUPO}{UF}{AAMM}.dbc  ex: STAC2602.dbc
            aamm = f"{str(ano)[2:]}{mes:02d}"
            targets = []
            for fn in files:
                fn_up = fn.upper()
                # Verificar se bate com alguma UF
                for uf in ufs:
                    padrao = f"{grupo}{uf}{aamm}"
                    if padrao in fn_up:
                        targets.append(fn)
                        break

            if not targets:
                log.warning(f"  Nenhum arquivo FTP para {grupo} {aamm}")
                continue

            downloaded = []
            for fn in targets:
                local = DATA_DIR / fn
                if local.exists():
                    log.info(f"  Cache: {fn}")
                    downloaded.append(str(local))
                    continue
                try:
                    buf = io.BytesIO()
                    ftp.retrbinary(f"RETR {fn}", buf.write)
                    buf.seek(0)
                    with open(local, "wb") as f:
                        f.write(buf.read())
                    downloaded.append(str(local))
                    log.info(f"  ✅ {fn} ({local.stat().st_size/1024:.1f} KB)")
                except Exception as e:
                    log.warning(f"  ⚠️ Erro baixando {fn}: {e}")

            resultados[grupo] = {"files": downloaded, "count": len(downloaded)}

        except ftplib.error_perm as e:
            log.warning(f"  Pasta FTP não encontrada: {grupo_dir} — {e}")
        except Exception as e:
            log.error(f"  Erro FTP grupo {grupo}: {e}")

    try:
        ftp.quit()
    except Exception:
        pass

    return resultados

# ── Converter DBC → JSON resumo (sem dbf2pd para evitar dep extra) ─────
def resumir_coleta(resultados_pysus: dict, resultados_ftp: dict,
                   comp_str: str, log: logging.Logger) -> Path:
    """Gera um JSON de resumo da coleta para uso pelo normalizador."""
    summary = {
        "competencia": comp_str,
        "gerado_em":   datetime.now().isoformat(),
        "metodo":      "pysus" if resultados_pysus else "ftp",
        "grupos":      {}
    }

    for grupo, info in (resultados_pysus or resultados_ftp).items():
        summary["grupos"][grupo] = info

    out = DATA_DIR / f"coleta_resumo_{comp_str}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info(f"📋 Resumo de coleta salvo: {out}")
    return out

# ── Main ───────────────────────────────────────────────────────────────
def main():
    ano, mes, comp_str = get_competencia()
    log = setup_logger(comp_str)
    log.info(f"╔══ EMET DMD — Coleta CNES Competência {ano}/{mes:02d} ══╗")

    grupos = list(GRUPOS.keys())
    ufs    = UFS_ALL

    # Tentar PySUS primeiro
    res_pysus = coletar_pysus(ano, mes, grupos, ufs, log)

    # Fallback FTP se PySUS falhar ou retornar vazio
    res_ftp = {}
    if len(res_pysus) < len(grupos):
        faltantes = [g for g in grupos if g not in res_pysus]
        log.info(f"[FTP Fallback] grupos sem PySUS: {faltantes}")
        res_ftp = coletar_ftp(ano, mes, faltantes, ufs, log)

    # Resumo
    resumo_path = resumir_coleta(res_pysus, res_ftp, comp_str, log)

    total_grupos = len(res_pysus) + len(res_ftp)
    log.info(f"╚══ Coleta concluída: {total_grupos}/{len(grupos)} grupos | {resumo_path} ══╝")

    # Exit code 0 mesmo se parcial (não bloquear o pipeline)
    sys.exit(0)

if __name__ == "__main__":
    main()
