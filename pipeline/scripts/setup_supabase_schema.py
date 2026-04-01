#!/usr/bin/env python3
"""
DMD Saude Brasil - Setup schema PostgreSQL no Supabase
Usa curl via subprocess para contornar limitacoes do urllib
"""

import json
import subprocess
import sys
import time

PROJECT_REF = "xxckbdilszvfmzyoquze"
ACCESS_TOKEN = "sbp_4de6618159100a4c4a199f2dbc0a1f2b5be28594"
API_URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"


def run_sql(sql, label=""):
    """Executa SQL via Supabase Management API usando curl"""
    payload = json.dumps({"query": sql})
    result = subprocess.run(
        [
            "curl", "-s", "-w", "\n%{http_code}",
            API_URL,
            "-H", f"Authorization: Bearer {ACCESS_TOKEN}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True, text=True, timeout=60
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    code = int(lines[-1]) if lines[-1].isdigit() else 0
    if code in (200, 201):
        return True, body
    else:
        return False, f"HTTP {code}: {body[:300]}"


# ============================================================
print("=== EXTENSOES ===")
for ext in ["uuid-ossp", "unaccent", "pg_trgm"]:
    ok, r = run_sql(f'CREATE EXTENSION IF NOT EXISTS "{ext}";')
    status = "OK" if ok else f"ERRO - {r[:80]}"
    print(f"  {ext}: {status}")

# ============================================================
blocos = []

blocos.append(("BLOCO 1 - Hierarquia territorial", [
    """CREATE TABLE regioes_brasil (
    id          SMALLINT PRIMARY KEY,
    nome        TEXT NOT NULL UNIQUE,
    sigla       CHAR(2) NOT NULL UNIQUE
);""",
    """CREATE TABLE ufs (
    sigla       CHAR(2) PRIMARY KEY,
    nome        TEXT NOT NULL,
    regiao_id   SMALLINT NOT NULL REFERENCES regioes_brasil(id),
    populacao   INTEGER NOT NULL DEFAULT 0,
    capital     TEXT,
    area_km2    NUMERIC(12,2)
);""",
    """CREATE TABLE macrorregioes_saude (
    id          SERIAL PRIMARY KEY,
    uf          CHAR(2) NOT NULL REFERENCES ufs(sigla),
    nome        TEXT NOT NULL,
    UNIQUE(uf, nome)
);""",
    """CREATE TABLE regioes_saude (
    id          SERIAL PRIMARY KEY,
    uf          CHAR(2) NOT NULL REFERENCES ufs(sigla),
    macro_id    INTEGER REFERENCES macrorregioes_saude(id),
    nome        TEXT NOT NULL,
    cod_ms      INTEGER,
    UNIQUE(uf, nome)
);""",
    """CREATE TABLE municipios (
    ibge        CHAR(7) PRIMARY KEY,
    nome        TEXT NOT NULL,
    uf          CHAR(2) NOT NULL REFERENCES ufs(sigla),
    regiao_saude_id INTEGER REFERENCES regioes_saude(id),
    populacao   INTEGER NOT NULL DEFAULT 0,
    faixa_pop   TEXT,
    area_km2    NUMERIC(12,2),
    idh         NUMERIC(5,3),
    latitude    NUMERIC(10,7),
    longitude   NUMERIC(10,7),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_municipios_uf ON municipios(uf);
CREATE INDEX idx_municipios_nome_trgm ON municipios USING gin(nome gin_trgm_ops);
CREATE INDEX idx_municipios_pop ON municipios(populacao DESC);""",
]))

blocos.append(("BLOCO 2 - Fontes e competencias", [
    """CREATE TABLE fontes (
    id          SERIAL PRIMARY KEY,
    sigla       TEXT NOT NULL UNIQUE,
    nome        TEXT NOT NULL,
    orgao       TEXT,
    url         TEXT,
    frequencia  TEXT
);""",
    """CREATE TABLE competencias (
    id          SERIAL PRIMARY KEY,
    ano         SMALLINT NOT NULL,
    mes         SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    referencia  TEXT NOT NULL,
    data_carga  TIMESTAMPTZ DEFAULT NOW(),
    fonte_id    INTEGER NOT NULL REFERENCES fontes(id),
    versao_banco TEXT,
    hash_sha256 TEXT,
    UNIQUE(ano, mes, fonte_id)
);""",
]))

blocos.append(("BLOCO 3 - Infraestrutura CNES", [
    """CREATE TABLE estabelecimentos (
    cnes        CHAR(7) PRIMARY KEY,
    nome        TEXT NOT NULL,
    municipio_ibge CHAR(7) NOT NULL REFERENCES municipios(ibge),
    tipo        TEXT,
    subtipo     TEXT,
    natureza    TEXT,
    gestao      TEXT,
    cnpj        CHAR(14),
    ativo       BOOLEAN DEFAULT TRUE,
    latitude    NUMERIC(10,7),
    longitude   NUMERIC(10,7),
    competencia_id INTEGER REFERENCES competencias(id),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);""",
    """CREATE TABLE leitos (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    leitos_sus      INTEGER DEFAULT 0,
    leitos_clinicos INTEGER DEFAULT 0,
    leitos_cirurgicos INTEGER DEFAULT 0,
    leitos_obstetricos INTEGER DEFAULT 0,
    leitos_pediatricos INTEGER DEFAULT 0,
    leitos_uti_adulto INTEGER DEFAULT 0,
    leitos_uti_neonatal INTEGER DEFAULT 0,
    leitos_uti_pediatrico INTEGER DEFAULT 0,
    leitos_psiquiatricos INTEGER DEFAULT 0,
    leitos_complementares INTEGER DEFAULT 0,
    leitos_por_1k   NUMERIC(6,3),
    uti_por_100k    NUMERIC(6,2),
    deficit_leitos  INTEGER,
    deficit_uti     INTEGER,
    fonte           TEXT DEFAULT 'CNES',
    imputado        BOOLEAN DEFAULT FALSE,
    UNIQUE(municipio_ibge, competencia_id)
);""",
    """CREATE TABLE profissionais_saude (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    medicos_total   INTEGER DEFAULT 0,
    medicos_sus     INTEGER DEFAULT 0,
    enfermeiros     INTEGER DEFAULT 0,
    dentistas       INTEGER DEFAULT 0,
    psiquiatras     INTEGER DEFAULT 0,
    medicos_por_1k  NUMERIC(6,3),
    UNIQUE(municipio_ibge, competencia_id)
);""",
]))

blocos.append(("BLOCO 4 - Atencao primaria", [
    """CREATE TABLE atencao_primaria (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    cobertura_esf_pct NUMERIC(5,2),
    equipes_esf     INTEGER DEFAULT 0,
    equipes_eap     INTEGER DEFAULT 0,
    ubs_total       INTEGER DEFAULT 0,
    acs_total       INTEGER DEFAULT 0,
    previne_prenatal NUMERIC(5,2),
    previne_sifilis  NUMERIC(5,2),
    previne_hiv      NUMERIC(5,2),
    previne_citopat  NUMERIC(5,2),
    fonte           TEXT DEFAULT 'e-Gestor AB',
    UNIQUE(municipio_ibge, competencia_id)
);""",
]))

blocos.append(("BLOCO 5 - Producao hospitalar SIH", [
    """CREATE TABLE producao_hospitalar (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    aih_aprovadas   INTEGER DEFAULT 0,
    aih_rejeitadas  INTEGER DEFAULT 0,
    valor_total     NUMERIC(14,2) DEFAULT 0,
    valor_rejeitado NUMERIC(14,2) DEFAULT 0,
    glosa_pct       NUMERIC(5,2),
    custo_medio_aih NUMERIC(10,2),
    tempo_medio_permanencia NUMERIC(5,1),
    taxa_mortalidade NUMERIC(5,2),
    taxa_reinternacao_30d NUMERIC(5,2),
    icsap_total     INTEGER DEFAULT 0,
    icsap_pct       NUMERIC(5,2),
    giro_leito      NUMERIC(5,2),
    taxa_ocupacao   NUMERIC(5,2),
    fonte           TEXT DEFAULT 'SIH/DATASUS',
    UNIQUE(municipio_ibge, competencia_id)
);""",
]))

blocos.append(("BLOCO 6 - Orcamento", [
    """CREATE TABLE orcamento_saude (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) REFERENCES municipios(ibge),
    uf              CHAR(2) REFERENCES ufs(sigla),
    ano             SMALLINT NOT NULL,
    receita_propria NUMERIC(14,2),
    repasse_fns     NUMERIC(14,2),
    emendas         NUMERIC(14,2),
    receita_total   NUMERIC(14,2),
    receita_per_capita NUMERIC(10,2),
    despesa_pessoal NUMERIC(14,2),
    despesa_custeio NUMERIC(14,2),
    despesa_investimento NUMERIC(14,2),
    despesa_total   NUMERIC(14,2),
    pct_asps        NUMERIC(5,2),
    cumpre_lc141    BOOLEAN,
    fonte           TEXT DEFAULT 'SIOPS'
);""",
]))

blocos.append(("BLOCO 7 - Saude mental", [
    """CREATE TABLE saude_mental (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    caps_total      INTEGER DEFAULT 0,
    caps_tipo       TEXT,
    caps_nomes      TEXT,
    srt             INTEGER DEFAULT 0,
    leitos_psiq_hg  INTEGER DEFAULT 0,
    psiq_cadastrados INTEGER DEFAULT 0,
    psiq_habilitados INTEGER DEFAULT 0,
    status_habilitacao TEXT,
    cobertura_raps  BOOLEAN DEFAULT FALSE,
    alerta_fiscal   BOOLEAN DEFAULT FALSE,
    nota_habilitacao TEXT,
    fonte           TEXT DEFAULT 'CNES',
    UNIQUE(municipio_ibge, competencia_id)
);""",
]))

blocos.append(("BLOCO 8 - Epidemiologia", [
    """CREATE TABLE epidemiologia (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) REFERENCES municipios(ibge),
    uf              CHAR(2) REFERENCES ufs(sigla),
    ano             SMALLINT NOT NULL,
    mortalidade_infantil NUMERIC(6,2),
    mortalidade_materna  NUMERIC(6,2),
    mortalidade_cv       NUMERIC(6,2),
    mortalidade_hospitalar NUMERIC(5,2),
    nascidos_vivos  INTEGER,
    partos_cesareos_pct NUMERIC(5,2),
    dengue_inc_100k NUMERIC(8,2),
    malaria_casos   INTEGER,
    tuberculose_inc NUMERIC(8,2),
    prev_diabetes   NUMERIC(5,2),
    prev_hipertensao NUMERIC(5,2),
    cob_vacinal_sarampo NUMERIC(5,2),
    cob_vacinal_polio   NUMERIC(5,2),
    cob_vacinal_penta   NUMERIC(5,2),
    cob_vacinal_infantil NUMERIC(5,2),
    fonte           TEXT DEFAULT 'SIM/SINASC/SINAN/PNI'
);""",
]))

blocos.append(("BLOCO 9 - Scores", [
    """CREATE TABLE scores_municipio (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    score_v3        NUMERIC(5,2),
    classificacao   TEXT,
    comp_deficit_leitos NUMERIC(5,2),
    comp_uti        NUMERIC(5,2),
    comp_esf        NUMERIC(5,2),
    comp_receita    NUMERIC(5,2),
    comp_fila       NUMERIC(5,2),
    comp_dengue     NUMERIC(5,2),
    comp_glosa      NUMERIC(5,2),
    comp_vacinal    NUMERIC(5,2),
    comp_idh_bonus  NUMERIC(5,2),
    deserto_tipo    SMALLINT,
    versao_calculo  TEXT,
    UNIQUE(municipio_ibge, competencia_id)
);""",
    """CREATE TABLE scores_uf (
    id              SERIAL PRIMARY KEY,
    uf              CHAR(2) NOT NULL REFERENCES ufs(sigla),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    score_v2        NUMERIC(5,2),
    idhh            NUMERIC(5,2),
    idhh_financeiro NUMERIC(5,2),
    idhh_qualidade  NUMERIC(5,2),
    idhh_eficiencia NUMERIC(5,2),
    idhh_acesso     NUMERIC(5,2),
    idhh_cobertura  NUMERIC(5,2),
    ieo             NUMERIC(5,2),
    classificacao   TEXT,
    UNIQUE(uf, competencia_id)
);""",
]))

blocos.append(("BLOCO 10 - Alertas", [
    """CREATE TABLE alertas (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) REFERENCES municipios(ibge),
    uf              CHAR(2) REFERENCES ufs(sigla),
    competencia_id  INTEGER NOT NULL REFERENCES competencias(id),
    tipo            TEXT NOT NULL,
    gravidade       TEXT NOT NULL,
    descricao       TEXT NOT NULL,
    base_legal      TEXT,
    valor_referencia NUMERIC(14,2),
    resolvido       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_alertas_tipo ON alertas(tipo);
CREATE INDEX idx_alertas_gravidade ON alertas(gravidade);""",
]))

blocos.append(("BLOCO 11 - Amazonas piloto", [
    """CREATE TABLE am_execucao_orcamentaria (
    id              SERIAL PRIMARY KEY,
    ano             SMALLINT NOT NULL,
    unidade_gestora TEXT NOT NULL,
    codigo_ug       TEXT,
    empenhado       NUMERIC(14,2),
    liquidado       NUMERIC(14,2),
    pago            NUMERIC(14,2),
    tipo_despesa    TEXT,
    risco           TEXT,
    fonte           TEXT DEFAULT 'SEFAZ-AM/SIAFE'
);""",
    """CREATE TABLE am_organizacoes_sociais (
    id              SERIAL PRIMARY KEY,
    nome            TEXT NOT NULL,
    cnpj            CHAR(14),
    unidades_geridas TEXT,
    ano             SMALLINT NOT NULL,
    valor_contrato  NUMERIC(14,2),
    valor_empenhado NUMERIC(14,2),
    metricas_sgc    BOOLEAN DEFAULT FALSE,
    status          TEXT,
    observacao      TEXT
);""",
    """CREATE TABLE am_glosas_unidade (
    id              SERIAL PRIMARY KEY,
    estabelecimento_cnes CHAR(7),
    nome_unidade    TEXT NOT NULL,
    ano             SMALLINT NOT NULL,
    base_aih_valor  NUMERIC(14,2),
    glosa_pct       NUMERIC(5,3),
    glosa_valor     NUMERIC(14,2),
    recuperavel     NUMERIC(14,2),
    roi_12m         NUMERIC(14,2),
    score_pareto    NUMERIC(5,2)
);""",
    """CREATE TABLE am_fila_sisreg (
    id              SERIAL PRIMARY KEY,
    municipio_ibge  CHAR(7) NOT NULL REFERENCES municipios(ibge),
    competencia_id  INTEGER REFERENCES competencias(id),
    fila_total      INTEGER DEFAULT 0,
    espera_dias     INTEGER,
    especialidade   TEXT,
    fonte           TEXT DEFAULT 'SISREG/SES-AM'
);""",
    """CREATE TABLE am_risco_erario (
    id              SERIAL PRIMARY KEY,
    categoria       TEXT NOT NULL,
    descricao       TEXT,
    base_valor      NUMERIC(14,2),
    pct_risco_min   NUMERIC(5,2),
    pct_risco_max   NUMERIC(5,2),
    risco_min       NUMERIC(14,2),
    risco_max       NUMERIC(14,2),
    confianca       TEXT,
    acao_recomendada TEXT,
    prazo           TEXT,
    ano             SMALLINT NOT NULL
);""",
]))

blocos.append(("BLOCO 12 - Series temporais", [
    """CREATE TABLE series_cnes (
    id              SERIAL PRIMARY KEY,
    uf              CHAR(2) NOT NULL REFERENCES ufs(sigla),
    ano             SMALLINT NOT NULL,
    mes             SMALLINT NOT NULL,
    leitos_sus      INTEGER,
    leitos_uti      INTEGER,
    medicos_sus     INTEGER,
    enfermeiros     INTEGER,
    equipes_esf     INTEGER,
    estabelecimentos INTEGER,
    caps_total      INTEGER,
    fonte           TEXT DEFAULT 'CNES/MS',
    UNIQUE(uf, ano, mes)
);
CREATE INDEX idx_series_uf_periodo ON series_cnes(uf, ano, mes);""",
]))

blocos.append(("BLOCO 13 - Perfis de acesso", [
    """CREATE TABLE perfis_acesso (
    id              TEXT PRIMARY KEY,
    nome            TEXT NOT NULL,
    descricao       TEXT,
    modulos         TEXT[] NOT NULL
);""",
    """INSERT INTO perfis_acesso VALUES
('controle',    'Controle e Auditoria',         'TCE, TCU, MP, CGE, CES',
    ARRAY['nacional','alertas','oss','financeiro','cockpit','benchmarking','sih','icsap','mapa','agente']),
('gestao',      'Gestão Estadual e Municipal',  'Secretários de saúde, gestores SUS',
    ARRAY['nacional','deficit','desertos','projecao','eficiencia','raps','icsap','infraestrutura','series','acesso','mapa','agente']),
('legislativo', 'Legislativo e Fiscalização',   'Deputados, senadores, CPIs',
    ARRAY['nacional','score','benchmarking','deficit','desertos','infraestrutura','epidemiologia','alertas','financeiro','sih','icsap','mapa','agente']),
('federal',     'Federal e Institucional',      'Ministério da Saúde, CONASS, CONASEMS',
    ARRAY['nacional','cockpit','idhh','qualidade','epidemiologia','cronicas','benchmarking','series','eficiencia','mapa','agente']),
('completo',    'Modo Completo (EMET)',         'Todos os módulos — uso interno',
    ARRAY['ALL']);""",
    """CREATE TABLE usuarios_dmd (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_id         UUID UNIQUE,
    nome            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    organizacao     TEXT,
    perfil_id       TEXT NOT NULL REFERENCES perfis_acesso(id),
    ufs_permitidas  CHAR(2)[],
    ativo           BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    ultimo_acesso   TIMESTAMPTZ
);""",
]))

blocos.append(("BLOCO 14 - Triggers", [
    """CREATE OR REPLACE FUNCTION calcular_indicadores_leitos()
RETURNS TRIGGER AS $$
DECLARE
    pop INTEGER;
BEGIN
    SELECT populacao INTO pop FROM municipios WHERE ibge = NEW.municipio_ibge;
    IF pop > 0 THEN
        NEW.leitos_por_1k := ROUND(NEW.leitos_sus::NUMERIC / pop * 1000, 3);
        NEW.uti_por_100k := ROUND(
            (COALESCE(NEW.leitos_uti_adulto,0) + COALESCE(NEW.leitos_uti_neonatal,0) + COALESCE(NEW.leitos_uti_pediatrico,0))::NUMERIC
            / pop * 100000, 2
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;""",
    """CREATE TRIGGER trg_calc_leitos
    BEFORE INSERT OR UPDATE ON leitos
    FOR EACH ROW EXECUTE FUNCTION calcular_indicadores_leitos();""",
    """CREATE OR REPLACE FUNCTION gerar_alerta_sm()
RETURNS TRIGGER AS $$
DECLARE
    pop INTEGER;
BEGIN
    SELECT populacao INTO pop FROM municipios WHERE ibge = NEW.municipio_ibge;
    IF pop > 20000 AND NEW.caps_total = 0 AND NEW.psiq_habilitados = 0 THEN
        NEW.alerta_fiscal := TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;""",
    """CREATE TRIGGER trg_alerta_sm
    BEFORE INSERT OR UPDATE ON saude_mental
    FOR EACH ROW EXECUTE FUNCTION gerar_alerta_sm();""",
    """CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;""",
    """CREATE TRIGGER trg_municipios_updated
    BEFORE UPDATE ON municipios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();""",
]))

blocos.append(("BLOCO 15 - Sementes", [
    """INSERT INTO regioes_brasil VALUES
(1, 'Norte', 'NO'),
(2, 'Nordeste', 'NE'),
(3, 'Sudeste', 'SE'),
(4, 'Sul', 'SU'),
(5, 'Centro-Oeste', 'CO');""",
    """INSERT INTO fontes (sigla, nome, orgao, frequencia) VALUES
('CNES',    'Cadastro Nacional de Estabelecimentos de Saúde', 'MS/DATASUS', 'mensal'),
('SIH',     'Sistema de Informações Hospitalares',            'MS/DATASUS', 'mensal'),
('SIA',     'Sistema de Informações Ambulatoriais',           'MS/DATASUS', 'mensal'),
('SIOPS',   'Sistema de Info. Orçamentos Públicos em Saúde',  'MS/SCTIE',  'anual'),
('FNS',     'Fundo Nacional de Saúde',                         'MS',        'anual'),
('IBGE',    'Instituto Brasileiro de Geografia e Estatística', 'IBGE',      'anual'),
('SIM',     'Sistema de Informações sobre Mortalidade',        'MS/SVS',    'anual'),
('SINASC',  'Sistema de Info. sobre Nascidos Vivos',           'MS/SVS',    'anual'),
('SINAN',   'Sistema de Info. Agravos de Notificação',         'MS/SVS',    'anual'),
('PNI',     'Programa Nacional de Imunizações',                'MS/CGPNI',  'anual'),
('eGestor', 'e-Gestor Atenção Básica',                         'MS/DAB',    'mensal'),
('PREVINE', 'Previne Brasil',                                   'MS',        'quadrimestral'),
('SISREG',  'Sistema de Regulação',                             'MS/DRAC',   'mensal'),
('SEFAZ-AM','Secretaria de Fazenda do Amazonas',               'SEFAZ-AM',  'anual'),
('SIAFE',   'Sistema Integrado de Administração Financeira',   'SEFAZ-AM',  'mensal'),
('DATASUS', 'Departamento de Informática do SUS',              'MS',        'variável');""",
]))

# ============================================================
# EXECUTAR
# ============================================================
print("\n=== EXECUTANDO BLOCOS ===")
erros = []
total_stmts = 0
ok_stmts = 0

for nome, stmts in blocos:
    bloco_ok = True
    for i, sql in enumerate(stmts):
        total_stmts += 1
        ok, result = run_sql(sql, f"{nome} [{i+1}/{len(stmts)}]")
        if ok:
            ok_stmts += 1
        else:
            bloco_ok = False
            erros.append((nome, i+1, result))
            print(f"  ERRO {nome} stmt {i+1}: {result[:150]}")
        time.sleep(0.3)  # rate limit
    status = "OK" if bloco_ok else "PARCIAL"
    print(f"  {nome}: {status}")

print(f"\nStatements: {ok_stmts}/{total_stmts} OK")

# ============================================================
# VERIFICACAO
# ============================================================
print("\n=== VERIFICACAO FINAL ===")

ok, body = run_sql("""SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;""")
if ok:
    tabelas = json.loads(body) if isinstance(body, str) else body
    nomes = [r["table_name"] for r in tabelas] if isinstance(tabelas, list) else []
    print(f"\nTabelas ({len(nomes)}):")
    for t in nomes:
        print(f"  - {t}")

ok, body = run_sql("""SELECT
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE') as tabelas,
    (SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='public') as triggers,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public') as indices;""")
if ok:
    counts = json.loads(body) if isinstance(body, str) else body
    if isinstance(counts, list) and counts:
        c = counts[0]
        print(f"\nResumo: {c['tabelas']} tabelas | {c['triggers']} triggers | {c['indices']} indices")

for table, label in [("regioes_brasil", "regioes"), ("fontes", "fontes"), ("perfis_acesso", "perfis")]:
    ok, body = run_sql(f"SELECT COUNT(*) as n FROM {table};")
    if ok:
        data = json.loads(body) if isinstance(body, str) else body
        n = data[0]["n"] if isinstance(data, list) and data else "?"
        print(f"  {label}: {n} registros")

if erros:
    print(f"\n!!! {len(erros)} statement(s) com erro")
    for nome, idx, err in erros:
        print(f"  {nome} #{idx}: {err[:120]}")
else:
    print("\nSchema criado com sucesso! Zero erros.")
