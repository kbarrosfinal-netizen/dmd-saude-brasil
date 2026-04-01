#!/usr/bin/env python3
"""
DMD Saude Brasil — Ingestao mensal de patch CNES no Supabase PostgreSQL.

Recebe um JSON de patch (gerado pelo cnes_scraper.py) e faz UPSERT
nas tabelas saude_mental e leitos do banco Supabase.

Uso:
    export SUPABASE_HOST="db.xxckbdilszvfmzyoquze.supabase.co"
    export SUPABASE_PASSWORD="..."
    python load_patch_to_supabase.py --patch cnes_data/cnes_patch_032026.json
"""

import argparse
import json
import os
import sys
import time

try:
    import psycopg2
except ImportError:
    print("ERRO: psycopg2 nao instalado. Rode: pip install psycopg2-binary")
    sys.exit(1)


def conectar():
    """Conecta ao Supabase PostgreSQL via variaveis de ambiente."""
    host = os.environ.get("SUPABASE_HOST", "db.xxckbdilszvfmzyoquze.supabase.co")
    port = int(os.environ.get("SUPABASE_PORT", "5432"))
    dbname = os.environ.get("SUPABASE_DB", "postgres")
    user = os.environ.get("SUPABASE_USER", "postgres")
    password = os.environ.get("SUPABASE_PASSWORD")

    if not password:
        print("ERRO: variavel SUPABASE_PASSWORD nao definida.")
        sys.exit(1)

    for tentativa in range(2):
        try:
            conn = psycopg2.connect(
                host=host, port=port, dbname=dbname,
                user=user, password=password,
                connect_timeout=15,
            )
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as e:
            if tentativa == 0:
                print(f"  Conexao falhou, tentando novamente em 5s... ({e})")
                time.sleep(5)
            else:
                print(f"ERRO: impossivel conectar ao banco: {e}")
                sys.exit(1)


def obter_competencia(cur, conn, mes, ano, fonte_sigla="CNES", versao="V43"):
    """Cria ou reutiliza uma competencia. Retorna o ID."""
    # Buscar fonte_id
    cur.execute("SELECT id FROM fontes WHERE sigla = %s;", (fonte_sigla,))
    row = cur.fetchone()
    fonte_id = row[0] if row else 1

    referencia = f"{mes:02d}/{ano}"
    cur.execute("""
        INSERT INTO competencias (ano, mes, referencia, fonte_id, versao_banco)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (ano, mes, fonte_id)
        DO UPDATE SET versao_banco = EXCLUDED.versao_banco
        RETURNING id;
    """, (ano, mes, referencia, fonte_id, versao))
    comp_id = cur.fetchone()[0]
    conn.commit()
    return comp_id


def processar_municipio(cur, comp_id, m):
    """Faz UPSERT de um municipio nas tabelas saude_mental e leitos."""
    ibge = str(m.get("ibge", m.get("ibge_cod", ""))).strip()
    if "." in ibge:
        ibge = ibge.split(".")[0]
    if not ibge or not ibge.isdigit() or len(ibge) < 6:
        return False, f"IBGE invalido: {m.get('m', '?')}"
    ibge = ibge.zfill(7)

    # Verificar se municipio existe
    cur.execute("SELECT 1 FROM municipios WHERE ibge = %s;", (ibge,))
    if not cur.fetchone():
        return False, f"IBGE {ibge} ({m.get('m', '?')}) nao existe no banco"

    # --- UPSERT saude_mental ---
    cob_raps = m.get("cobertura_raps", "")
    is_raps = cob_raps in ("SIM", True, "true")
    is_alerta = m.get("alerta_fiscal", False) is True

    cur.execute("""
        INSERT INTO saude_mental (
            municipio_ibge, competencia_id,
            caps_total, caps_tipo, caps_nomes, srt, leitos_psiq_hg,
            psiq_cadastrados, psiq_habilitados, status_habilitacao,
            cobertura_raps, alerta_fiscal, nota_habilitacao, fonte
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (municipio_ibge, competencia_id) DO UPDATE SET
            caps_total = EXCLUDED.caps_total,
            caps_tipo = EXCLUDED.caps_tipo,
            caps_nomes = EXCLUDED.caps_nomes,
            srt = EXCLUDED.srt,
            leitos_psiq_hg = EXCLUDED.leitos_psiq_hg,
            psiq_cadastrados = EXCLUDED.psiq_cadastrados,
            psiq_habilitados = EXCLUDED.psiq_habilitados,
            status_habilitacao = EXCLUDED.status_habilitacao,
            cobertura_raps = EXCLUDED.cobertura_raps,
            alerta_fiscal = EXCLUDED.alerta_fiscal,
            nota_habilitacao = EXCLUDED.nota_habilitacao,
            fonte = EXCLUDED.fonte;
    """, (
        ibge, comp_id,
        m.get("caps", 0) or 0,
        m.get("caps_tipo", ""),
        m.get("caps_nomes", ""),
        m.get("srt", 0) or 0,
        m.get("psiq_hg", m.get("leitos_hg", 0)) or 0,
        m.get("psiq_cad", 0) or 0,
        m.get("psiq_hab", 0) or 0,
        m.get("psiq_status", ""),
        is_raps,
        is_alerta,
        m.get("nota_habilitacao", ""),
        m.get("fonte_sm", "CNES"),
    ))

    # --- UPSERT leitos (psiquiatricos) se houver dados ---
    leitos_hg = m.get("leitos_hg", m.get("psiq_hg", None))
    if leitos_hg is not None:
        cur.execute("""
            INSERT INTO leitos (
                municipio_ibge, competencia_id,
                leitos_psiquiatricos, fonte, imputado
            ) VALUES (%s, %s, %s, 'CNES', FALSE)
            ON CONFLICT (municipio_ibge, competencia_id) DO UPDATE SET
                leitos_psiquiatricos = EXCLUDED.leitos_psiquiatricos;
        """, (ibge, comp_id, int(leitos_hg) if leitos_hg else 0))

    return True, None


def main():
    parser = argparse.ArgumentParser(
        description="Carrega patch CNES no Supabase PostgreSQL"
    )
    parser.add_argument(
        "--patch", required=True,
        help="Caminho do arquivo JSON de patch (ex: cnes_data/cnes_patch_032026.json)"
    )
    args = parser.parse_args()

    # Validar arquivo
    if not os.path.exists(args.patch):
        print(f"ERRO: arquivo nao encontrado: {args.patch}")
        sys.exit(1)

    t0 = time.time()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] DMD Saude Brasil — Ingestao de patch CNES")
    print(f"  Arquivo: {args.patch}")

    # Ler patch
    with open(args.patch, "r", encoding="utf-8") as f:
        patch = json.load(f)

    competencia = patch.get("competencia", "")
    municipios = patch.get("municipios", [])
    print(f"  Competencia: {competencia}")
    print(f"  Municipios no patch: {len(municipios)}")

    if not competencia or not municipios:
        print("ERRO: patch vazio ou sem competencia.")
        sys.exit(1)

    # Extrair mes/ano
    parts = competencia.split("/")
    if len(parts) != 2:
        print(f"ERRO: formato de competencia invalido: {competencia} (esperado MM/AAAA)")
        sys.exit(1)
    mes, ano = int(parts[0]), int(parts[1])

    # Conectar
    print("  Conectando ao Supabase...")
    conn = conectar()
    cur = conn.cursor()
    print("  Conexao OK")

    # Competencia
    comp_id = obter_competencia(cur, conn, mes, ano)
    print(f"  Competencia ID: {comp_id}")

    # Processar municipios
    print(f"\n  Processando {len(municipios)} municipios...")
    total = 0
    ok_count = 0
    erros = []
    uf_atual = None

    # Agrupar por UF para commit por UF
    by_uf = {}
    for m in municipios:
        uf = m.get("uf", "??")
        if uf not in by_uf:
            by_uf[uf] = []
        by_uf[uf].append(m)

    for uf in sorted(by_uf.keys()):
        muns = by_uf[uf]
        uf_ok = 0
        for m in muns:
            total += 1
            try:
                sucesso, erro = processar_municipio(cur, comp_id, m)
                if sucesso:
                    ok_count += 1
                    uf_ok += 1
                else:
                    erros.append(erro)
            except Exception as e:
                erros.append(f"{m.get('m', '?')} ({uf}): {str(e)[:100]}")
                conn.rollback()

        conn.commit()
        print(f"    {uf}: {uf_ok}/{len(muns)}")

    # Contar alertas gerados
    cur.execute("""
        SELECT COUNT(*) FROM saude_mental
        WHERE competencia_id = %s AND alerta_fiscal = TRUE;
    """, (comp_id,))
    alertas = cur.fetchone()[0]

    # Contar vacuos de habilitacao
    cur.execute("""
        SELECT COUNT(*) FROM saude_mental
        WHERE competencia_id = %s AND psiq_habilitados = 0 AND caps_total > 0;
    """, (comp_id,))
    vacuos = cur.fetchone()[0]

    cur.close()
    conn.close()
    elapsed = time.time() - t0

    # Relatorio
    print(f"\n{'=' * 50}")
    print(f"  RELATORIO DE INGESTAO")
    print(f"{'=' * 50}")
    print(f"  Competencia:              {competencia}")
    print(f"  Total no patch:           {total}")
    print(f"  Atualizados com sucesso:  {ok_count}")
    print(f"  Pulados (sem IBGE):       {len(erros)}")
    print(f"  Alertas fiscais SM:       {alertas}")
    print(f"  Vacuos de habilitacao:    {vacuos}")
    print(f"  Tempo total:              {elapsed:.1f}s")

    if erros:
        print(f"\n  Erros ({len(erros)}):")
        for e in erros[:20]:
            print(f"    - {e}")
        if len(erros) > 20:
            print(f"    ... e mais {len(erros) - 20} erros")

    print(f"{'=' * 50}")
    sys.exit(0 if not erros else 1)


if __name__ == "__main__":
    main()
