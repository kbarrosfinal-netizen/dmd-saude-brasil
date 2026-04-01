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

TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe"
CAPS_TIPOS = {"70":"CAPS I","71":"CAPS II","72":"CAPS III",
              "73":"CAPSi","74":"CAPSad","75":"CAPSad III","76":"CAPSad IV","67":"SRT"}
UF_COD = {"AC":"12","AL":"27","AM":"13","AP":"16","BA":"29","CE":"23","DF":"53",
          "ES":"32","GO":"52","MA":"21","MG":"31","MS":"50","MT":"51","PA":"15",
          "PB":"25","PE":"26","PI":"22","PR":"41","RJ":"33","RN":"24","RO":"11",
          "RR":"14","RS":"43","SC":"42","SE":"28","SP":"35","TO":"17"}
UFS_ALL = sorted(UF_COD.keys())

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

def build_payload(uf_cod, tipo_cod):
    base = {k:"TODAS_AS_CATEGORIAS__" for k in [
        "SMunic","SMunicgestor","SCapital","SRegsaud","SMacsaud","SMicr","SRmetrop",
        "STerCidadania","SMesorregPNDR","SAmazLegal","SSemiarido","SFaixFront","SZonFront",
        "SMunExtrPobr","SEnsPesq","SNatJur","SEsfJur","SEsfAdm","SNatureza","STipoGestao"]}
    base.update({"Linha":"Município","Coluna":"--Nenhuma--","Incremento":"Estabelecimentos",
                 "Arquivos":"estabbr.def","pesqmes1":"Digite o texto e clique na lupa",
                 "STipoUnid":tipo_cod,"SUF":uf_cod,"zeran":"1","formato":"table","mostre":"Mostra"})
    return base

def parse_tabnet(html, uf, tipo):
    res = []
    for i6, nome, cnt in re.findall(r'<td[^>]*>(\d{6})\s+([^<]+)</td>\s*<td[^>]*>(\d+)</td>', html, re.I):
        res.append({"ibge6":i6.strip(),"nome_tabnet":nome.strip(),"count":int(cnt),"tipo":tipo,"uf":uf})
    if not res:
        for nome, cnt in re.findall(r'<td[^>]*class="[^"]*linha[^"]*"[^>]*>([^<]{3,50})</td>\s*<td[^>]*>(\d+)</td>', html, re.I):
            res.append({"ibge6":"","nome_tabnet":nome.strip(),"count":int(cnt),"tipo":tipo,"uf":uf})
    return res

def fetch_tipo(uf, tipo_cod):
    tipo_nome = CAPS_TIPOS[tipo_cod]
    try:
        r = requests.post(f"{TABNET_URL}?cnes/cnv/estabbr.def",
            data=build_payload(UF_COD[uf], tipo_cod),
            headers={"User-Agent":"Mozilla/5.0 (DMD-Pipeline/4.0; EMET)",
                     "Referer":"http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/estabbr.def",
                     "Content-Type":"application/x-www-form-urlencoded"}, timeout=30)
        if r.status_code != 200: return {"status":"HTTP_ERROR","data":[]}
        return {"status":"OK","data":parse_tabnet(r.text, uf, tipo_nome)}
    except requests.Timeout: return {"status":"TIMEOUT","data":[]}
    except Exception as e: return {"status":"ERROR","data":[]}

def coletar_uf(uf, mapa):
    log(f"  {uf}: coletando TabNet...")
    ag = {}
    for tc in CAPS_TIPOS:
        res = fetch_tipo(uf, tc)
        tn = CAPS_TIPOS[tc]
        if res["status"] != "OK":
            log(f"    {tn}: {res['status']}", "WARN"); time.sleep(2); continue
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
    t0 = time.time()
    log(f"DMD Saude Brasil — Coletor CNES v4.0")
    log(f"Competencia: {ref} | UFs: {len(ufs)}")

    mapa = load_ibge_map(args.municipios_json)
    log(f"Mapa IBGE: {len(mapa)} municipios")

    todos, status = [], {}
    for uf in ufs:
        try:
            muns = coletar_uf(uf, mapa); todos.extend(muns); status[uf] = "OK"
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
    sys.exit(0 if not erros else 1)

if __name__ == "__main__":
    main()
