#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  EMET DMD GESTÃO BRASIL — Gerador Dashboard v5.1                        ║
║  Script 03 — Lê dashboard_data.json e gera HTML autocontido            ║
║  Output: pages/index.html (GitHub Pages)                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import os, sys, json, logging
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "dashboard_data.json"
OUT_FILE  = ROOT / "pages" / "index.html"
LOG_DIR   = ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_DIR / "dashboard.log", encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("dashboard_gen")

def carregar_dados(log) -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    log.warning("dashboard_data.json não encontrado — usando dados padrão v37")
    # Dados hardcoded do banco v37 como fallback
    return {
        "meta": {"versao": "5.1", "gerado_em": datetime.now().isoformat(),
                 "total_municipios": 5569, "fonte": "DMD_v37"},
        "kpis": {"total_municipios": 5569, "populacao_total": 207208235,
                 "total_caps": 3738, "total_srt": 343,
                 "total_leitos_sus": 424350, "total_alertas": 325},
        "ufs": [
            {"uf":"AC","municipios":22,"pop":910871,"caps":17,"srt":3,"leitos_sus":754,"alertas_fiscais":4,"score_medio":54.9},
            {"uf":"AL","municipios":102,"pop":3256292,"caps":84,"srt":6,"leitos_sus":3973,"alertas_fiscais":11,"score_medio":60.0},
            {"uf":"AM","municipios":62,"pop":4318905,"caps":36,"srt":8,"leitos_sus":5991,"alertas_fiscais":8,"score_medio":46.9},
            {"uf":"AP","municipios":16,"pop":794618,"caps":10,"srt":1,"leitos_sus":798,"alertas_fiscais":1,"score_medio":52.3},
            {"uf":"BA","municipios":417,"pop":13918639,"caps":311,"srt":12,"leitos_sus":16475,"alertas_fiscais":72,"score_medio":58.9},
            {"uf":"CE","municipios":184,"pop":8833000,"caps":145,"srt":8,"leitos_sus":10200,"alertas_fiscais":22,"score_medio":59.1},
            {"uf":"DF","municipios":1,"pop":3015268,"caps":16,"srt":2,"leitos_sus":3500,"alertas_fiscais":0,"score_medio":55.2},
            {"uf":"ES","municipios":78,"pop":3831000,"caps":57,"srt":4,"leitos_sus":4500,"alertas_fiscais":0,"score_medio":56.8},
            {"uf":"GO","municipios":246,"pop":6950000,"caps":130,"srt":5,"leitos_sus":8200,"alertas_fiscais":0,"score_medio":53.1},
            {"uf":"MA","municipios":217,"pop":6580000,"caps":127,"srt":8,"leitos_sus":6300,"alertas_fiscais":35,"score_medio":57.4},
            {"uf":"MG","municipios":853,"pop":21300000,"caps":551,"srt":22,"leitos_sus":45000,"alertas_fiscais":0,"score_medio":55.3},
            {"uf":"MS","municipios":79,"pop":2778000,"caps":60,"srt":3,"leitos_sus":3800,"alertas_fiscais":0,"score_medio":53.8},
            {"uf":"MT","municipios":141,"pop":3500000,"caps":75,"srt":4,"leitos_sus":4200,"alertas_fiscais":1,"score_medio":48.6},
            {"uf":"PA","municipios":144,"pop":8100000,"caps":107,"srt":8,"leitos_sus":9200,"alertas_fiscais":20,"score_medio":48.1},
            {"uf":"PB","municipios":223,"pop":3970000,"caps":148,"srt":5,"leitos_sus":5200,"alertas_fiscais":18,"score_medio":60.3},
            {"uf":"PE","municipios":185,"pop":9200000,"caps":184,"srt":11,"leitos_sus":14000,"alertas_fiscais":30,"score_medio":61.2},
            {"uf":"PI","municipios":224,"pop":3280000,"caps":115,"srt":4,"leitos_sus":3800,"alertas_fiscais":28,"score_medio":57.8},
            {"uf":"PR","municipios":399,"pop":11430000,"caps":197,"srt":12,"leitos_sus":17000,"alertas_fiscais":0,"score_medio":58.5},
            {"uf":"RJ","municipios":92,"pop":16500000,"caps":275,"srt":28,"leitos_sus":35000,"alertas_fiscais":0,"score_medio":52.1},
            {"uf":"RN","municipios":167,"pop":3420000,"caps":110,"srt":6,"leitos_sus":4600,"alertas_fiscais":14,"score_medio":59.7},
            {"uf":"RO","municipios":52,"pop":1600000,"caps":30,"srt":2,"leitos_sus":1800,"alertas_fiscais":8,"score_medio":50.2},
            {"uf":"RR","municipios":15,"pop":614000,"caps":10,"srt":1,"leitos_sus":650,"alertas_fiscais":3,"score_medio":47.8},
            {"uf":"RS","municipios":497,"pop":11300000,"caps":231,"srt":16,"leitos_sus":22000,"alertas_fiscais":0,"score_medio":57.8},
            {"uf":"SC","municipios":295,"pop":7200000,"caps":197,"srt":9,"leitos_sus":14500,"alertas_fiscais":0,"score_medio":57.0},
            {"uf":"SE","municipios":75,"pop":2270000,"caps":44,"srt":3,"leitos_sus":3500,"alertas_fiscais":12,"score_medio":60.5},
            {"uf":"SP","municipios":645,"pop":44025364,"caps":564,"srt":81,"leitos_sus":130712,"alertas_fiscais":1,"score_medio":52.4},
            {"uf":"TO","municipios":139,"pop":1586859,"caps":42,"srt":3,"leitos_sus":1082,"alertas_fiscais":10,"score_medio":50.4},
        ]
    }

def gerar_html(dados: dict, log) -> None:
    kpis  = dados.get("kpis", {})
    meta  = dados.get("meta", {})
    ufs   = dados.get("ufs", [])
    gerado= meta.get("gerado_em", datetime.now().isoformat())[:10]

    ufs_json = json.dumps(ufs, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>EMET DMD Gestão Brasil — Dashboard v5.1</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"/>
<style>
  :root {{ --primary:#1a3a5c; --accent:#e74c3c; --success:#27ae60; --warning:#f39c12; }}
  body {{ background:#f4f7fb; font-family:'Segoe UI',sans-serif; }}
  .navbar {{ background:var(--primary)!important; }}
  .kpi-card {{ border-left:4px solid var(--primary); transition:.2s; }}
  .kpi-card:hover {{ transform:translateY(-3px); box-shadow:0 8px 20px rgba(0,0,0,.12); }}
  .kpi-value {{ font-size:2rem; font-weight:700; color:var(--primary); }}
  .kpi-label {{ font-size:.8rem; color:#6c757d; text-transform:uppercase; letter-spacing:1px; }}
  .alert-badge {{ background:var(--accent); color:#fff; border-radius:50px; padding:2px 10px; font-size:.75rem; }}
  .tab-content {{ padding:20px 0; }}
  .uf-bar {{ height:20px; background:linear-gradient(90deg,var(--primary),#4a90d9); border-radius:4px; }}
  footer {{ background:var(--primary); color:#fff; padding:20px; margin-top:40px; }}
  .status-dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
  .dot-green {{ background:#27ae60; }}
  .dot-yellow {{ background:#f39c12; }}
  .dot-red {{ background:#e74c3c; }}
</style>
</head>
<body>

<nav class="navbar navbar-dark mb-4">
  <div class="container-fluid">
    <span class="navbar-brand fw-bold">🏥 EMET DMD Gestão Brasil</span>
    <span class="text-white-50 small">Dashboard Nacional v5.1 · Atualizado: {gerado} · Fonte: {meta.get("fonte","DMD v37 + DATASUS")}</span>
  </div>
</nav>

<div class="container-fluid px-4">

  <!-- Alertas críticos -->
  <div class="alert alert-danger d-flex align-items-center mb-3" role="alert">
    <strong>🚨 Alertas Ativos:</strong>&nbsp;
    <span>{kpis.get("total_alertas",325)} municípios sem CAPS (pop &gt;20k) · {round(kpis.get("total_caps",3738)/5569*100,1)}% cobertura RAPS nacional</span>
    <span class="ms-auto badge bg-danger">{gerado}</span>
  </div>

  <!-- KPI Cards -->
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-3 col-xl-2">
      <div class="card kpi-card h-100 p-3">
        <div class="kpi-value">{kpis.get("total_municipios",5569):,}</div>
        <div class="kpi-label">Municípios</div>
      </div>
    </div>
    <div class="col-6 col-md-3 col-xl-2">
      <div class="card kpi-card h-100 p-3">
        <div class="kpi-value">{kpis.get("populacao_total",207208235)/1e6:.1f}M</div>
        <div class="kpi-label">Habitantes</div>
      </div>
    </div>
    <div class="col-6 col-md-3 col-xl-2">
      <div class="card kpi-card h-100 p-3">
        <div class="kpi-value">{kpis.get("total_caps",3738):,}</div>
        <div class="kpi-label">CAPS Ativos</div>
      </div>
    </div>
    <div class="col-6 col-md-3 col-xl-2">
      <div class="card kpi-card h-100 p-3">
        <div class="kpi-value">{kpis.get("total_srt",343)}</div>
        <div class="kpi-label">SRT Residências</div>
      </div>
    </div>
    <div class="col-6 col-md-3 col-xl-2">
      <div class="card kpi-card h-100 p-3">
        <div class="kpi-value">{kpis.get("total_leitos_sus",424350):,}</div>
        <div class="kpi-label">Leitos SUS</div>
      </div>
    </div>
    <div class="col-6 col-md-3 col-xl-2">
      <div class="card kpi-card h-100 p-3 border-danger">
        <div class="kpi-value text-danger">{kpis.get("total_alertas",325)}</div>
        <div class="kpi-label">Alertas Fiscais</div>
      </div>
    </div>
  </div>

  <!-- Tabs -->
  <ul class="nav nav-tabs" id="mainTabs">
    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-ufs">📊 Por UF</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-caps">🧠 CAPS/SRT</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-leitos">🛏️ Leitos SUS</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-alertas">⚠️ Alertas</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-pipeline">🔄 Pipeline</button></li>
  </ul>

  <div class="tab-content" id="mainTabsContent">

    <!-- Tab UFs -->
    <div class="tab-pane fade show active" id="tab-ufs">
      <div class="row g-3">
        <div class="col-md-8">
          <div class="card p-3">
            <h6 class="mb-3">Score Médio de Saúde por UF</h6>
            <canvas id="chartUFscore" height="320"></canvas>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card p-3">
            <h6 class="mb-3">Distribuição CAPS por Região</h6>
            <canvas id="chartRegioes" height="300"></canvas>
          </div>
        </div>
      </div>
      <!-- Tabela UFs -->
      <div class="card mt-3">
        <div class="card-header">Indicadores por Estado (27 UFs)</div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0" id="tabelaUFs">
              <thead class="table-dark">
                <tr><th>UF</th><th>Municípios</th><th>População</th><th>CAPS</th><th>SRT</th><th>Leitos SUS</th><th>Alertas</th><th>Score</th></tr>
              </thead>
              <tbody id="tbodyUFs"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab CAPS/SRT -->
    <div class="tab-pane fade" id="tab-caps">
      <div class="row g-3">
        <div class="col-md-6">
          <div class="card p-3">
            <h6>CAPS por UF</h6>
            <canvas id="chartCaps" height="380"></canvas>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card p-3">
            <h6>SRT (Residências Terapêuticas) por UF</h6>
            <canvas id="chartSRT" height="380"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab Leitos -->
    <div class="tab-pane fade" id="tab-leitos">
      <div class="card p-3">
        <h6>Leitos SUS por UF</h6>
        <canvas id="chartLeitos" height="300"></canvas>
      </div>
    </div>

    <!-- Tab Alertas -->
    <div class="tab-pane fade" id="tab-alertas">
      <div class="card p-3">
        <div class="alert alert-warning">
          <strong>⚠️ {kpis.get("total_alertas",325)} municípios</strong> com população &gt;20.000 hab. sem CAPS ativo registrado no CNES.
        </div>
        <h6>Alertas Fiscais por UF</h6>
        <canvas id="chartAlertas" height="280"></canvas>
      </div>
    </div>

    <!-- Tab Pipeline -->
    <div class="tab-pane fade" id="tab-pipeline">
      <div class="row g-3">
        <div class="col-md-6">
          <div class="card p-3">
            <h6>🔄 Status do Pipeline de Atualização</h6>
            <table class="table table-sm">
              <tr><td>Versão Dashboard</td><td><strong>v5.1</strong></td></tr>
              <tr><td>Fonte Principal</td><td>DMD v37 + CNES DATASUS</td></tr>
              <tr><td>Última Atualização</td><td>{gerado}</td></tr>
              <tr><td>Banco de Municípios</td><td>{kpis.get("total_municipios",5569):,} municípios</td></tr>
              <tr><td>FTP DATASUS</td><td><span class="status-dot dot-green"></span> Configurado</td></tr>
              <tr><td>GitHub Actions</td><td><span class="status-dot dot-green"></span> Ativo (dia 18/mês)</td></tr>
              <tr><td>GitHub Pages</td><td><span class="status-dot dot-green"></span> Deploy automático</td></tr>
              <tr><td>PySUS</td><td><span class="status-dot dot-yellow"></span> Requer certificado</td></tr>
            </table>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card p-3">
            <h6>📋 Cronograma de Cobertura CNES</h6>
            <div class="mb-2">
              <small class="text-muted">Norte (7 UFs) — Abril/2026</small>
              <div class="progress mb-1"><div class="progress-bar" style="width:11.6%">11.6%</div></div>
            </div>
            <div class="mb-2">
              <small class="text-muted">Nordeste (9 UFs) — Maio/2026</small>
              <div class="progress mb-1"><div class="progress-bar bg-warning" style="width:0%">0%</div></div>
            </div>
            <div class="mb-2">
              <small class="text-muted">Sudeste+Sul (7 UFs) — Junho/2026</small>
              <div class="progress mb-1"><div class="progress-bar bg-warning" style="width:0%">0%</div></div>
            </div>
            <div class="mb-2">
              <small class="text-muted">Centro-Oeste (4 UFs) — Julho/2026</small>
              <div class="progress mb-1"><div class="progress-bar bg-warning" style="width:0%">0%</div></div>
            </div>
            <hr/>
            <div>
              <small class="text-muted">Meta Nacional 100% — Julho/2026</small>
              <div class="progress"><div class="progress-bar bg-success" style="width:11.6%">11.6%</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div><!-- /.tab-content -->
</div><!-- /.container-fluid -->

<footer class="text-center">
  <small>EMET DMD Gestão Brasil · Dashboard Nacional v5.1 · {gerado} · Dados: DATASUS/CNES + IBGE · <a href="https://github.com/kbarrosfinal-netizen/dmd-saude-brasil" class="text-white">GitHub</a></small>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
const UFS = {ufs_json};

// Preencher tabela
const tbody = document.getElementById('tbodyUFs');
UFS.forEach(u => {{
  const score = u.score_medio || 0;
  const badge = score >= 60 ? 'success' : score >= 52 ? 'warning' : 'danger';
  tbody.innerHTML += `<tr>
    <td><strong>${{u.uf}}</strong></td>
    <td>${{u.municipios}}</td>
    <td>${{(u.pop/1e6).toFixed(2)}}M</td>
    <td>${{u.caps}}</td>
    <td>${{u.srt}}</td>
    <td>${{(u.leitos_sus||0).toLocaleString('pt-BR')}}</td>
    <td>${{u.alertas_fiscais > 0 ? '<span class="alert-badge">' + u.alertas_fiscais + '</span>' : '—'}}</td>
    <td><span class="badge bg-${{badge}}">${{score.toFixed(1)}}</span></td>
  </tr>`;
}});

// Chart Score por UF
new Chart(document.getElementById('chartUFscore'), {{
  type: 'bar',
  data: {{
    labels: UFS.map(u => u.uf),
    datasets: [{{
      label: 'Score Médio v3',
      data: UFS.map(u => u.score_medio || 0),
      backgroundColor: UFS.map(u => (u.score_medio||0) >= 60 ? '#27ae60' : (u.score_medio||0) >= 52 ? '#f39c12' : '#e74c3c'),
    }}]
  }},
  options: {{ plugins: {{ legend: {{ display:false }} }}, scales: {{ y: {{ min:35, max:75 }} }} }}
}});

// Chart Regiões donut
const regioes = {{
  'Norte': UFS.filter(u=>['AC','AM','AP','PA','RO','RR','TO'].includes(u.uf)).reduce((a,u)=>a+u.caps,0),
  'Nordeste': UFS.filter(u=>['AL','BA','CE','MA','PB','PE','PI','RN','SE'].includes(u.uf)).reduce((a,u)=>a+u.caps,0),
  'Sudeste': UFS.filter(u=>['ES','MG','RJ','SP'].includes(u.uf)).reduce((a,u)=>a+u.caps,0),
  'Sul': UFS.filter(u=>['PR','RS','SC'].includes(u.uf)).reduce((a,u)=>a+u.caps,0),
  'C-Oeste': UFS.filter(u=>['DF','GO','MS','MT'].includes(u.uf)).reduce((a,u)=>a+u.caps,0),
}};
new Chart(document.getElementById('chartRegioes'), {{
  type: 'doughnut',
  data: {{
    labels: Object.keys(regioes),
    datasets: [{{ data: Object.values(regioes), backgroundColor:['#1a3a5c','#2980b9','#27ae60','#f39c12','#8e44ad'] }}]
  }}
}});

// Chart CAPS por UF
new Chart(document.getElementById('chartCaps'), {{
  type: 'bar',
  data: {{
    labels: UFS.map(u=>u.uf),
    datasets: [{{ label:'CAPS', data:UFS.map(u=>u.caps), backgroundColor:'#2980b9' }}]
  }},
  options: {{ indexAxis:'y', plugins:{{ legend:{{display:false}} }} }}
}});

// Chart SRT
new Chart(document.getElementById('chartSRT'), {{
  type: 'bar',
  data: {{
    labels: UFS.map(u=>u.uf),
    datasets: [{{ label:'SRT', data:UFS.map(u=>u.srt), backgroundColor:'#8e44ad' }}]
  }},
  options: {{ indexAxis:'y', plugins:{{ legend:{{display:false}} }} }}
}});

// Chart Leitos
new Chart(document.getElementById('chartLeitos'), {{
  type: 'bar',
  data: {{
    labels: UFS.map(u=>u.uf),
    datasets: [{{ label:'Leitos SUS', data:UFS.map(u=>u.leitos_sus||0), backgroundColor:'#1a3a5c' }}]
  }},
  options: {{ plugins:{{ legend:{{display:false}} }} }}
}});

// Chart Alertas
const comAlertas = UFS.filter(u=>u.alertas_fiscais>0);
new Chart(document.getElementById('chartAlertas'), {{
  type:'bar',
  data:{{
    labels: comAlertas.map(u=>u.uf),
    datasets:[{{ label:'Alertas Fiscais', data:comAlertas.map(u=>u.alertas_fiscais), backgroundColor:'#e74c3c' }}]
  }},
  options:{{ plugins:{{legend:{{display:false}}}} }}
}});
</script>
</body>
</html>"""

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    log.info(f"✅ Dashboard gerado: {OUT_FILE} ({OUT_FILE.stat().st_size/1024:.1f} KB)")

def main():
    log = setup_logger()
    log.info("╔══ EMET DMD — Gerador Dashboard v5.1 ══╗")
    dados = carregar_dados(log)
    gerar_html(dados, log)
    log.info("╚══ Dashboard gerado com sucesso ══╝")
    sys.exit(0)

if __name__ == "__main__":
    main()
