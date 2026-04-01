#!/usr/bin/env python3
"""
DMD Saude Brasil — Verificacao de saude do banco Supabase.

Verifica conexao, conta registros e mostra ultima competencia carregada.

Uso:
    export SUPABASE_PASSWORD="..."
    python check_supabase.py

Modo alternativo (quando conexao direta nao funciona):
    export SUPABASE_ACCESS_TOKEN="sbp_..."
    python check_supabase.py --api
"""

import argparse
import json
import os
import subprocess
import sys

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


# ── Conexao direta via psycopg2 ──────────────────────────────

def conectar_psycopg2():
    host = os.environ.get("SUPABASE_HOST", "db.xxckbdilszvfmzyoquze.supabase.co")
    port = int(os.environ.get("SUPABASE_PORT", "5432"))
    dbname = os.environ.get("SUPABASE_DB", "postgres")
    user = os.environ.get("SUPABASE_USER", "postgres")
    password = os.environ.get("SUPABASE_PASSWORD")
    if not password:
        return None, "variavel SUPABASE_PASSWORD nao definida"
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password,
            connect_timeout=10,
        )
        conn.autocommit = True
        return conn, None
    except Exception as e:
        return None, str(e)[:120]


def query_psycopg2(conn, q):
    cur = conn.cursor()
    cur.execute(q)
    if cur.description:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    return []


# ── Conexao via Management API (fallback) ────────────────────

def query_api(q):
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    ref = os.environ.get("SUPABASE_PROJECT_REF", "xxckbdilszvfmzyoquze")
    if not token:
        return None
    url = f"https://api.supabase.com/v1/projects/{ref}/database/query"
    r = subprocess.run(
        ["curl", "-s", "-w", "\n%{http_code}", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"query": q})],
        capture_output=True, text=True, timeout=30,
    )
    lines = r.stdout.strip().rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    code = int(lines[-1]) if lines[-1].isdigit() else 0
    if code in (200, 201):
        try:
            return json.loads(body)
        except Exception:
            return []
    return None


def main():
    parser = argparse.ArgumentParser(description="Verifica saude do banco DMD Supabase")
    parser.add_argument("--api", action="store_true",
                        help="Usar Management API em vez de conexao direta")
    args = parser.parse_args()

    # Decidir metodo de conexao
    use_api = args.api
    conn = None
    pg_version = "?"

    if not use_api and HAS_PSYCOPG2:
        conn, err = conectar_psycopg2()
        if conn:
            rows = query_psycopg2(conn, "SELECT version();")
            pg_version = rows[0]["version"].split(",")[0] if rows else "?"
        else:
            print(f"  Conexao direta falhou: {err}")
            print("  Tentando via Management API...")
            use_api = True

    if use_api:
        rows = query_api("SELECT version();")
        if rows is None:
            print("ERRO: impossivel conectar.")
            print("  Defina SUPABASE_PASSWORD (conexao direta)")
            print("  ou SUPABASE_ACCESS_TOKEN (Management API)")
            sys.exit(1)
        pg_version = rows[0]["version"].split(",")[0] if rows else "?"

    def sql(q):
        if conn:
            return query_psycopg2(conn, q)
        return query_api(q) or []

    # ── Coletar dados ─────────────────────────────────────────

    contagens = {}
    tabelas = [
        "municipios", "leitos", "atencao_primaria", "saude_mental",
        "scores_municipio", "epidemiologia", "alertas", "series_cnes",
        "usuarios_dmd",
    ]
    for t in tabelas:
        rows = sql(f"SELECT COUNT(*) as n FROM {t};")
        contagens[t] = rows[0]["n"] if rows else 0

    # Ultima competencia
    rows = sql("""
        SELECT id, referencia, versao_banco
        FROM competencias ORDER BY ano DESC, mes DESC LIMIT 1;
    """)
    if rows:
        ult_comp = rows[0]
        comp_str = f"{ult_comp['referencia']} (ID: {ult_comp['id']}, {ult_comp.get('versao_banco', '?')})"
    else:
        comp_str = "nenhuma"

    # Alertas ativos
    rows = sql("SELECT COUNT(*) as n FROM saude_mental WHERE alerta_fiscal = TRUE;")
    alertas_sm = rows[0]["n"] if rows else 0

    # Top 5 UFs por score medio (menor = pior)
    rows = sql("""
        SELECT m.uf,
            ROUND(AVG(s.score_v3)::numeric, 1) as score_medio,
            COUNT(*) as n_mun
        FROM municipios m
        JOIN scores_municipio s ON s.municipio_ibge = m.ibge
        GROUP BY m.uf
        ORDER BY score_medio ASC
        LIMIT 5;
    """)
    top_ufs = rows if rows else []

    # Fechar conexao direta
    if conn:
        conn.close()

    # ── Exibir relatorio ──────────────────────────────────────

    modo = "API" if use_api else "psycopg2"
    conexao_status = f"OK ({pg_version}) [{modo}]"

    print()
    print(f"  ╔══ DMD SAUDE BRASIL — STATUS DO BANCO {'═' * 16}╗")
    print(f"  ║  Conexao:             {conexao_status:<32}║")
    print(f"  ║  Municipios:          {contagens['municipios']:>6,}                          ║")
    print(f"  ║  Ultima competencia:  {comp_str:<32}║")
    print(f"  ║  Leitos:              {contagens['leitos']:>6,} registros                  ║")
    print(f"  ║  Atencao primaria:    {contagens['atencao_primaria']:>6,} registros                  ║")
    print(f"  ║  Saude mental:        {contagens['saude_mental']:>6,} registros                  ║")
    print(f"  ║  Scores:              {contagens['scores_municipio']:>6,} registros                  ║")
    print(f"  ║  Epidemiologia:       {contagens['epidemiologia']:>6,} registros                  ║")
    print(f"  ║  Alertas SM ativos:   {alertas_sm:>6,}                          ║")
    print(f"  ║  Series CNES:         {contagens['series_cnes']:>6,} registros                  ║")
    print(f"  ║  Usuarios DMD:        {contagens['usuarios_dmd']:>6,}                          ║")
    print(f"  ║{'─' * 55}║")
    if top_ufs:
        print(f"  ║  Top 5 UFs mais criticas (menor score):             ║")
        for i, row in enumerate(top_ufs):
            score = float(row["score_medio"]) if row["score_medio"] else 0
            print(f"  ║    {i + 1}. {row['uf']}  {score:>5.1f}  ({row['n_mun']} mun.)                     ║")
    print(f"  ╚{'═' * 55}╝")
    print()


if __name__ == "__main__":
    main()
