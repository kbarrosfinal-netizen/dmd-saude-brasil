#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  EMET DMD GESTÃO BRASIL — Orquestrador Pipeline v5.1                    ║
║  Script 04 — Executa toda a cadeia de coleta→normalização→dashboard    ║
║  Uso: python3 04_orquestrador.py [--dry-run] [--skip-cnes]             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import os, sys, json, logging, subprocess, argparse, time
from datetime import datetime
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"pipeline_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("orquestrador"), log_file

def run_step(script: str, label: str, log, dry_run: bool = False) -> bool:
    """Executa um script Python e retorna True se bem-sucedido."""
    script_path = Path(__file__).parent / script
    if not script_path.exists():
        log.error(f"❌ Script não encontrado: {script_path}")
        return False

    if dry_run:
        log.info(f"[DRY-RUN] Simulando: {label}")
        return True

    log.info(f"▶ Iniciando: {label}")
    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            timeout=1800  # 30 min timeout por step
        )
        elapsed = time.time() - t0
        if result.returncode == 0:
            log.info(f"✅ {label} concluído em {elapsed:.1f}s")
            return True
        else:
            log.error(f"❌ {label} falhou (exit {result.returncode}) em {elapsed:.1f}s")
            return False
    except subprocess.TimeoutExpired:
        log.error(f"⏰ {label} excedeu timeout de 30min")
        return False
    except Exception as e:
        log.error(f"❌ Erro executando {label}: {e}")
        return False

def gerar_relatorio_final(resultados: dict, log_file: Path, log) -> None:
    """Gera JSON de sumário da execução."""
    summary = {
        "pipeline_versao": "5.1",
        "executado_em":    datetime.now().isoformat(),
        "log_file":        str(log_file),
        "etapas":          resultados,
        "status_geral":    "SUCESSO" if all(resultados.values()) else
                           "PARCIAL" if any(resultados.values()) else "FALHA"
    }
    out = ROOT / "data" / "logs" / "pipeline_summary.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"📋 Sumário salvo: {out}")

    # GitHub Step Summary (se em CI)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write(f"# 🏥 EMET DMD Pipeline v5.1 — Sumário\n\n")
            f.write(f"**Status:** {summary['status_geral']}\n\n")
            f.write(f"| Etapa | Resultado |\n|---|---|\n")
            for etapa, ok in resultados.items():
                emoji = "✅" if ok else "❌"
                f.write(f"| {etapa} | {emoji} {'OK' if ok else 'FALHA'} |\n")

def main():
    parser = argparse.ArgumentParser(description="EMET DMD Pipeline Orquestrador v5.1")
    parser.add_argument("--dry-run",    action="store_true", help="Simular sem executar")
    parser.add_argument("--skip-cnes",  action="store_true", help="Pular coleta CNES")
    parser.add_argument("--skip-tabnet",action="store_true", help="Pular coleta TabNet")
    parser.add_argument("--only-dashboard", action="store_true", help="Só gerar dashboard")
    args = parser.parse_args()

    log, log_file = setup_logger()
    log.info("╔═══════════════════════════════════════════════════╗")
    log.info("║   EMET DMD GESTÃO BRASIL — Pipeline v5.1          ║")
    log.info(f"║   Execução: {datetime.now().strftime('%d/%m/%Y %H:%M')}                      ║")
    log.info("╚═══════════════════════════════════════════════════╝")

    resultados = {}

    # Etapa 1: Coletar CNES
    if not args.skip_cnes and not args.only_dashboard:
        resultados["1_coleta_cnes"] = run_step(
            "00_coletor_cnes.py", "Coleta CNES (PySUS+FTP)", log, args.dry_run
        )
    else:
        log.info("⏭ Coleta CNES ignorada")

    # Etapa 2: Coletar TabNet
    if not args.skip_tabnet and not args.only_dashboard:
        resultados["2_coleta_tabnet"] = run_step(
            "01_coletor_tabnet.py", "Coleta TabNet CAPS/SRT", log, args.dry_run
        )
    else:
        log.info("⏭ Coleta TabNet ignorada")

    # Etapa 3: Normalizar
    if not args.only_dashboard:
        resultados["3_normalizacao"] = run_step(
            "02_normalizador.py", "Normalização e Enriquecimento", log, args.dry_run
        )

    # Etapa 4: Gerar Dashboard
    resultados["4_dashboard"] = run_step(
        "03_gerar_dashboard.py", "Geração Dashboard HTML", log, args.dry_run
    )

    # Sumário
    gerar_relatorio_final(resultados, log_file, log)

    # Status final
    total = len(resultados)
    ok    = sum(1 for v in resultados.values() if v)
    log.info(f"╚═══ Pipeline concluído: {ok}/{total} etapas OK ═══╝")

    # Exit code: 0 se tudo OK ou parcial (não bloquear CI)
    sys.exit(0 if ok > 0 else 1)

if __name__ == "__main__":
    main()
