#!/usr/bin/env python3
"""
DMD Saude Brasil — Gera index_supabase.html a partir de index.html

Remove variaveis de dados embarcadas (~3.8 MB) e substitui por
conexao ao Supabase PostgreSQL via API REST.

Uso:
    python pipeline/scripts/build_supabase_dashboard.py
"""

import re
import os
import sys

SUPA_URL = "https://xxckbdilszvfmzyoquze.supabase.co"
SUPA_KEY = "sb_publishable_6zHUr_Olsac5o7dMc_LLug_2tK7boQu"

# ── Bloco JS a injetar no <head> ──────────────────────────────

SUPABASE_HEAD_SCRIPT = f'''
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
// ══════════════════════════════════════════════════════════════
// DMD SAUDE BRASIL — CONEXAO SUPABASE (anon key — segura para frontend)
// ══════════════════════════════════════════════════════════════
var SUPA_URL = '{SUPA_URL}';
var SUPA_KEY = '{SUPA_KEY}';
var _db = supabase.createClient(SUPA_URL, SUPA_KEY);
var _cache = {{}};

// Verificar conexao ao inicializar
(async function() {{
  try {{
    var r = await _db.from('municipios').select('ibge', {{ count: 'exact', head: true }});
    var el = document.getElementById('db-status');
    if (el) {{
      if (r.count > 0) {{
        el.textContent = 'Banco ativo — ' + r.count.toLocaleString('pt-BR') + ' municipios — Supabase';
        el.style.color = '#00C6BD';
      }} else {{
        el.textContent = 'Banco vazio — verifique carga';
        el.style.color = '#F59E0B';
      }}
    }}
  }} catch(e) {{
    var el = document.getElementById('db-status');
    if (el) {{ el.textContent = 'Banco offline'; el.style.color = '#E74C3C'; }}
  }}
}})();
</script>
'''

# ── Nova loadAllMunis() que busca do Supabase ─────────────────

NEW_LOAD_ALL_MUNIS = '''async function loadAllMunis() {
  // [SUPABASE] Busca dados do PostgreSQL em vez de descomprimir base64
  if (window.MUNIS && Object.keys(window.MUNIS).length > 1) return window.MUNIS;
  try {
    console.log('[DMD Supabase] Carregando municipios...');
    var t0 = Date.now();

    // Buscar municipios com joins nas tabelas relacionadas
    var { data: munis, error: e1 } = await _db.from('municipios')
      .select('ibge, nome, uf, populacao, idh, latitude, longitude, faixa_pop')
      .order('uf');
    if (e1) throw e1;

    // Buscar dados relacionados em paralelo
    var [leitos, scores, sm, ap, epi] = await Promise.all([
      _db.from('leitos').select('municipio_ibge, leitos_sus, leitos_por_1k, deficit_leitos, deficit_uti, leitos_uti_adulto, leitos_psiquiatricos'),
      _db.from('scores_municipio').select('municipio_ibge, score_v3, classificacao, comp_deficit_leitos, comp_uti, comp_esf, comp_receita'),
      _db.from('saude_mental').select('municipio_ibge, caps_total, caps_tipo, caps_nomes, srt, leitos_psiq_hg, psiq_cadastrados, psiq_habilitados, status_habilitacao, cobertura_raps, alerta_fiscal, nota_habilitacao, fonte'),
      _db.from('atencao_primaria').select('municipio_ibge, cobertura_esf_pct, equipes_esf, acs_total'),
      _db.from('epidemiologia').select('municipio_ibge, mortalidade_infantil, mortalidade_materna, mortalidade_cv, dengue_inc_100k, nascidos_vivos, prev_diabetes, prev_hipertensao, cob_vacinal_sarampo, cob_vacinal_infantil')
    ]);

    // Indexar por ibge para joins rapidos
    var idx = {};
    function indexar(result, prefix) {
      if (result.data) result.data.forEach(function(r) {
        var k = r.municipio_ibge;
        if (!idx[k]) idx[k] = {};
        Object.keys(r).forEach(function(f) {
          if (f !== 'municipio_ibge') idx[k][prefix + f] = r[f];
        });
      });
    }
    indexar(leitos, '');
    indexar(scores, '');
    indexar(sm, '');
    indexar(ap, '');
    indexar(epi, '');

    // Montar MUNIS no formato original {UF: [array de municipios]}
    var result = {};
    munis.forEach(function(m) {
      var uf = m.uf;
      if (!result[uf]) result[uf] = [];
      var r = idx[m.ibge] || {};

      result[uf].push({
        // Campos basicos (alias curtos usados pelo dashboard)
        uf: uf,
        m: m.nome,
        pop: m.populacao || 0,
        idh: m.idh || 0,
        lat: m.latitude,
        lon: m.longitude,
        ibge_cod: m.ibge,
        porte: m.faixa_pop || '',
        mac: '', // macrorregiao — nao temos no banco ainda
        regiao: '',

        // Leitos (alias curtos)
        l: r.leitos_por_1k || 0,
        leitos_sus: r.leitos_sus || 0,
        leitos_sus_1k: r.leitos_por_1k || 0,
        u: 0, // UTI taxa — calculado
        dl: r.deficit_leitos || 0,
        du: r.deficit_uti || 0,
        lq: r.leitos_psiquiatricos || 0,

        // ESF / Atencao primaria
        e: r.cobertura_esf_pct || 0,
        esf_equipes: r.equipes_esf || 0,
        agentes_acs: r.acs_total || 0,

        // Scores
        score_v3: r.score_v3 || 0,
        score_v3_d1: r.comp_deficit_leitos || 0,
        score_v3_d2: r.comp_uti || 0,
        score_v3_d3: r.comp_esf || 0,
        score_v3_d4: r.comp_receita || 0,
        risco_v3: r.classificacao || '',
        crit: r.classificacao || '',

        // Saude mental
        caps: r.caps_total || 0,
        caps_tipo: r.caps_tipo || '',
        caps_nomes: r.caps_nomes || '',
        srt: r.srt || 0,
        leitos_hg: r.leitos_psiq_hg || 0,
        psiq_cad: r.psiq_cadastrados || 0,
        psiq_hab: r.psiq_habilitados || 0,
        psiq_status: r.status_habilitacao || '',
        cobertura_raps: r.cobertura_raps ? 'SIM' : 'NAO',
        alerta_fiscal: r.alerta_fiscal || false,
        nota_habilitacao: r.nota_habilitacao || '',
        fonte_sm: r.fonte || 'CNES',

        // Epidemiologia
        mi: r.mortalidade_infantil || 0,
        mm: r.mortalidade_materna || 0,
        mort_cv_100k: r.mortalidade_cv || 0,
        dengue_inc: r.dengue_inc_100k || 0,
        nascimentos: r.nascidos_vivos || 0,
        prev_dm_pct: r.prev_diabetes || 0,
        prev_has_pct: r.prev_hipertensao || 0,
        cob_sarampo: r.cob_vacinal_sarampo || 0,
        cobertura_vacinal: r.cob_vacinal_infantil || 0,

        // Orcamento (placeholder — dados nao carregados ainda)
        g: 0,
        siops_desp: 0,

        // Flags (calculados)
        f: 0,
        n_flags: 0,
        flags: [],
        vulnerab: 0,
        prioridade: 0,
        recup_r: 0,
        score_mun: r.score_v3 || 0,
        risco_mun: r.classificacao || '',
      });
    });

    window.MUNIS = result;
    var total = Object.values(result).reduce(function(s, a) { return s + a.length; }, 0);
    console.log('[DMD Supabase] ' + total + ' municipios carregados em ' + (Date.now() - t0) + 'ms');
    return result;
  } catch(e) {
    console.error('[DMD Supabase] loadAllMunis erro:', e);
    // Fallback: tentar base64 se existir
    if (typeof MUNIS_FULL_B64 !== 'undefined' && MUNIS_FULL_B64) {
      console.warn('[DMD Supabase] Fallback para MUNIS_FULL_B64');
      return _loadAllMunis_b64();
    }
    return null;
  }
}'''

# ── Indicador de conexao HTML ─────────────────────────────────

DB_STATUS_HTML = '''<div id="db-status" style="position:fixed;bottom:8px;right:8px;background:rgba(13,27,42,0.9);color:#5E90AA;padding:4px 10px;border-radius:4px;font-size:10px;font-family:'Space Grotesk',sans-serif;z-index:9999;border:1px solid #162E4A;">Conectando...</div>'''

# ── CSS de loading ────────────────────────────────────────────

LOADING_CSS = '''
.supa-loading{text-align:center;padding:40px;color:#00C6BD;font-size:14px;font-family:'Space Grotesk',sans-serif;}
.supa-loading::before{content:'';display:block;width:32px;height:32px;border:3px solid #1B2A3D;border-top-color:#00C6BD;border-radius:50%;margin:0 auto 12px;animation:spin .8s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
'''

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    src = "index.html"
    dst = "index_supabase.html"

    if not os.path.exists(src):
        print(f"ERRO: {src} nao encontrado")
        sys.exit(1)

    with open(src, "r", encoding="utf-8") as f:
        html = f.read()

    original_size = len(html)
    print(f"Fonte: {src} ({original_size / 1024 / 1024:.1f} MB)")

    # ── 1. Remover MUNIS_FULL_B64 (maior: ~1.55 MB em 1 linha) ──
    html = re.sub(
        r'var MUNIS_FULL_B64\s*=\s*"[^"]*";',
        '// [SUPABASE] var MUNIS_FULL_B64 removida — dados agora via Supabase PostgreSQL\nvar MUNIS_FULL_B64 = "";',
        html
    )
    print("  MUNIS_FULL_B64: removida")

    # ── 2. Remover _LT_ALL (~1.98 MB em 1 linha) ──
    html = re.sub(
        r'var _LT_ALL\s*=\s*\[.*?\];',
        '// [SUPABASE] var _LT_ALL removida — dados via Supabase\nvar _LT_ALL = [];',
        html,
        flags=re.DOTALL,
        count=1,
    )
    print("  _LT_ALL: removida")

    # ── 3. Remover window.MORT_MUN (~122 KB) ──
    html = re.sub(
        r'window\.MORT_MUN\s*=\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\};',
        '// [SUPABASE] window.MORT_MUN removida\nwindow.MORT_MUN={};',
        html,
        count=1,
    )
    print("  MORT_MUN: removida")

    # ── 4. Remover window.SIH_MUN (~121 KB) ──
    html = re.sub(
        r'window\.SIH_MUN\s*=\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\};',
        '// [SUPABASE] window.SIH_MUN removida\nwindow.SIH_MUN={};',
        html,
        count=1,
    )
    print("  SIH_MUN: removida")

    # ── 5. Remover window.SERIES_NAC (~7.5 KB) ──
    html = re.sub(
        r'window\.SERIES_NAC\s*=\s*\{.*?\};',
        '// [SUPABASE] window.SERIES_NAC removida\nwindow.SERIES_NAC={};',
        html,
        flags=re.DOTALL,
        count=1,
    )
    print("  SERIES_NAC: removida")

    # ── 6. Remover _SER_MUNI (~40 KB) ──
    html = re.sub(
        r'var _SER_MUNI\s*=\s*\[.*?\];',
        '// [SUPABASE] var _SER_MUNI removida\nvar _SER_MUNI = [];',
        html,
        flags=re.DOTALL,
        count=1,
    )
    print("  _SER_MUNI: removida")

    # ── 7. Substituir loadAllMunis() ──
    # Renomear a original para _loadAllMunis_b64 (fallback) e injetar a nova
    html = html.replace(
        "async function loadAllMunis() {",
        "async function _loadAllMunis_b64() {"
    )
    # Inserir nova loadAllMunis antes da renomeada
    html = html.replace(
        "async function _loadAllMunis_b64() {",
        NEW_LOAD_ALL_MUNIS + "\n\n// Fallback original (base64) — usado se Supabase offline\nasync function _loadAllMunis_b64() {"
    )
    print("  loadAllMunis: substituida por versao Supabase")

    # ── 8. Injetar Supabase client no <head> ──
    # Adicionar antes do primeiro <script> no head
    html = html.replace(
        "</head>",
        f"<style>{LOADING_CSS}</style>\n{SUPABASE_HEAD_SCRIPT}\n</head>"
    )
    print("  Supabase client: injetado no <head>")

    # ── 9. Adicionar indicador de conexao antes de </body> ──
    html = html.replace("</body>", f"{DB_STATUS_HTML}\n</body>")
    print("  Indicador de conexao: adicionado")

    # ── 10. Atualizar titulo da pagina ──
    html = html.replace(
        "DMD SAUDE BRASIL V43",
        "DMD SAUDE BRASIL V43 — Supabase"
    )

    # ── Salvar ──
    with open(dst, "w", encoding="utf-8") as f:
        f.write(html)

    final_size = len(html)
    saved = original_size - final_size
    print(f"\nOutput: {dst}")
    print(f"  Original: {original_size / 1024 / 1024:.1f} MB")
    print(f"  Supabase: {final_size / 1024 / 1024:.1f} MB")
    print(f"  Reducao:  {saved / 1024 / 1024:.1f} MB ({saved * 100 / original_size:.0f}%)")


if __name__ == "__main__":
    main()
