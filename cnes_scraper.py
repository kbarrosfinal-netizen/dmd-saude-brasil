#!/usr/bin/env python3
"""
DMD Saude Brasil — Coletor CNES mensal via TabNet DATASUS.
Gera patch JSON para ingestao no Supabase via load_patch_to_supabase.py.

Uso:
    python cnes_scraper.py --competencia 032026
    python cnes_scraper.py --competencia 032026 --ufs AM PA RR
    python cnes_scraper.py  # usa mes anterior automaticamente
"""
import argparse, csv, datetime, hashlib, json, os, re, sys, time, unicodedata
try:
    import requests
except ImportError:
    print("ERRO: pip install requests"); sys.exit(1)

TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/estabbr.def"
TABNET_REFERER = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/estabbr.def"

# Tipos de estabelecimento no TabNet (valor do SELECT STipo_de_Estabelecimento)
# 30 = CAPS, 38 = Residencial Terapeutico (inclui SRT)
TABNET_TIPOS = {"30": "CAPS", "38": "SRT"}

# UFs no TabNet — valores sequenciais 1-27 (NAO sao codigos IBGE!)
UF_TABNET = {
    "AC":"1","AL":"2","AM":"4","AP":"3","BA":"5","CE":"6","DF":"7","ES":"8",
    "GO":"9","MA":"10","MG":"13","MS":"12","MT":"11","PA":"14","PB":"15",
    "PE":"17","PI":"18","PR":"16","RJ":"19","RN":"20","RO":"22","RR":"23",
    "RS":"21","SC":"24","SE":"26","SP":"25","TO":"27",
}
UFS_ALL = sorted(UF_TABNET.keys())

def log(msg, lvl="INFO"):
    print(f"[{datetime.datetime.now():%H:%M:%S}][{lvl}] {msg}")

def normalize(n):
    nfkd = unicodedata.normalize("NFKD", n.upper())
    return re.sub(r"[^A-Z0-9 ]","","".join(c for c in nfkd if not unicodedata.combining(c))).strip()

def load_ibge_map(path):
    mapa = {}
    if path and os.path.exists(path) and path.endswith(".json"):
        with open(path, encoding="utf-8") as f: data = json.load(f)
        if isinstance(data, list):
            for m in data:
                i7 = str(m.get("ibge",m.get("ibge_cod","")))
                if i7 and len(i7)>=6: mapa[i7[:6]]={"ibge7":i7.zfill(7),"nome":m.get("nome",m.get("m","")),"uf":m.get("uf","")}
        return mapa
    ep = os.path.join("export","export_munis_full.json")
    if os.path.exists(ep):
        with open(ep, encoding="utf-8") as f: munis = json.load(f)
        for uf, ms in munis.items():
            for m in ms:
                ir = str(m.get("ibge_cod",""))
                if "." in ir: ir = ir.split(".")[0]
                if ir and ir.isdigit() and len(ir)>=6:
                    i7 = ir.zfill(7); mapa[i7[:6]] = {"ibge7":i7,"nome":m.get("m",""),"uf":uf}
    return mapa

def competencia_to_dbf(mes, ano):
    """Converte mes/ano para nome do arquivo DBF do TabNet. Ex: 3,2026 -> stbr2603.dbf"""
    return f"stbr{str(ano)[2:]}{mes:02d}.dbf"

def build_tabnet_body(uf_tabnet_cod, tipo_cod, dbf_arquivo):
    """Constroi body do POST TabNet com nomes de campo ISO-8859-1 corretos."""
    # Nomes dos campos SELECT no formulario TabNet (ISO-8859-1)
    fields = [
        ("Linha", "Munic\xedpio"),
        ("Coluna", "--N\xe3o-Ativa--"),
        ("Incremento", "Quantidade"),
        ("Arquivos", dbf_arquivo),
        ("SRegi\xe3o", "TODAS_AS_CATEGORIAS__"),
        ("SUnidade_da_Federa\xe7\xe3o", uf_tabnet_cod),
        ("SMunic\xedpio", "TODAS_AS_CATEGORIAS__"),
        ("SMunic\xedpio_gestor", "TODAS_AS_CATEGORIAS__"),
        ("SCapital", "TODAS_AS_CATEGORIAS__"),
        ("SRegi\xe3o_de_Sa\xfade_(CIR)", "TODAS_AS_CATEGORIAS__"),
        ("SMacrorregi\xe3o_de_Sa\xfade", "TODAS_AS_CATEGORIAS__"),
        ("SMicrorregi\xe3o_IBGE", "TODAS_AS_CATEGORIAS__"),
        ("SRegi\xe3o_Metropolitana_-_RIDE", "TODAS_AS_CATEGORIAS__"),
        ("STerrit\xf3rio_da_Cidadania", "TODAS_AS_CATEGORIAS__"),
        ("SMesorregi\xe3o_PNDR", "TODAS_AS_CATEGORIAS__"),
        ("SAmaz\xf4nia_Legal", "TODAS_AS_CATEGORIAS__"),
        ("SSemi\xe1rido", "TODAS_AS_CATEGORIAS__"),
        ("SFaixa_de_Fronteira", "TODAS_AS_CATEGORIAS__"),
        ("SZona_de_Fronteira", "TODAS_AS_CATEGORIAS__"),
        ("SMunic\xedpio_de_extrema_pobreza", "TODAS_AS_CATEGORIAS__"),
        ("SEnsino/Pesquisa", "TODAS_AS_CATEGORIAS__"),
        ("SNatureza_Jur\xeddica", "TODAS_AS_CATEGORIAS__"),
        ("SEsfera_Jur\xeddica", "TODAS_AS_CATEGORIAS__"),
        ("SEsfera_Administrativa", "TODAS_AS_CATEGORIAS__"),
        ("SNatureza", "TODAS_AS_CATEGORIAS__"),
        ("STipo_de_Estabelecimento", tipo_cod),
        ("STipo_de_Gest\xe3o", "TODAS_AS_CATEGORIAS__"),
        ("STipo_de_Prestador", "TODAS_AS_CATEGORIAS__"),
        ("formato", "table"),
        ("mostre", "Mostra"),
    ]
    import urllib.parse
    parts = []
    for name, value in fields:
        enc_n = urllib.parse.quote(name, safe="/()", encoding="latin-1")
        enc_v = urllib.parse.quote(value, safe="_+()", encoding="latin-1")
        parts.append(f"{enc_n}={enc_v}")
    return "&".join(parts).encode("latin-1")

def parse_tabnet(html, uf, tipo):
    """Parse do HTML TabNet. O HTML usa tags nao fechadas (<TD> sem </TD>)."""
    res = []
    # Formato real do TabNet:
    #   <TR align="right">
    #   <TD ALIGN=LEFT>130260 MANAUS
    #   <TD>7
    # Padrao principal: TD com IBGE 6 digitos + nome, seguido de TD com numero
    for ibge, nome, cnt in re.findall(
            r'<TD[^>]*>\s*(\d{6})\s+([^<\n]+?)\s*\n\s*<TD[^>]*>\s*(\d+)',
            html, re.I):
        if nome.strip().upper() != 'TOTAL':
            res.append({"ibge6": ibge.strip(), "nome_tabnet": nome.strip(),
                         "count": int(cnt), "tipo": tipo, "uf": uf})
    if res:
        return res
    # Fallback: TDs fechadas (formato alternativo)
    for ibge, nome, cnt in re.findall(
            r'<td[^>]*>(\d{6})\s+([^<]+)</td>\s*<td[^>]*>(\d+)</td>',
            html, re.I):
        res.append({"ibge6": ibge.strip(), "nome_tabnet": nome.strip(),
                     "count": int(cnt), "tipo": tipo, "uf": uf})
    return res

def fetch_tipo(uf, tipo_cod, dbf_arquivo):
    """Faz POST ao TabNet e retorna dados parseados."""
    tipo_nome = TABNET_TIPOS[tipo_cod]
    uf_cod = UF_TABNET.get(uf, "")
    if not uf_cod:
        return {"status": "UF_INVALIDA", "data": []}
    try:
        body = build_tabnet_body(uf_cod, tipo_cod, dbf_arquivo)
        r = requests.post(TABNET_URL, data=body, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": TABNET_REFERER,
            "Content-Type": "application/x-www-form-urlencoded",
        }, timeout=45)
        if r.status_code != 200:
            return {"status": "HTTP_ERROR", "data": []}
        # Decodificar como latin-1 (charset do TabNet)
        text = r.content.decode("latin-1", errors="replace")
        parsed = parse_tabnet(text, uf, tipo_nome)
        if not parsed and len(text) > 2000:
            log(f"    {tipo_nome}: HTML {len(text)} bytes mas 0 resultados", "WARN")
        elif not parsed and len(text) < 2000:
            log(f"    {tipo_nome}: resposta pequena ({len(text)} bytes) — possivel formulario", "WARN")
        return {"status": "OK", "data": parsed}
    except requests.Timeout:
        log(f"    {tipo_nome}: TIMEOUT", "WARN")
        return {"status": "TIMEOUT", "data": []}
    except Exception as e:
        log(f"    {tipo_nome}: ERRO — {e}", "ERROR")
        return {"status": "ERROR", "data": []}

def coletar_uf(uf, mapa, dbf_arquivo):
    """Coleta CAPS e SRT para uma UF via TabNet."""
    log(f"  {uf}: coletando TabNet...")
    ag = {}
    for tc, tn in TABNET_TIPOS.items():
        res = fetch_tipo(uf, tc, dbf_arquivo)
        if res["status"] != "OK":
            log(f"    {tn}: {res['status']}", "WARN"); time.sleep(2); continue
        log(f"    {tn}: {len(res['data'])} municipios")
        for it in res["data"]:
            i6 = it["ibge6"]; key = i6 if i6 else normalize(it["nome_tabnet"])
            if key not in ag:
                info = mapa.get(i6, {})
                ag[key] = {"uf":uf,"m":info.get("nome",it["nome_tabnet"]),
                    "ibge":info.get("ibge7",f"{i6}0" if i6 else ""),
                    "caps":0,"caps_tipo":[],"srt":0,"leitos_hg":0,"psiq_hg":0,"psiq_hg_sus":0,
                    "psiq_cad":0,"psiq_hab":0,"psiq_status":"","cobertura_raps":"NAO",
                    "alerta_fiscal":False,"nota_habilitacao":"","caps_nomes":"","fonte_sm":""}
            if tn == "SRT": ag[key]["srt"] += it["count"]
            else:
                ag[key]["caps"] += it["count"]
                if it["count"]>0 and tn not in ag[key]["caps_tipo"]: ag[key]["caps_tipo"].append(tn)
        time.sleep(1.5)
    muns = []
    for m in ag.values():
        m["caps_tipo"] = ", ".join(m["caps_tipo"])
        m["cobertura_raps"] = "SIM" if m["caps"]>0 else "NAO"
        muns.append(m)
    log(f"  {uf}: {len(muns)} municipios, {sum(m['caps'] for m in muns)} CAPS")
    return muns

def main():
    p = argparse.ArgumentParser(description="Coletor CNES mensal")
    p.add_argument("--competencia", help="MMAAAA (ex: 032026)")
    p.add_argument("--ufs", nargs="+", help="UFs especificas")
    p.add_argument("--municipios-json", help="Arquivo JSON com mapeamento IBGE")
    args = p.parse_args()

    if args.competencia:
        comp = args.competencia
    else:
        hoje = datetime.date.today()
        ma = hoje.replace(day=1) - datetime.timedelta(days=1)
        comp = ma.strftime("%m%Y")
    mes, ano, ref = int(comp[:2]), int(comp[2:]), f"{comp[:2]}/{comp[2:]}"
    ufs = args.ufs or UFS_ALL
    dbf = competencia_to_dbf(mes, ano)
    t0 = time.time()
    log(f"DMD Saude Brasil — Coletor CNES v5.0")
    log(f"Competencia: {ref} | DBF: {dbf} | UFs: {len(ufs)}")

    mapa = load_ibge_map(args.municipios_json)
    log(f"Mapa IBGE: {len(mapa)} municipios (0 = sem mapa, usa nomes TabNet)")

    todos, status = [], {}
    for uf in ufs:
        try:
            muns = coletar_uf(uf, mapa, dbf); todos.extend(muns); status[uf] = "OK"
        except Exception as e:
            log(f"  {uf}: ERRO — {e}", "ERROR"); status[uf] = f"ERRO"
        time.sleep(2)

    os.makedirs("cnes_data", exist_ok=True)
    pf = f"cnes_data/cnes_patch_{comp}.json"
    patch = {"competencia":ref,"gerado_em":datetime.datetime.now().isoformat(),
             "total_municipios":len(todos),"total_caps":sum(m["caps"] for m in todos),
             "total_srt":sum(m["srt"] for m in todos),"ufs_coletadas":len(ufs),
             "status_ufs":status,"fonte":f"CNES_TabNet_{comp}",
             "versao_coletor":"4.0","municipios":todos}
    with open(pf,"w",encoding="utf-8") as f: json.dump(patch,f,ensure_ascii=False,indent=2)

    af = f"cnes_data/cnes_auditoria_{comp}.csv"
    with open(af,"w",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uf","municipio","ibge","caps","srt","caps_tipo","cobertura_raps"])
        for m in todos:
            w.writerow([m["uf"],m["m"],m["ibge"],m["caps"],m["srt"],m["caps_tipo"],m["cobertura_raps"]])

    elapsed = time.time() - t0
    erros = {k:v for k,v in status.items() if v != "OK"}
    log(f"\n{'='*50}")
    log(f"  Competencia:    {ref}")
    log(f"  UFs OK:         {sum(1 for v in status.values() if v=='OK')}/{len(ufs)}")
    log(f"  Municipios:     {len(todos)}")
    log(f"  CAPS:           {patch['total_caps']}")
    log(f"  SRT:            {patch['total_srt']}")
    log(f"  Patch:          {pf}")
    log(f"  Tempo:          {elapsed:.0f}s")
    log(f"{'='*50}")
    if len(todos) == 0:
        log("ERRO FATAL: 0 municipios coletados — possivel mudanca no formato TabNet", "ERROR")
        sys.exit(2)
    sys.exit(0 if not erros else 1)

if __name__ == "__main__":
    main()
