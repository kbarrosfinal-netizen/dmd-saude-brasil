#!/usr/bin/env python3
"""
DMD Saude Brasil — Agregacao mensal para series temporais CNES.

Apos cada ingestao de patch, agrega dados por UF e insere na tabela
series_cnes para alimentar graficos de evolucao temporal.

Uso:
    export SUPABASE_PASSWORD="..."
    python update_series_cnes.py --competencia 03/2026
"""

import argparse
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

    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password,
            connect_timeout=15,
        )
        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERRO: impossivel conectar ao banco: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Agrega dados por UF e atualiza series_cnes"
    )
    parser.add_argument(
        "--competencia", required=True,
        help="Competencia no formato MM/AAAA (ex: 03/2026)"
    )
    args = parser.parse_args()

    parts = args.competencia.split("/")
    if len(parts) != 2:
        print(f"ERRO: formato invalido: {args.competencia} (esperado MM/AAAA)")
        sys.exit(1)
    mes, ano = int(parts[0]), int(parts[1])

    t0 = time.time()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] DMD Saude Brasil — Atualizacao series CNES")
    print(f"  Competencia: {args.competencia} (mes={mes}, ano={ano})")

    conn = conectar()
    cur = conn.cursor()
    print("  Conexao OK")

    # Buscar competencia_id mais recente para agregar
    cur.execute("""
        SELECT id FROM competencias
        WHERE ano = %s AND mes = %s
        ORDER BY id DESC LIMIT 1;
    """, (ano, mes))
    row = cur.fetchone()
    if row:
        comp_id = row[0]
    else:
        # Usar a competencia mais recente disponivel
        cur.execute("SELECT id FROM competencias ORDER BY ano DESC, mes DESC LIMIT 1;")
        row = cur.fetchone()
        comp_id = row[0] if row else 1
    print(f"  Competencia ID: {comp_id}")

    # Agregar por UF
    cur.execute("""
        SELECT
            m.uf,
            COALESCE(SUM(l.leitos_sus), 0)::INTEGER as leitos_sus,
            COALESCE(SUM(
                COALESCE(l.leitos_uti_adulto, 0) +
                COALESCE(l.leitos_uti_neonatal, 0) +
                COALESCE(l.leitos_uti_pediatrico, 0)
            ), 0)::INTEGER as leitos_uti,
            COALESCE(SUM(sm.caps_total), 0)::INTEGER as caps_total
        FROM municipios m
        LEFT JOIN leitos l
            ON l.municipio_ibge = m.ibge AND l.competencia_id = %s
        LEFT JOIN saude_mental sm
            ON sm.municipio_ibge = m.ibge AND sm.competencia_id = %s
        GROUP BY m.uf
        ORDER BY m.uf;
    """, (comp_id, comp_id))

    rows = cur.fetchall()
    count = 0

    for uf, leitos_sus, leitos_uti, caps_total in rows:
        cur.execute("""
            INSERT INTO series_cnes (uf, ano, mes, leitos_sus, leitos_uti, caps_total, fonte)
            VALUES (%s, %s, %s, %s, %s, %s, 'CNES/MS')
            ON CONFLICT (uf, ano, mes) DO UPDATE SET
                leitos_sus = EXCLUDED.leitos_sus,
                leitos_uti = EXCLUDED.leitos_uti,
                caps_total = EXCLUDED.caps_total;
        """, (uf, ano, mes, leitos_sus, leitos_uti, caps_total))
        count += 1

    conn.commit()

    # Verificar resultado
    cur.execute("""
        SELECT uf, leitos_sus, leitos_uti, caps_total
        FROM series_cnes
        WHERE ano = %s AND mes = %s
        ORDER BY uf;
    """, (ano, mes))
    series = cur.fetchall()

    cur.close()
    conn.close()
    elapsed = time.time() - t0

    print(f"\n  {count} UFs atualizadas em series_cnes")
    print(f"\n  {'UF':<4} {'Leitos SUS':>12} {'Leitos UTI':>12} {'CAPS':>6}")
    print(f"  {'-'*38}")
    for uf, ls, lu, cap in series:
        print(f"  {uf:<4} {ls:>12,} {lu:>12,} {cap:>6}")

    total_leitos = sum(r[1] for r in series)
    total_uti = sum(r[2] for r in series)
    total_caps = sum(r[3] for r in series)
    print(f"  {'-'*38}")
    print(f"  {'BR':<4} {total_leitos:>12,} {total_uti:>12,} {total_caps:>6}")
    print(f"\n  Tempo: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
