#!/usr/bin/env python3
"""
DMD Saude Brasil - Carga de dados no Supabase PostgreSQL
Usa Management API via curl (contorna DNS local)
"""

import json, subprocess, time, os, sys

PROJECT_REF = "xxckbdilszvfmzyoquze"
TOKEN = "sbp_4de6618159100a4c4a199f2dbc0a1f2b5be28594"
URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
COMP_ID = 1  # Competencia criada no passo anterior


def sql(query):
    """Executa SQL via Management API"""
    r = subprocess.run(
        ["curl", "-s", "-w", "\n%{http_code}", URL,
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"query": query})],
        capture_output=True, text=True, timeout=120
    )
    lines = r.stdout.strip().rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    code = int(lines[-1]) if lines[-1].isdigit() else 0
    if code in (200, 201):
        try:
            return True, json.loads(body)
        except:
            return True, body
    return False, f"HTTP {code}: {body[:300]}"


def esc(v):
    """Escapa string para SQL"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def nullable(v):
    """Retorna NULL se vazio/None/0"""
    if v is None or v == '' or v == 0 or v == 0.0:
        return "NULL"
    return esc(v)


def num(v):
    """Retorna numero ou NULL"""
    if v is None or v == '' or v == 'N/A':
        return "NULL"
    try:
        n = float(v)
        if n == 0:
            return "0"
        return str(n)
    except:
        return "NULL"


# ============================================================
# Carregar dados
# ============================================================
print("Carregando export/export_munis_full.json...")
with open('export/export_munis_full.json', 'r', encoding='utf-8') as f:
    munis_full = json.load(f)

total_munis = sum(len(v) for v in munis_full.values())
print(f"  {len(munis_full)} UFs, {total_munis} municipios\n")

# ============================================================
# PASSO 4: MUNICIPIOS
# ============================================================
print("=" * 60)
print("PASSO 4: MUNICIPIOS")
print("=" * 60)

count = 0
errors = []
BATCH_SIZE = 100

for uf, municipios in sorted(munis_full.items()):
    values_list = []
    for m in municipios:
        ibge = str(m.get('ibge_cod', '')).strip()
        if not ibge or len(ibge) < 6:
            errors.append(f"IBGE invalido: {m.get('m', '?')} ({uf}) ibge={ibge}")
            continue
        ibge = ibge.zfill(7)

        vals = (
            f"({esc(ibge)}, {esc(m.get('m', ''))}, {esc(uf)}, "
            f"{num(m.get('pop', 0))}, {nullable(m.get('idh'))}, "
            f"{num(m.get('lat'))}, {num(m.get('lon'))}, "
            f"{nullable(m.get('porte'))})"
        )
        values_list.append(vals)

    # Inserir em lotes
    for i in range(0, len(values_list), BATCH_SIZE):
        batch = values_list[i:i + BATCH_SIZE]
        insert_sql = f"""
        INSERT INTO municipios (ibge, nome, uf, populacao, idh, latitude, longitude, faixa_pop)
        VALUES {', '.join(batch)}
        ON CONFLICT (ibge) DO UPDATE SET
            nome = EXCLUDED.nome,
            populacao = EXCLUDED.populacao,
            idh = EXCLUDED.idh,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            faixa_pop = EXCLUDED.faixa_pop;
        """
        ok, r = sql(insert_sql)
        if not ok:
            errors.append(f"{uf} batch {i}: {r[:100]}")
        else:
            count += len(batch)
        time.sleep(0.2)

    print(f"  {uf}: {len(municipios)} municipios")

print(f"\nTotal municipios inseridos: {count}")
if errors:
    print(f"Erros ({len(errors)}):")
    for e in errors[:5]:
        print(f"  {e}")

# ============================================================
# PASSO 5: LEITOS
# ============================================================
print("\n" + "=" * 60)
print("PASSO 5: LEITOS")
print("=" * 60)

count = 0
errors_l = []

for uf, municipios in sorted(munis_full.items()):
    values_list = []
    for m in municipios:
        ibge = str(m.get('ibge_cod', '')).strip().zfill(7)
        if not ibge or ibge == '0000000' or len(ibge) < 7:
            continue

        leitos_sus = m.get('leitos_sus', 0)
        if leitos_sus is None or leitos_sus == '':
            leitos_sus = 0

        uti = m.get('u', 0)
        if uti is None or uti == '':
            uti = 0
        # u pode ser float (taxa) ou int (absoluto)
        # Se < 1, provavelmente é taxa — nao usar como absoluto
        uti_abs = int(uti) if isinstance(uti, (int, float)) and uti >= 1 else 0

        vals = (
            f"({esc(ibge)}, {COMP_ID}, "
            f"{num(leitos_sus)}, "  # leitos_sus
            f"0, 0, 0, "  # clinicos, cirurgicos, obstetricos
            f"{uti_abs}, 0, 0, "  # uti adulto, neo, ped
            f"{num(m.get('lq', 0))}, "  # psiquiatricos
            f"0, "  # complementares
            f"NULL, NULL, "  # leitos_por_1k, uti_por_100k (trigger calcula)
            f"{num(m.get('dl'))}, "  # deficit_leitos
            f"{num(m.get('du'))}, "  # deficit_uti
            f"'CNES', FALSE)"
        )
        values_list.append(vals)

    for i in range(0, len(values_list), BATCH_SIZE):
        batch = values_list[i:i + BATCH_SIZE]
        insert_sql = f"""
        INSERT INTO leitos (municipio_ibge, competencia_id,
            leitos_sus, leitos_clinicos, leitos_cirurgicos, leitos_obstetricos,
            leitos_uti_adulto, leitos_uti_neonatal, leitos_uti_pediatrico,
            leitos_psiquiatricos, leitos_complementares,
            leitos_por_1k, uti_por_100k,
            deficit_leitos, deficit_uti, fonte, imputado)
        VALUES {', '.join(batch)}
        ON CONFLICT (municipio_ibge, competencia_id) DO UPDATE SET
            leitos_sus = EXCLUDED.leitos_sus,
            leitos_uti_adulto = EXCLUDED.leitos_uti_adulto,
            deficit_leitos = EXCLUDED.deficit_leitos,
            deficit_uti = EXCLUDED.deficit_uti;
        """
        ok, r = sql(insert_sql)
        if not ok:
            errors_l.append(f"{uf} batch {i}: {r[:100]}")
        else:
            count += len(batch)
        time.sleep(0.2)

    print(f"  {uf}: OK")

print(f"\nTotal leitos inseridos: {count}")

# ============================================================
# PASSO 6: ATENCAO PRIMARIA
# ============================================================
print("\n" + "=" * 60)
print("PASSO 6: ATENCAO PRIMARIA")
print("=" * 60)

count = 0
for uf, municipios in sorted(munis_full.items()):
    values_list = []
    for m in municipios:
        ibge = str(m.get('ibge_cod', '')).strip().zfill(7)
        if not ibge or ibge == '0000000':
            continue

        esf = m.get('e')
        if esf is not None and isinstance(esf, (int, float)):
            # Ja vem em % (ex: 83.1)
            esf_val = num(esf)
        else:
            esf_val = "NULL"

        vals = (
            f"({esc(ibge)}, {COMP_ID}, "
            f"{esf_val}, "  # cobertura_esf_pct
            f"{num(m.get('esf_equipes', 0))}, "  # equipes_esf
            f"0, "  # equipes_eap
            f"0, "  # ubs_total
            f"{num(m.get('agentes_acs', 0))}, "  # acs_total
            f"NULL, NULL, NULL, NULL, "  # previne_*
            f"'e-Gestor AB')"
        )
        values_list.append(vals)

    for i in range(0, len(values_list), BATCH_SIZE):
        batch = values_list[i:i + BATCH_SIZE]
        insert_sql = f"""
        INSERT INTO atencao_primaria (municipio_ibge, competencia_id,
            cobertura_esf_pct, equipes_esf, equipes_eap, ubs_total, acs_total,
            previne_prenatal, previne_sifilis, previne_hiv, previne_citopat, fonte)
        VALUES {', '.join(batch)}
        ON CONFLICT (municipio_ibge, competencia_id) DO UPDATE SET
            cobertura_esf_pct = EXCLUDED.cobertura_esf_pct,
            equipes_esf = EXCLUDED.equipes_esf,
            acs_total = EXCLUDED.acs_total;
        """
        ok, r = sql(insert_sql)
        if ok:
            count += len(batch)
        time.sleep(0.2)

    print(f"  {uf}: OK")

print(f"\nTotal atencao primaria: {count}")

# ============================================================
# PASSO 7: SAUDE MENTAL
# ============================================================
print("\n" + "=" * 60)
print("PASSO 7: SAUDE MENTAL")
print("=" * 60)

count = 0
for uf, municipios in sorted(munis_full.items()):
    values_list = []
    for m in municipios:
        ibge = str(m.get('ibge_cod', '')).strip().zfill(7)
        if not ibge or ibge == '0000000':
            continue

        cob_raps = m.get('cobertura_raps', '')
        is_raps = cob_raps in ('SIM', True, 'true', 'True')
        is_alerta = m.get('alerta_fiscal', False) is True

        vals = (
            f"({esc(ibge)}, {COMP_ID}, "
            f"{num(m.get('caps', 0))}, "  # caps_total
            f"{esc(m.get('caps_tipo', ''))}, "  # caps_tipo
            f"{esc(m.get('caps_nomes', ''))}, "  # caps_nomes
            f"{num(m.get('srt', 0))}, "  # srt
            f"{num(m.get('leitos_hg', 0))}, "  # leitos_psiq_hg
            f"{num(m.get('psiq_cad', 0))}, "  # psiq_cadastrados
            f"{num(m.get('psiq_hab', 0))}, "  # psiq_habilitados
            f"{esc(m.get('psiq_status', ''))}, "  # status_habilitacao
            f"{'TRUE' if is_raps else 'FALSE'}, "  # cobertura_raps
            f"{'TRUE' if is_alerta else 'FALSE'}, "  # alerta_fiscal
            f"{esc(m.get('nota_habilitacao', ''))}, "  # nota_habilitacao
            f"{esc(m.get('fonte_sm', 'CNES'))})"  # fonte
        )
        values_list.append(vals)

    for i in range(0, len(values_list), BATCH_SIZE):
        batch = values_list[i:i + BATCH_SIZE]
        insert_sql = f"""
        INSERT INTO saude_mental (municipio_ibge, competencia_id,
            caps_total, caps_tipo, caps_nomes, srt, leitos_psiq_hg,
            psiq_cadastrados, psiq_habilitados, status_habilitacao,
            cobertura_raps, alerta_fiscal, nota_habilitacao, fonte)
        VALUES {', '.join(batch)}
        ON CONFLICT (municipio_ibge, competencia_id) DO UPDATE SET
            caps_total = EXCLUDED.caps_total,
            psiq_cadastrados = EXCLUDED.psiq_cadastrados,
            psiq_habilitados = EXCLUDED.psiq_habilitados,
            alerta_fiscal = EXCLUDED.alerta_fiscal;
        """
        ok, r = sql(insert_sql)
        if ok:
            count += len(batch)
        time.sleep(0.2)

    print(f"  {uf}: OK")

print(f"\nTotal saude mental: {count}")

# ============================================================
# PASSO 8: SCORES
# ============================================================
print("\n" + "=" * 60)
print("PASSO 8: SCORES MUNICIPIO")
print("=" * 60)

count = 0
for uf, municipios in sorted(munis_full.items()):
    values_list = []
    for m in municipios:
        ibge = str(m.get('ibge_cod', '')).strip().zfill(7)
        if not ibge or ibge == '0000000':
            continue

        score = m.get('score_v3')
        if score is None:
            continue

        vals = (
            f"({esc(ibge)}, {COMP_ID}, "
            f"{num(score)}, "  # score_v3
            f"{esc(m.get('risco_v3', ''))}, "  # classificacao
            f"{num(m.get('score_v3_d1'))}, "  # comp_deficit_leitos
            f"{num(m.get('score_v3_d2'))}, "  # comp_uti
            f"{num(m.get('score_v3_d3'))}, "  # comp_esf
            f"{num(m.get('score_v3_d4'))}, "  # comp_receita
            f"NULL, NULL, NULL, NULL, "  # comp_fila, dengue, glosa, vacinal
            f"NULL, "  # deserto_tipo
            f"'V3')"  # versao_calculo
        )
        values_list.append(vals)

    for i in range(0, len(values_list), BATCH_SIZE):
        batch = values_list[i:i + BATCH_SIZE]
        insert_sql = f"""
        INSERT INTO scores_municipio (municipio_ibge, competencia_id,
            score_v3, classificacao, comp_deficit_leitos, comp_uti,
            comp_esf, comp_receita, comp_fila, comp_dengue, comp_glosa, comp_vacinal,
            deserto_tipo, versao_calculo)
        VALUES {', '.join(batch)}
        ON CONFLICT (municipio_ibge, competencia_id) DO UPDATE SET
            score_v3 = EXCLUDED.score_v3,
            classificacao = EXCLUDED.classificacao,
            comp_deficit_leitos = EXCLUDED.comp_deficit_leitos,
            comp_uti = EXCLUDED.comp_uti,
            comp_esf = EXCLUDED.comp_esf,
            comp_receita = EXCLUDED.comp_receita;
        """
        ok, r = sql(insert_sql)
        if ok:
            count += len(batch)
        time.sleep(0.2)

    print(f"  {uf}: OK")

print(f"\nTotal scores: {count}")

# ============================================================
# PASSO 9: EPIDEMIOLOGIA
# ============================================================
print("\n" + "=" * 60)
print("PASSO 9: EPIDEMIOLOGIA")
print("=" * 60)

count = 0
for uf, municipios in sorted(munis_full.items()):
    values_list = []
    for m in municipios:
        ibge = str(m.get('ibge_cod', '')).strip().zfill(7)
        if not ibge or ibge == '0000000':
            continue

        vals = (
            f"({esc(ibge)}, {esc(uf)}, 2025, "
            f"{num(m.get('mi'))}, "  # mortalidade_infantil
            f"{num(m.get('mm'))}, "  # mortalidade_materna
            f"{num(m.get('mort_cv_100k'))}, "  # mortalidade_cv
            f"NULL, "  # mortalidade_hospitalar
            f"{num(m.get('nascimentos'))}, "  # nascidos_vivos
            f"NULL, "  # partos_cesareos_pct
            f"{num(m.get('dengue_inc'))}, "  # dengue_inc_100k
            f"NULL, NULL, "  # malaria, tuberculose
            f"{num(m.get('prev_dm_pct'))}, "  # prev_diabetes
            f"{num(m.get('prev_has_pct'))}, "  # prev_hipertensao
            f"{num(m.get('cob_sarampo'))}, "  # cob_vacinal_sarampo
            f"NULL, NULL, "  # polio, penta
            f"{num(m.get('cobertura_vacinal'))}, "  # cob_vacinal_infantil
            f"'SIM/SINASC/SINAN/PNI')"
        )
        values_list.append(vals)

    for i in range(0, len(values_list), BATCH_SIZE):
        batch = values_list[i:i + BATCH_SIZE]
        insert_sql = f"""
        INSERT INTO epidemiologia (municipio_ibge, uf, ano,
            mortalidade_infantil, mortalidade_materna, mortalidade_cv,
            mortalidade_hospitalar, nascidos_vivos, partos_cesareos_pct,
            dengue_inc_100k, malaria_casos, tuberculose_inc,
            prev_diabetes, prev_hipertensao,
            cob_vacinal_sarampo, cob_vacinal_polio, cob_vacinal_penta,
            cob_vacinal_infantil, fonte)
        VALUES {', '.join(batch)}
        ON CONFLICT DO NOTHING;
        """
        ok, r = sql(insert_sql)
        if ok:
            count += len(batch)
        time.sleep(0.2)

    print(f"  {uf}: OK")

print(f"\nTotal epidemiologia: {count}")

# ============================================================
# PASSO 10: PRODUCAO HOSPITALAR (dados de UF_SIH_DATA)
# ============================================================
print("\n" + "=" * 60)
print("PASSO 10: SERIES CNES (dados AM)")
print("=" * 60)

# Carregar series AM
if os.path.exists('export/export__ser_est.json'):
    with open('export/export__ser_est.json') as f:
        ser_est = json.load(f)

    values_list = []
    for s in ser_est:
        ano = s.get('ano')
        if not ano:
            continue
        vals = (
            f"('AM', {ano}, 1, "
            f"{num(s.get('leitos'))}, "
            f"{num(s.get('uti'))}, "
            f"NULL, NULL, NULL, NULL, NULL, 'CNES/MS')"
        )
        values_list.append(vals)

    if values_list:
        insert_sql = f"""
        INSERT INTO series_cnes (uf, ano, mes, leitos_sus, leitos_uti,
            medicos_sus, enfermeiros, equipes_esf, estabelecimentos, caps_total, fonte)
        VALUES {', '.join(values_list)}
        ON CONFLICT (uf, ano, mes) DO UPDATE SET
            leitos_sus = EXCLUDED.leitos_sus,
            leitos_uti = EXCLUDED.leitos_uti;
        """
        ok, r = sql(insert_sql)
        print(f"  Series CNES AM: {'OK' if ok else r[:100]} ({len(values_list)} registros)")

# ============================================================
# PASSO 11: DADOS AM PILOTO
# ============================================================
print("\n" + "=" * 60)
print("PASSO 11: DADOS AM PILOTO")
print("=" * 60)

# Alertas AM
if os.path.exists('export/export_alertas.json'):
    with open('export/export_alertas.json') as f:
        alertas = json.load(f)

    values_list = []
    for a in alertas:
        if isinstance(a, list) and len(a) >= 3:
            vals = (
                f"(NULL, 'AM', {COMP_ID}, "
                f"{esc(a[2])}, "  # tipo (categoria)
                f"{esc(a[1])}, "  # gravidade
                f"{esc(a[0])}, "  # descricao (titulo)
                f"NULL, NULL, FALSE)"
            )
            values_list.append(vals)

    if values_list:
        insert_sql = f"""
        INSERT INTO alertas (municipio_ibge, uf, competencia_id,
            tipo, gravidade, descricao, base_legal, valor_referencia, resolvido)
        VALUES {', '.join(values_list)}
        ON CONFLICT DO NOTHING;
        """
        ok, r = sql(insert_sql)
        print(f"  Alertas AM: {'OK' if ok else r[:100]} ({len(values_list)} alertas)")

# Glosas AM
if os.path.exists('export/export_glosa.json'):
    with open('export/export_glosa.json') as f:
        glosas = json.load(f)

    values_list = []
    for g in glosas:
        if isinstance(g, list) and len(g) >= 5:
            nome = str(g[0]).replace("'", "''")
            vals = (
                f"(NULL, '{nome}', 2025, "
                f"NULL, "  # base_aih_valor
                f"{num(g[1])}, "  # glosa_pct
                f"{num(g[2])}, "  # glosa_valor
                f"{num(g[3])}, "  # recuperavel
                f"{num(g[4])}, "  # roi_12m
                f"NULL)"  # score_pareto
            )
            values_list.append(vals)

    if values_list:
        insert_sql = f"""
        INSERT INTO am_glosas_unidade (estabelecimento_cnes, nome_unidade, ano,
            base_aih_valor, glosa_pct, glosa_valor, recuperavel, roi_12m, score_pareto)
        VALUES {', '.join(values_list)}
        ON CONFLICT DO NOTHING;
        """
        ok, r = sql(insert_sql)
        print(f"  Glosas AM: {'OK' if ok else r[:100]} ({len(values_list)} unidades)")

# Scores UF (via ST)
if os.path.exists('export/export_st.json'):
    with open('export/export_st.json') as f:
        st_data = json.load(f)

    # Atualizar populacao nas UFs
    for s in st_data:
        uf_sigla = s.get('uf', '')
        pop = s.get('pop', 0)
        if uf_sigla and pop:
            sql_up = f"UPDATE ufs SET populacao = {pop} WHERE sigla = '{uf_sigla}';"
            sql(sql_up)
    print(f"  Populacao UFs atualizada: {len(st_data)} UFs")

# ============================================================
# VERIFICACAO FINAL
# ============================================================
print("\n" + "=" * 60)
print("VERIFICACAO FINAL")
print("=" * 60)

time.sleep(1)

# Contagem por tabela
ok, r = sql("""
SELECT 'ufs' as tabela, COUNT(*) as registros FROM ufs
UNION ALL SELECT 'municipios', COUNT(*) FROM municipios
UNION ALL SELECT 'leitos', COUNT(*) FROM leitos
UNION ALL SELECT 'atencao_primaria', COUNT(*) FROM atencao_primaria
UNION ALL SELECT 'saude_mental', COUNT(*) FROM saude_mental
UNION ALL SELECT 'scores_municipio', COUNT(*) FROM scores_municipio
UNION ALL SELECT 'epidemiologia', COUNT(*) FROM epidemiologia
UNION ALL SELECT 'alertas', COUNT(*) FROM alertas
UNION ALL SELECT 'series_cnes', COUNT(*) FROM series_cnes
UNION ALL SELECT 'am_glosas_unidade', COUNT(*) FROM am_glosas_unidade
ORDER BY tabela;
""")
if ok:
    print("\nContagem por tabela:")
    for row in r:
        print(f"  {row['tabela']:<25} {row['registros']:>6} registros")

# Municipios por UF
ok, r = sql("SELECT uf, COUNT(*) as n FROM municipios GROUP BY uf ORDER BY uf;")
if ok:
    print(f"\nMunicipios por UF ({sum(row['n'] for row in r)} total):")
    line = ""
    for row in r:
        line += f"  {row['uf']}:{row['n']}"
        if len(line) > 70:
            print(line)
            line = ""
    if line:
        print(line)

# Verificar trigger leitos_por_1k
ok, r = sql("""
SELECT m.nome, m.populacao, l.leitos_sus, l.leitos_por_1k, l.uti_por_100k
FROM municipios m JOIN leitos l ON l.municipio_ibge = m.ibge
WHERE l.leitos_por_1k IS NOT NULL AND l.leitos_por_1k > 0
ORDER BY l.leitos_por_1k DESC
LIMIT 5;
""")
if ok and r:
    print("\nTrigger leitos_por_1k (top 5):")
    for row in r:
        print(f"  {row['nome']}: pop={row['populacao']}, leitos={row['leitos_sus']}, "
              f"l/1k={row['leitos_por_1k']}, uti/100k={row['uti_por_100k']}")

# Alertas SM gerados pelo trigger
ok, r = sql("SELECT COUNT(*) as n FROM saude_mental WHERE alerta_fiscal = TRUE;")
if ok:
    print(f"\nAlertas fiscais saude mental (trigger): {r[0]['n']}")

print("\n" + "=" * 60)
print("CARGA CONCLUIDA")
print("=" * 60)
