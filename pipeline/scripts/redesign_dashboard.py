#!/usr/bin/env python3
"""
DMD Saude Brasil — Redesign do Dashboard
Aplica transformacoes visuais cirurgicas no index_supabase.html
Fases: A (Hero + Nav), B (Hierarquia Visual), C (IA + Print)

NOTA: O dashboard usa innerHTML em varios pontos para renderizar
conteudo gerado internamente (KPIs, tabelas, chat). Isso e seguro
neste contexto pois nao ha input de usuario externo — todos os dados
vem de fontes controladas (Supabase, MUNIS_FULL_B64).
"""
import re, sys

SRC = 'index_supabase.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

lines = html.split('\n')
print(f'[redesign] {len(lines)} linhas carregadas')

# ═══════════════════════════════════════════════════════════════
# FASE A1 — Inserir CSS redesign apos linha 495 (</style> do shell)
# ═══════════════════════════════════════════════════════════════

CSS_REDESIGN = '''<style id="css-redesign">
/* ═══ HERO LANDING ═══ */
.hero-section{max-width:1200px;margin:0 auto;padding:40px 24px 60px}
.hero-header{text-align:center;margin-bottom:36px}
.hero-header h1{font-family:'Space Grotesk',sans-serif;font-size:clamp(28px,4vw,42px);font-weight:700;color:#fff;margin:0}
.hero-header h1 em{color:#00C6BD;font-style:normal}
.hero-header .hero-sub{font-family:'DM Sans',sans-serif;font-size:15px;color:#8899AA;margin-top:8px}
.hero-header .hero-badge{display:inline-block;background:rgba(0,198,189,.1);color:#00C6BD;font-size:11px;font-weight:600;padding:4px 14px;border-radius:20px;margin-top:12px;letter-spacing:.5px;font-family:'Space Grotesk',sans-serif}

.hero-map-container{margin:0 auto 32px;border-radius:12px;overflow:hidden;border:1px solid rgba(0,198,189,.15);background:#0A1628}
#hero-map{height:380px;background:#0A1628}

.hero-kpi-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:40px}
.hero-kpi-card{background:#1B2A3D;border-radius:12px;padding:24px 16px;text-align:center;border-top:3px solid #00C6BD;transition:transform .2s,box-shadow .2s}
.hero-kpi-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.3)}
.hero-kpi-value{display:block;font-family:'Space Grotesk',sans-serif;font-size:clamp(24px,3vw,36px);font-weight:700;color:#fff;line-height:1.1}
.hero-kpi-label{display:block;font-size:11px;color:#8899AA;text-transform:uppercase;letter-spacing:1px;margin-top:8px;font-family:'DM Sans',sans-serif}
.hero-kpi-detail{display:block;font-size:11px;color:#5E7080;margin-top:4px}

.hero-uf-row{text-align:center;margin-bottom:36px}
.hero-uf-row label{font-family:'DM Sans',sans-serif;font-size:14px;color:#8899AA;margin-right:12px}
#hero-uf-select{background:#1B2A3D;color:#fff;border:1px solid rgba(0,198,189,.3);border-radius:8px;padding:10px 18px;font-size:14px;font-family:'DM Sans',sans-serif;cursor:pointer;min-width:260px;outline:none;transition:border-color .2s}
#hero-uf-select:focus{border-color:#00C6BD}
#hero-uf-select option{background:#1B2A3D;color:#fff}

.hero-divider{text-align:center;color:#5E7080;font-size:13px;margin:8px 0 28px;font-family:'DM Sans',sans-serif;letter-spacing:.5px}

.hero-question-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:40px}
.hero-question-card{background:#1B2A3D;border:1px solid rgba(0,198,189,.15);border-radius:12px;padding:24px 20px;cursor:pointer;transition:all .25s ease;text-align:center}
.hero-question-card:hover{border-color:#00C6BD;transform:translateY(-4px);box-shadow:0 8px 32px rgba(0,198,189,.12)}
.hq-icon{display:block;font-size:32px;margin-bottom:10px}
.hq-text{display:block;font-family:'Space Grotesk',sans-serif;font-size:15px;font-weight:700;color:#fff;margin-bottom:6px;line-height:1.3}
.hq-sub{display:block;font-size:12px;color:#8899AA;font-family:'DM Sans',sans-serif}

.hero-profiles{text-align:center;margin-bottom:24px}
.hero-profiles p{font-size:13px;color:#5E7080;margin-bottom:12px;font-family:'DM Sans',sans-serif}
.hero-profile-pills{display:flex;justify-content:center;gap:8px;flex-wrap:wrap}
.hero-profile-pill{background:transparent;border:1px solid rgba(0,198,189,.25);color:#8899AA;padding:8px 20px;border-radius:24px;cursor:pointer;font-size:12px;font-weight:600;font-family:'Space Grotesk',sans-serif;transition:all .2s;letter-spacing:.3px}
.hero-profile-pill:hover{border-color:#00C6BD;color:#00C6BD;background:rgba(0,198,189,.06)}
.hero-footer{text-align:center;font-size:11px;color:#4A5A6A;line-height:1.6;font-family:'DM Sans',sans-serif}

/* ═══ NAVEGAÇÃO 2 NÍVEIS ═══ */
#shell-nav-primary{position:sticky;top:0;z-index:2000;background:#0D1B2A;border-bottom:2px solid rgba(0,198,189,.25);display:flex;align-items:center;padding:0 20px;height:52px;gap:2px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.nav-primary-btn{font-family:'Space Grotesk',sans-serif;font-size:12px;font-weight:600;color:#8899AA;background:none;border:none;padding:14px 14px;cursor:pointer;border-bottom:3px solid transparent;transition:all .2s;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap}
.nav-primary-btn:hover{color:#fff}
.nav-primary-btn.active{color:#00C6BD;border-bottom-color:#00C6BD}
.nav-primary-home{color:#00C6BD !important;font-size:13px}

#shell-nav-sub{background:#1B2A3D;display:flex;padding:0 20px;height:42px;align-items:center;gap:6px;border-bottom:1px solid rgba(255,255,255,.04);overflow-x:auto;-webkit-overflow-scrolling:touch}
.nav-sub-btn{font-family:'DM Sans',sans-serif;font-size:12px;color:#8899AA;background:none;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;transition:all .2s;white-space:nowrap}
.nav-sub-btn:hover{color:#fff;background:rgba(255,255,255,.04)}
.nav-sub-btn.active{background:rgba(0,198,189,.1);color:#00C6BD}

/* ═══ HIERARQUIA VISUAL (FASE B) ═══ */
.shell-module.active{display:block;max-width:1400px;margin:0 auto;padding:24px 28px}
#mod-mapa.active{max-width:none;padding:0}
#mod-welcome.active{max-width:none;padding:0}
.contexto-banner{padding:14px 20px;border-radius:10px;margin:0 0 24px;font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px}
.contexto-banner.cb-critico{background:rgba(231,76,60,.1);border-left:4px solid #E74C3C;color:#E74C3C}
.contexto-banner.cb-alerta{background:rgba(243,156,18,.1);border-left:4px solid #F39C12;color:#F39C12}
.contexto-banner.cb-bom{background:rgba(46,204,113,.1);border-left:4px solid #2ECC71;color:#2ECC71}

/* ═══ MÓDULO IA DEDICADO (FASE C) ═══ */
#mod-ia .ia-hero{text-align:center;padding:40px 20px 20px}
#mod-ia .ia-hero h2{font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:700;color:#fff;margin:0 0 8px}
#mod-ia .ia-hero p{font-size:14px;color:#8899AA;margin:0}
.ia-sug-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;max-width:800px;margin:24px auto}
.ia-sug-card{background:#1B2A3D;border:1px solid rgba(0,198,189,.15);border-radius:10px;padding:14px 18px;cursor:pointer;font-size:13px;color:#ddd;font-family:'DM Sans',sans-serif;transition:all .2s;text-align:left}
.ia-sug-card:hover{border-color:#00C6BD;background:rgba(0,198,189,.06)}
.ia-sug-card span{margin-right:8px}
.ia-chat-embed{max-width:800px;margin:0 auto;padding:0 20px 40px}
.ia-msgs{background:#0A1628;border-radius:12px;padding:20px;min-height:280px;max-height:450px;overflow-y:auto;margin-bottom:16px;border:1px solid rgba(255,255,255,.04)}
.ia-msg-user{background:rgba(0,198,189,.1);border-radius:12px 12px 4px 12px;padding:12px 16px;margin:8px 0 8px 60px;font-size:14px;color:#fff;font-family:'DM Sans',sans-serif}
.ia-msg-bot{background:#1B2A3D;border-radius:12px 12px 12px 4px;padding:12px 16px;margin:8px 60px 8px 0;font-size:14px;color:#ddd;border-left:3px solid #00C6BD;font-family:'DM Sans',sans-serif}
.ia-input-row{display:flex;gap:12px}
#ia-input{flex:1;background:#1B2A3D;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:14px 18px;color:#fff;font-size:14px;font-family:'DM Sans',sans-serif;outline:none;resize:none;min-height:48px}
#ia-input:focus{border-color:#00C6BD}
.ia-send-btn{background:#00C6BD;color:#0D1B2A;border:none;border-radius:10px;padding:14px 24px;font-weight:700;cursor:pointer;font-family:'Space Grotesk',sans-serif;font-size:14px;transition:background .2s}
.ia-send-btn:hover{background:#00E5D9}

/* ═══ LEAFLET TOOLTIP ═══ */
.hero-uf-tooltip{background:#1B2A3D !important;color:#fff !important;border:1px solid #00C6BD !important;border-radius:6px !important;font-family:'DM Sans',sans-serif !important;font-size:12px !important;padding:6px 10px !important;box-shadow:0 4px 12px rgba(0,0,0,.4) !important}
.hero-uf-tooltip::before{border-top-color:#00C6BD !important}

/* ═══ PRINT (FASE C) ═══ */
@media print{
  #shell-topbar,#shell-badge,#shell-nav-primary,#shell-nav-sub,
  #shell-modnav,#btn-trocar-perfil,#dmd-fab,#dmd-panel,
  #mod-welcome,#db-status,.contexto-banner{display:none !important}
  body{background:#fff !important;color:#000 !important}
  .shell-module.active{display:block !important;max-width:100%;padding:10px}
  .panel,.kstrip>div{border:1px solid #ddd;background:#f8f9fa !important}
  .kv,.kpi-value{color:#000 !important}
  canvas{max-width:100% !important;height:auto !important}
}

/* ═══ RESPONSIVE ═══ */
@media(max-width:768px){
  .hero-kpi-strip{grid-template-columns:repeat(2,1fr)}
  .hero-question-grid{grid-template-columns:1fr}
  .ia-sug-grid{grid-template-columns:1fr}
  #shell-nav-primary{height:auto;flex-wrap:wrap;padding:8px 12px;gap:0}
  .nav-primary-btn{padding:10px 10px;font-size:11px}
  .hero-section{padding:24px 16px 40px}
  #hero-map{height:260px}
}
@media(max-width:480px){
  .hero-kpi-strip{grid-template-columns:1fr 1fr}
  .hero-kpi-card{padding:16px 10px}
  .hero-kpi-value{font-size:22px}
}
</style>'''

# Encontrar a linha </style> do shell CSS (proximo a linha 495)
idx_css_end = None
for i, line in enumerate(lines):
    if i > 480 and i < 510 and line.strip() == '</style>':
        idx_css_end = i
        break

if idx_css_end is None:
    print('[ERRO] Nao encontrou </style> do shell CSS')
    sys.exit(1)

css_lines = CSS_REDESIGN.strip().split('\n')
lines = lines[:idx_css_end+1] + [''] + css_lines + [''] + lines[idx_css_end+1:]
print(f'[A1] CSS redesign inserido apos linha {idx_css_end+1} ({len(css_lines)} linhas)')


# ═══════════════════════════════════════════════════════════════
# FASE A3 — Inserir nova nav + esconder modnav antigo
# ═══════════════════════════════════════════════════════════════

NAV_HTML = '''<!-- ═══ NAVEGAÇÃO REDESIGN ═══ -->
<div id="shell-nav-primary" style="display:none">
  <button class="nav-primary-btn nav-primary-home" data-group="home" onclick="goHome()">&#8592; Início</button>
  <button class="nav-primary-btn" data-group="nacional" onclick="showGroup('nacional')">Nacional</button>
  <button class="nav-primary-btn" data-group="estado" onclick="showGroup('estado')">Meu Estado</button>
  <button class="nav-primary-btn" data-group="comparar" onclick="showGroup('comparar')">Comparar</button>
  <button class="nav-primary-btn" data-group="alertas" onclick="showGroup('alertas')">Alertas</button>
  <button class="nav-primary-btn" data-group="ia" onclick="navigateToModule('mod-ia')">Agente IA</button>
  <button class="nav-primary-btn" data-group="piloto" onclick="showGroup('piloto')">AM Piloto</button>
</div>
<div id="shell-nav-sub" style="display:none"></div>'''

idx_modnav = None
for i, line in enumerate(lines):
    if 'id="shell-modnav"' in line:
        idx_modnav = i
        break

if idx_modnav is None:
    print('[ERRO] Nao encontrou shell-modnav')
    sys.exit(1)

nav_lines = NAV_HTML.strip().split('\n')
lines = lines[:idx_modnav] + nav_lines + [''] + lines[idx_modnav:]
print(f'[A3a] Nav primaria inserida antes de shell-modnav (linha {idx_modnav})')

# Esconder modnav antigo
for i, line in enumerate(lines):
    if 'id="shell-modnav"' in line and 'style=' not in line:
        lines[i] = line.replace('id="shell-modnav"', 'id="shell-modnav" style="display:none"')
        print(f'[A3b] shell-modnav escondido na linha {i}')
        break


# ═══════════════════════════════════════════════════════════════
# FASE A2 — Substituir mod-welcome por Hero
# ═══════════════════════════════════════════════════════════════

UF_OPTIONS = '''<option value="">Brasil — Visão Nacional</option>
      <option value="AC">Acre</option><option value="AL">Alagoas</option>
      <option value="AP">Amapá</option><option value="AM">Amazonas</option>
      <option value="BA">Bahia</option><option value="CE">Ceará</option>
      <option value="DF">Distrito Federal</option><option value="ES">Espírito Santo</option>
      <option value="GO">Goiás</option><option value="MA">Maranhão</option>
      <option value="MT">Mato Grosso</option><option value="MS">Mato Grosso do Sul</option>
      <option value="MG">Minas Gerais</option><option value="PA">Pará</option>
      <option value="PB">Paraíba</option><option value="PR">Paraná</option>
      <option value="PE">Pernambuco</option><option value="PI">Piauí</option>
      <option value="RJ">Rio de Janeiro</option><option value="RN">Rio Grande do Norte</option>
      <option value="RS">Rio Grande do Sul</option><option value="RO">Rondônia</option>
      <option value="RR">Roraima</option><option value="SC">Santa Catarina</option>
      <option value="SP">São Paulo</option><option value="SE">Sergipe</option>
      <option value="TO">Tocantins</option>'''

HERO_HTML = f'''<div id="mod-welcome" class="shell-module active">
<div class="hero-section">
  <div class="hero-header">
    <h1><em>DMD</em> Saúde Brasil</h1>
    <p class="hero-sub">Inteligência em saúde pública &middot; 5.569 municípios &middot; 27 estados &middot; 115 indicadores</p>
    <span class="hero-badge">V44 &middot; CNES 02/2026 &middot; 16 FONTES FEDERAIS</span>
  </div>

  <div class="hero-map-container">
    <div id="hero-map"></div>
  </div>

  <div class="hero-kpi-strip">
    <div class="hero-kpi-card">
      <span class="hero-kpi-value">5.569</span>
      <span class="hero-kpi-label">Municípios</span>
      <span class="hero-kpi-detail">analisados em tempo real</span>
    </div>
    <div class="hero-kpi-card">
      <span class="hero-kpi-value">R$ 226 bi</span>
      <span class="hero-kpi-label">Orçamento SUS</span>
      <span class="hero-kpi-detail">LOA 2025 &middot; 27 estados</span>
    </div>
    <div class="hero-kpi-card">
      <span class="hero-kpi-value" style="color:#E74C3C">R$ 6,9 bi</span>
      <span class="hero-kpi-label">Glosas Evitáveis</span>
      <span class="hero-kpi-detail">estimativa nacional</span>
    </div>
    <div class="hero-kpi-card">
      <span class="hero-kpi-value" style="color:#2ECC71">89,4%</span>
      <span class="hero-kpi-label">Cobertura ESF</span>
      <span class="hero-kpi-detail">maior ESF nacional</span>
    </div>
  </div>

  <div class="hero-uf-row">
    <label>&#128269; Selecione seu estado para começar:</label>
    <select id="hero-uf-select" onchange="heroSelectUF(this.value)">
      {UF_OPTIONS}
    </select>
  </div>

  <div class="hero-divider">ou explore por tema:</div>

  <div class="hero-question-grid">
    <div class="hero-question-card" onclick="heroNavigate('mod-nacional')">
      <span class="hq-icon">&#128176;</span>
      <span class="hq-text">Onde estou perdendo dinheiro?</span>
      <span class="hq-sub">Glosas, oportunidades e ROI</span>
    </div>
    <div class="hero-question-card" onclick="heroNavigate('mod-infra')">
      <span class="hq-icon">&#127973;</span>
      <span class="hq-text">Minha rede é suficiente?</span>
      <span class="hq-sub">Leitos, médicos, ESF e déficits</span>
    </div>
    <div class="hero-question-card" onclick="heroNavigate('mod-sv3')">
      <span class="hq-icon">&#9888;&#65039;</span>
      <span class="hq-text">Quais municípios estão em risco?</span>
      <span class="hq-sub">Alertas, scores e vulnerabilidade</span>
    </div>
    <div class="hero-question-card" onclick="heroNavigate('mod-benchmark')">
      <span class="hq-icon">&#128202;</span>
      <span class="hq-text">Como me comparo com outros?</span>
      <span class="hq-sub">Rankings e benchmarks entre UFs</span>
    </div>
    <div class="hero-question-card" onclick="heroNavigate('mod-saudemental')">
      <span class="hq-icon">&#129504;</span>
      <span class="hq-text">Saúde mental e CAPS</span>
      <span class="hq-sub">Cobertura RAPS e desertos</span>
    </div>
    <div class="hero-question-card" onclick="heroNavigate('mod-ia')">
      <span class="hq-icon">&#129302;</span>
      <span class="hq-text">Pergunte ao Agente IA</span>
      <span class="hq-sub">Consulte qualquer dado</span>
    </div>
  </div>

  <div class="hero-profiles">
    <p>Selecione seu perfil de acesso:</p>
    <div class="hero-profile-pills">
      <button class="hero-profile-pill" onclick="setProfile('controle')">&#128269; Controle</button>
      <button class="hero-profile-pill" onclick="setProfile('gestao')">&#127973; Gestão</button>
      <button class="hero-profile-pill" onclick="setProfile('legislativo')">&#9878;&#65039; Legislativo</button>
      <button class="hero-profile-pill" onclick="setProfile('federal')">&#127963;&#65039; Federal</button>
      <button class="hero-profile-pill" onclick="setProfile('emet')">&#1488;&#1502;&#1514; Completo</button>
    </div>
  </div>

  <div class="hero-footer">
    EMET Gestão Brasil Ltda &middot; Dados 100% públicos e auditáveis<br>
    DATASUS &middot; IBGE &middot; SIOPS &middot; CNES &middot; FNS &middot; RNDS &middot; e-Gestor AB &middot; SIM &middot; SINASC &middot; SINAN
  </div>
</div>
</div>'''

# Encontrar mod-welcome
idx_welcome_start = None
for i, line in enumerate(lines):
    if 'id="mod-welcome"' in line and 'shell-module' in line:
        idx_welcome_start = i
        break

if idx_welcome_start is None:
    print('[ERRO] mod-welcome nao encontrado')
    sys.exit(1)

# Encontrar fechamento contando divs
depth = 0
idx_welcome_end = None
for i in range(idx_welcome_start, len(lines)):
    depth += lines[i].count('<div')
    depth -= lines[i].count('</div>')
    if depth <= 0 and i > idx_welcome_start:
        idx_welcome_end = i
        break

if idx_welcome_end is None:
    print('[ERRO] Fechamento de mod-welcome nao encontrado')
    sys.exit(1)

hero_lines = HERO_HTML.split('\n')
lines = lines[:idx_welcome_start] + hero_lines + lines[idx_welcome_end+1:]
print(f'[A2] mod-welcome substituido por hero ({idx_welcome_end - idx_welcome_start + 1} linhas -> {len(hero_lines)} linhas)')


# ═══════════════════════════════════════════════════════════════
# FASE A4/A5/A6/A7 — JS roteamento + mapa hero
# ═══════════════════════════════════════════════════════════════

JS_ROUTING = r'''
// ═══ REDESIGN: Navegacao por grupos + Hero Map ═══

var _NAV_GROUPS = {
  nacional: {
    label: 'Nacional',
    modules: [
      {id:'mod-nacional', label:'Painel Nacional'},
      {id:'mod-cockpit', label:'Cockpit Executivo'},
      {id:'mod-financeiro', label:'Financeiro SIH'},
      {id:'mod-scorev2', label:'Score V2'}
    ]
  },
  estado: {
    label: 'Meu Estado',
    modules: [
      {id:'mod-infra', label:'Infraestrutura'},
      {id:'mod-leitos', label:'D\u00e9ficit Leitos'},
      {id:'mod-desertos', label:'Desertos Sanit\u00e1rios'},
      {id:'mod-saudemental', label:'Sa\u00fade Mental'},
      {id:'mod-epidemiologia', label:'Epidemiologia'},
      {id:'mod-acesso', label:'Acesso e Regula\u00e7\u00e3o'}
    ]
  },
  comparar: {
    label: 'Comparar',
    modules: [
      {id:'mod-benchmark', label:'Benchmarking'},
      {id:'mod-eficiencia', label:'Efici\u00eancia'},
      {id:'mod-idhh', label:'IDH Hospitalar'},
      {id:'mod-qualidade', label:'Qualidade'},
      {id:'mod-series', label:'S\u00e9ries CNES'}
    ]
  },
  alertas: {
    label: 'Alertas',
    modules: [
      {id:'mod-sv3', label:'Alertas V3'},
      {id:'mod-dc', label:'Doen\u00e7as Cr\u00f4nicas'},
      {id:'mod-sih', label:'SIH/Interna\u00e7\u00f5es'},
      {id:'mod-icsap', label:'ICSAP'},
      {id:'mod-projecao', label:'Proje\u00e7\u00e3o 2030'},
      {id:'mod-mapa', label:'Mapa'}
    ]
  },
  piloto: {
    label: 'AM Piloto',
    modules: [
      {id:'mod-am', label:'Amazonas'},
      {id:'mod-oss', label:'OSS-AM'}
    ]
  }
};

function showGroup(groupKey) {
  var group = _NAV_GROUPS[groupKey];
  if (!group) return;
  document.querySelectorAll('.nav-primary-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.group === groupKey);
  });
  var subNav = document.getElementById('shell-nav-sub');
  subNav.style.display = 'flex';
  subNav.textContent = '';
  group.modules.forEach(function(m, idx) {
    var btn = document.createElement('button');
    btn.className = 'nav-sub-btn';
    btn.textContent = m.label;
    btn.onclick = function() {
      document.querySelectorAll('.nav-sub-btn').forEach(function(b){ b.classList.remove('active'); });
      btn.classList.add('active');
      switchMod(m.id);
    };
    subNav.appendChild(btn);
  });
  switchMod(group.modules[0].id);
  subNav.querySelector('.nav-sub-btn').classList.add('active');
}

function goHome() {
  document.getElementById('shell-nav-sub').style.display = 'none';
  document.querySelectorAll('.nav-primary-btn').forEach(function(b){ b.classList.remove('active'); });
  voltarWelcome();
  setTimeout(function(){ initHeroMap(); }, 200);
}

function navigateToModule(modId) {
  if (modId === 'mod-ia') {
    var nav = document.getElementById('shell-nav-primary');
    if (nav.style.display === 'none') {
      nav.style.display = '';
      document.getElementById('shell-nav-sub').style.display = 'none';
    }
    document.querySelectorAll('.nav-primary-btn').forEach(function(b){
      b.classList.toggle('active', b.dataset.group === 'ia');
    });
    switchMod('mod-ia');
    return;
  }
  for (var key in _NAV_GROUPS) {
    var mods = _NAV_GROUPS[key].modules;
    for (var i = 0; i < mods.length; i++) {
      if (mods[i].id === modId) {
        showGroup(key);
        switchMod(modId);
        var subBtns = document.querySelectorAll('.nav-sub-btn');
        subBtns.forEach(function(b, idx) {
          b.classList.toggle('active', idx === i);
        });
        return;
      }
    }
  }
  switchMod(modId);
}

function heroNavigate(modId) {
  var saved = localStorage.getItem('dmd_profile');
  if (!saved) {
    setProfile('emet');
  } else {
    document.getElementById('shell-nav-primary').style.display = '';
  }
  setTimeout(function(){ navigateToModule(modId); }, 50);
}

function heroSelectUF(uf) {
  if (!uf) return;
  var saved = localStorage.getItem('dmd_profile');
  if (!saved) setProfile('emet');
  else document.getElementById('shell-nav-primary').style.display = '';
  setTimeout(function(){ showGroup('estado'); }, 50);
}

// ═══ Hero Map (Leaflet Choropleth) ═══
var _heroMapInit = false;
var heroMap = null;

function initHeroMap() {
  if (_heroMapInit) return;
  if (typeof L === 'undefined') { setTimeout(initHeroMap, 500); return; }
  var el = document.getElementById('hero-map');
  if (!el || el.offsetParent === null) return;
  _heroMapInit = true;

  heroMap = L.map('hero-map', {
    center: [-14.5, -52], zoom: 4,
    zoomControl: false, attributionControl: false,
    dragging: true, scrollWheelZoom: false, doubleClickZoom: false
  });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd', maxZoom: 8
  }).addTo(heroMap);

  fetch('https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson')
    .then(function(r){ return r.json(); })
    .then(function(geo) {
      var siglaMap = {'Acre':'AC','Alagoas':'AL','Amap\u00e1':'AP','Amazonas':'AM','Bahia':'BA',
        'Cear\u00e1':'CE','Distrito Federal':'DF','Esp\u00edrito Santo':'ES','Goi\u00e1s':'GO','Maranh\u00e3o':'MA',
        'Mato Grosso':'MT','Mato Grosso do Sul':'MS','Minas Gerais':'MG','Par\u00e1':'PA',
        'Para\u00edba':'PB','Paran\u00e1':'PR','Pernambuco':'PE','Piau\u00ed':'PI','Rio de Janeiro':'RJ',
        'Rio Grande do Norte':'RN','Rio Grande do Sul':'RS','Rond\u00f4nia':'RO','Roraima':'RR',
        'Santa Catarina':'SC','S\u00e3o Paulo':'SP','Sergipe':'SE','Tocantins':'TO'};
      var colors = ['#E74C3C','#F39C12','#F1C40F','#2ECC71','#00C6BD'];
      L.geoJSON(geo, {
        style: function(feature) {
          var name = feature.properties.name || '';
          var uf = siglaMap[name] || name;
          var hash = 0;
          for(var c=0;c<uf.length;c++) hash += uf.charCodeAt(c);
          return {
            fillColor: colors[hash % colors.length],
            weight: 1.5, opacity: 0.8, color: '#0D1B2A', fillOpacity: 0.65
          };
        },
        onEachFeature: function(feature, layer) {
          var name = feature.properties.name || '';
          var uf = siglaMap[name] || name;
          layer.bindTooltip('<b>' + uf + '</b> \u2014 ' + name, {
            sticky: true, className: 'hero-uf-tooltip'
          });
          layer.on('click', function() {
            var sel = document.getElementById('hero-uf-select');
            if (sel) sel.value = uf;
            heroSelectUF(uf);
          });
        }
      }).addTo(heroMap);
    })
    .catch(function(e) { console.warn('[hero-map] GeoJSON falhou:', e); });
}

document.addEventListener('DOMContentLoaded', function() {
  setTimeout(initHeroMap, 800);
});
'''

# Encontrar switchMod e seu fechamento
idx_switchmod_end = None
for i, line in enumerate(lines):
    if 'function switchMod(id, btn)' in line:
        depth = 0
        for j in range(i, min(i+100, len(lines))):
            depth += lines[j].count('{')
            depth -= lines[j].count('}')
            if depth <= 0 and j > i:
                idx_switchmod_end = j
                break
        break

if idx_switchmod_end is None:
    print('[ERRO] Nao encontrou fim de switchMod()')
    sys.exit(1)

# Encontrar </script> apos switchMod
idx_script_end = None
for i in range(idx_switchmod_end, min(idx_switchmod_end + 5, len(lines))):
    if '</script>' in lines[i]:
        idx_script_end = i
        break

if idx_script_end is None:
    print('[ERRO] Nao encontrou </script> apos switchMod')
    sys.exit(1)

js_lines = JS_ROUTING.strip().split('\n')
lines = lines[:idx_script_end] + js_lines + [''] + lines[idx_script_end:]
print(f'[A4/A6] JS roteamento + hero map inserido ({len(js_lines)} linhas)')


# ═══════════════════════════════════════════════════════════════
# FASE A5 — Modificar setProfile e voltarWelcome
# ═══════════════════════════════════════════════════════════════

for i, line in enumerate(lines):
    if "document.getElementById('shell-modnav').style.display = ''" in line and 'btn-trocar' not in line and 'none' not in line:
        lines[i] = line.replace(
            "document.getElementById('shell-modnav').style.display = ''",
            "document.getElementById('shell-modnav').style.display = 'none'; document.getElementById('shell-nav-primary').style.display = ''"
        )
        print(f'[A5a] setProfile: modnav->nav-primary na linha {i}')
        break

# voltarWelcome — adicionar esconder nav-primary e sub
for i, line in enumerate(lines):
    if "function voltarWelcome()" in line:
        # Encontrar a linha que esconde shell-modnav dentro desta funcao
        for j in range(i, min(i+20, len(lines))):
            if "shell-modnav" in lines[j] and "none" in lines[j]:
                lines[j] = lines[j].rstrip() + "\n  document.getElementById('shell-nav-primary').style.display = 'none';\n  document.getElementById('shell-nav-sub').style.display = 'none';"
                print(f'[A5b] voltarWelcome: esconder nav-primary+sub na linha {j}')
                break
        break


# ═══════════════════════════════════════════════════════════════
# FASE C1 — Criar modulo mod-ia
# ═══════════════════════════════════════════════════════════════

MOD_IA_HTML = '''
<!-- ═══ MÓDULO IA DEDICADO ═══ -->
<div id="mod-ia" class="shell-module">
  <div class="ia-hero">
    <h2>&#129302; Agente DMD — Inteligência Artificial</h2>
    <p>Pergunte qualquer coisa sobre os dados de saúde do Brasil.<br>O agente consulta o banco com 5.569 municípios em tempo real.</p>
  </div>
  <div class="ia-sug-grid">
    <div class="ia-sug-card" onclick="iaSugClick('Quais os 5 municípios do AM com maior déficit de leitos?')">
      <span>&#127973;</span> Quais os 5 municípios do AM com maior déficit de leitos?
    </div>
    <div class="ia-sug-card" onclick="iaSugClick('Compare a cobertura ESF do Amazonas com a meta do Previne Brasil')">
      <span>&#128202;</span> Compare a cobertura ESF do Amazonas com a meta Previne Brasil
    </div>
    <div class="ia-sug-card" onclick="iaSugClick('Quanto o Maranhão perde em glosas evitáveis por ano?')">
      <span>&#128176;</span> Quanto o Maranhão perde em glosas evitáveis por ano?
    </div>
    <div class="ia-sug-card" onclick="iaSugClick('Quais estados têm mais municípios sem CAPS?')">
      <span>&#129504;</span> Quais estados têm mais municípios sem CAPS?
    </div>
  </div>
  <div class="ia-chat-embed">
    <div id="ia-msgs" class="ia-msgs"></div>
    <div class="ia-input-row">
      <textarea id="ia-input" rows="1" placeholder="Analise, compare, audite... pergunte em linguagem natural"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();iaSend()}"></textarea>
      <button class="ia-send-btn" onclick="iaSend()">Enviar &#10148;</button>
    </div>
  </div>
</div>

<script>
/* Modulo IA dedicado — conecta ao DMD existente */
function iaSugClick(text) {
  var input = document.getElementById('ia-input');
  if (input) { input.value = text; iaSend(); }
}
function iaSend() {
  var input = document.getElementById('ia-input');
  if (!input || !input.value.trim()) return;
  var text = input.value.trim();
  input.value = '';
  var msgs = document.getElementById('ia-msgs');
  var userDiv = document.createElement('div');
  userDiv.className = 'ia-msg-user';
  userDiv.textContent = text;
  msgs.appendChild(userDiv);
  msgs.scrollTop = msgs.scrollHeight;
  /* Delegar ao DMD existente */
  if (typeof DMD !== 'undefined' && DMD.send) {
    var dmdInput = document.getElementById('dmd-input');
    if (dmdInput) {
      dmdInput.value = text;
      DMD.send();
      /* Sincronizar resposta */
      var checkResp = setInterval(function(){
        var dmdMsgs = document.getElementById('dmd-msgs');
        if (dmdMsgs && dmdMsgs.lastElementChild) {
          var last = dmdMsgs.lastElementChild;
          if (last.className && last.className.indexOf('bot') >= 0) {
            var botDiv = document.createElement('div');
            botDiv.className = 'ia-msg-bot';
            botDiv.textContent = last.textContent;
            msgs.appendChild(botDiv);
            msgs.scrollTop = msgs.scrollHeight;
            clearInterval(checkResp);
          }
        }
      }, 1000);
      setTimeout(function(){ clearInterval(checkResp); }, 30000);
    }
  } else {
    var botDiv = document.createElement('div');
    botDiv.className = 'ia-msg-bot';
    botDiv.textContent = 'Agente IA inicializando... Tente novamente em instantes.';
    msgs.appendChild(botDiv);
    msgs.scrollTop = msgs.scrollHeight;
  }
}
</script>
'''

# Encontrar o FAB do agente para inserir mod-ia ANTES
idx_fab = None
for i, line in enumerate(lines):
    if 'id="dmd-fab"' in line:
        idx_fab = i
        break

if idx_fab:
    ia_lines = MOD_IA_HTML.strip().split('\n')
    lines = lines[:idx_fab] + ia_lines + [''] + lines[idx_fab:]
    print(f'[C1] Modulo mod-ia inserido antes da linha {idx_fab} ({len(ia_lines)} linhas)')

    # C2 — Converter FAB em atalho
    for i in range(idx_fab + len(ia_lines), min(idx_fab + len(ia_lines) + 10, len(lines))):
        if 'id="dmd-fab"' in lines[i] and 'DMD.toggle()' in lines[i]:
            lines[i] = lines[i].replace('DMD.toggle()', "navigateToModule('mod-ia')")
            print(f'[C2] FAB onclick alterado na linha {i}')
            break


# ═══════════════════════════════════════════════════════════════
# SALVAR
# ═══════════════════════════════════════════════════════════════

output = '\n'.join(lines)
with open(SRC, 'w', encoding='utf-8') as f:
    f.write(output)

new_lines = len(lines)
old_lines = len(html.split('\n'))
print(f'\n[DONE] {SRC} salvo ({len(output)} bytes, {new_lines} linhas)')
print(f'Crescimento: +{new_lines - old_lines} linhas')
