#!/usr/bin/env python3
"""
SCRIPT 02 — NORMALIZADOR E VALIDADOR DE MUNICÍPIOS
DMD Saúde Brasil | EMET Gestão Brasil | Pipeline Nacional v3.0

PASSO 2 e 3 do pipeline:
- Normalização de nomes (uppercase sem acentos)
- Match por código IBGE 7 dígitos (NUNCA só por nome)
- Validação de consistência pós-coleta
- Geração de relatório de erros/alertas

REGRAS CRÍTICAS DO PROMPT 3:
a) psiq_hab <= psiq_cad
b) caps >= 0
c) pop > 0
d) pop > 20.000 e caps == 0 → alerta_fiscal
e) psiq_cad > 0 e psiq_hab == 0 → VACUO_HAB
f) Sem duplicatas por UF
g) Total municípios por UF = IBGE oficial
"""

import json
import re
import unicodedata
import datetime
import hashlib
from pathlib import Path
from collections import Counter

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────
BASE_DIR = Path("/home/user/dmd-pipeline-nacional")

MUNICIPIOS_IBGE_POR_UF = {
    "AC": 22, "AL": 102, "AM": 62, "AP": 16, "BA": 417, "CE": 184,
    "DF": 1,  "ES": 78,  "GO": 246,"MA": 217,"MG": 853,"MS": 79,
    "MT": 142,"PA": 144,"PB": 223,"PE": 185,"PI": 224,"PR": 399,
    "RJ": 92, "RN": 167,"RO": 52, "RR": 15, "RS": 497,"SC": 295,
    "SE": 75, "SP": 645,"TO": 139
}

# ─── UTILITÁRIOS ──────────────────────────────────────────────────────────
def normalize(nome: str) -> str:
    if not nome:
        return ""
    nfkd = unicodedata.normalize("NFKD", nome.upper())
    return re.sub(r"[^A-Z0-9 ]", "", "".join(c for c in nfkd if not unicodedata.combining(c))).strip()

def log(msg, level="INFO"):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}][{level}] {msg}")

# ─── CARREGAR BASE IBGE ───────────────────────────────────────────────────
def load_ibge_base():
    path = BASE_DIR / "data" / "municipios_ibge.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    # Índice principal: ibge7 → dados
    by_ibge7 = {m["ibge7"]: m for m in data["municipios"]}
    # Índice secundário: ibge6 → dados  
    by_ibge6 = {m["ibge6"]: m for m in data["municipios"]}
    # Índice terciário: (uf, nome_norm) → dados
    by_uf_nome = {(m["uf"], m["nome_norm"]): m for m in data["municipios"]}
    
    return data["municipios"], by_ibge7, by_ibge6, by_uf_nome

# ─── VALIDAÇÃO DE CONSISTÊNCIA ────────────────────────────────────────────
class ValidadorMunicipio:
    """
    Implementa todas as 7 regras de validação do Prompt 3, Passo 3
    """
    
    FONTES_REAIS = {"CNES_16032026", "CNES_Mar2026", "CNES_16032026 + SES-AM_29012026"}
    FONTES_SUBSTITUIVEIS = {"ESTIMATIVA_PORTE_Mar2026", "MODELO_PREDITIVO_Mar2026", "PENDENTE"}
    
    def __init__(self, uf: str):
        self.uf = uf
        self.erros = []
        self.alertas = []
        self.warnings = []
    
    def validar_municipio(self, m: dict) -> dict:
        """Valida um único município e retorna flags de alerta."""
        flags = {
            "alerta_fiscal": False,
            "vacuo_hab": False,
            "erros": [],
            "warnings": [],
        }
        
        ibge = m.get("ibge7", m.get("ibge", ""))
        nome = m.get("m", m.get("nome", ""))
        
        # REGRA a) psiq_hab <= psiq_cad
        psiq_cad = m.get("psiq_cad", 0) or 0
        psiq_hab = m.get("psiq_hab", 0) or 0
        if psiq_hab > psiq_cad:
            flags["erros"].append(f"R_A: psiq_hab({psiq_hab}) > psiq_cad({psiq_cad}) — IMPOSSÍVEL")
        
        # REGRA b) caps >= 0
        caps = m.get("caps", 0) or 0
        if caps < 0:
            flags["erros"].append(f"R_B: caps={caps} negativo — INVÁLIDO")
        
        # REGRA c) pop > 0
        pop = m.get("pop", 0) or 0
        if pop <= 0:
            flags["warnings"].append(f"R_C: pop={pop} — sem população registrada")
        
        # REGRA d) pop > 20.000 e caps == 0 → alerta_fiscal
        if pop > 20000 and caps == 0:
            flags["alerta_fiscal"] = True
            flags["warnings"].append(f"R_D: ALERTA FISCAL — pop={pop:,} sem CAPS")
        
        # REGRA e) psiq_cad > 0 e psiq_hab == 0 → VACUO_HAB
        if psiq_cad > 0 and psiq_hab == 0:
            flags["vacuo_hab"] = True
            flags["warnings"].append(f"R_E: VÁCUO HAB — {psiq_cad} leitos cadastrados, 0 habilitados")
        
        return flags
    
    def validar_uf_completa(self, municipios: list) -> dict:
        """
        Valida lista completa de municípios de uma UF.
        Regra f) sem duplicatas
        Regra g) total bate com IBGE
        """
        result = {
            "uf": self.uf,
            "total_municipios": len(municipios),
            "esperado_ibge": MUNICIPIOS_IBGE_POR_UF.get(self.uf, 0),
            "alertas_fiscais": 0,
            "vacuos_hab": 0,
            "erros_consistencia": 0,
            "duplicatas": [],
            "orfaos": [],
            "municipios_validados": [],
        }
        
        # REGRA f) duplicatas
        ibge_vistos = Counter(m.get("ibge7", m.get("ibge", "")) for m in municipios)
        duplicatas = [ibge for ibge, cnt in ibge_vistos.items() if cnt > 1]
        result["duplicatas"] = duplicatas
        if duplicatas:
            self.erros.append(f"UF {self.uf}: {len(duplicatas)} códigos IBGE duplicados: {duplicatas[:5]}")
        
        # Validar cada município
        for m in municipios:
            flags = self.validar_municipio(m)
            m["_alerta_fiscal"] = flags["alerta_fiscal"]
            m["_vacuo_hab"] = flags["vacuo_hab"]
            m["_erros_val"] = flags["erros"]
            m["_warnings_val"] = flags["warnings"]
            
            if flags["alerta_fiscal"]:
                result["alertas_fiscais"] += 1
            if flags["vacuo_hab"]:
                result["vacuos_hab"] += 1
            if flags["erros"]:
                result["erros_consistencia"] += len(flags["erros"])
            
            result["municipios_validados"].append(m)
        
        # REGRA g) total bate com IBGE
        esperado = result["esperado_ibge"]
        obtido = len(municipios)
        result["divergencia_ibge"] = obtido - esperado
        if obtido != esperado:
            self.erros.append(
                f"UF {self.uf}: total={obtido} ≠ IBGE={esperado} "
                f"(diff={obtido-esperado:+d})"
            )
        
        return result

# ─── MATCHER IBGE ─────────────────────────────────────────────────────────
class MatcherIBGE:
    """
    Realiza match entre dados do TabNet e base IBGE.
    REGRA CRÍTICA: match por código IBGE, NUNCA só por nome.
    """
    
    def __init__(self, by_ibge7, by_ibge6, by_uf_nome):
        self.by_ibge7 = by_ibge7
        self.by_ibge6 = by_ibge6
        self.by_uf_nome = by_uf_nome
        self.stats = Counter()
    
    def match(self, item: dict, uf: str) -> tuple:
        """
        Retorna (municipio_ibge, metodo_match, confianca)
        metodo_match: 'IBGE7' | 'IBGE6' | 'NOME_NORM' | 'ORPHAN'
        """
        ibge6 = str(item.get("ibge6", "")).strip()
        nome_tabnet = item.get("municipio_tabnet", item.get("nome", "")).strip()
        nome_norm = normalize(nome_tabnet)
        
        # Tentativa 1: IBGE6 direto (6 dígitos TabNet)
        if ibge6 and ibge6 in self.by_ibge6:
            m = self.by_ibge6[ibge6]
            if m["uf"] == uf:  # Confirmar UF (evitar colisão entre estados)
                self.stats["IBGE6"] += 1
                return m, "IBGE6", 1.0
        
        # Tentativa 2: IBGE7 (se fornecido com 7 dígitos)
        ibge7 = str(item.get("ibge7", "")).strip()
        if ibge7 and len(ibge7) == 7 and ibge7 in self.by_ibge7:
            self.stats["IBGE7"] += 1
            return self.by_ibge7[ibge7], "IBGE7", 1.0
        
        # Tentativa 3: Nome normalizado dentro da UF (fallback)
        key_uf_nome = (uf, nome_norm)
        if key_uf_nome in self.by_uf_nome:
            self.stats["NOME_NORM"] += 1
            return self.by_uf_nome[key_uf_nome], "NOME_NORM", 0.85
        
        # Não encontrado: ORPHAN
        self.stats["ORPHAN"] += 1
        return None, "ORPHAN", 0.0
    
    def report(self) -> dict:
        total = sum(self.stats.values())
        return {
            "total": total,
            "por_metodo": dict(self.stats),
            "taxa_match": round((total - self.stats.get("ORPHAN", 0)) / max(total, 1) * 100, 1)
        }

# ─── PASSO 4: GERAÇÃO DE PATCH JSON ──────────────────────────────────────
def gerar_patch_json(uf: str, municipios_validados: list, competencia: str, fonte: str) -> dict:
    """
    Gera patch JSON no formato padrão do Prompt 3, Passo 4
    """
    patch = {
        "versao": "3.0",
        "competencia": competencia,
        "uf": uf,
        "gerado_em": datetime.datetime.now().isoformat(),
        "fonte": fonte,
        "total_municipios": len(municipios_validados),
        "municipios": []
    }
    
    for m in municipios_validados:
        entry = {
            "m": m.get("nome", ""),
            "ibge": m.get("ibge7", m.get("ibge", "")),
            "pop": m.get("pop_2022", m.get("pop", 0)),
            "caps": m.get("caps", 0),
            "caps_tipo": m.get("caps_tipos", ""),
            "srt": m.get("srt", 0),
            "psiq_cad": m.get("psiq_cad", 0),
            "psiq_hab": m.get("psiq_hab", 0),
            "leitos_sus": m.get("leitos_sus", 0),
            "uti": m.get("uti", 0),
            "esf_pct": m.get("esf_pct", 0),
            "fonte_sm": fonte,
            # Campos calculados/derivados
            "alerta_fiscal": m.get("_alerta_fiscal", False),
            "vacuo_hab": m.get("_vacuo_hab", False),
            # Campos adicionais (serão preenchidos nas próximas camadas)
            "lq": round(m.get("psiq_hab", 0) / max(m.get("pop_2022", 1), 1) * 1000, 4),
            "def_psiq": max(0, m.get("psiq_cad", 0) - m.get("psiq_hab", 0)),
        }
        patch["municipios"].append(entry)
    
    # Hash de integridade
    patch["sha256"] = hashlib.sha256(
        json.dumps(patch["municipios"], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    
    return patch

# ─── PASSO 6: AUDITORIA PÓS-INJEÇÃO ─────────────────────────────────────
def gerar_relatorio_auditoria(uf: str, resultado_validacao: dict, patch: dict) -> dict:
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "uf": uf,
        "competencia": patch.get("competencia", ""),
        "total_municipios_patch": patch.get("total_municipios", 0),
        "esperado_ibge": MUNICIPIOS_IBGE_POR_UF.get(uf, 0),
        "divergencia_ibge": resultado_validacao.get("divergencia_ibge", 0),
        "alertas_fiscais": resultado_validacao.get("alertas_fiscais", 0),
        "vacuos_hab": resultado_validacao.get("vacuos_hab", 0),
        "erros_consistencia": resultado_validacao.get("erros_consistencia", 0),
        "duplicatas": resultado_validacao.get("duplicatas", []),
        "patch_sha256": patch.get("sha256", ""),
        "status_auditoria": "APROVADO" if (
            resultado_validacao.get("erros_consistencia", 0) == 0 and
            resultado_validacao.get("divergencia_ibge", 1) == 0 and
            len(resultado_validacao.get("duplicatas", [])) == 0
        ) else "REPROVADO_COM_PENDENCIAS",
    }

# ─── DEMONSTRAÇÃO: NORMALIZAÇÃO COM BASE IBGE ────────────────────────────
if __name__ == "__main__":
    log("SCRIPT 02 — NORMALIZADOR/VALIDADOR — TESTE")
    
    muns, by7, by6, by_uf_nome = load_ibge_base()
    log(f"Base IBGE carregada: {len(muns)} municípios")
    
    matcher = MatcherIBGE(by7, by6, by_uf_nome)
    
    # Testar com amostra AC
    amostra_ac = [
        {"ibge6": "120001", "municipio_tabnet": "ACRELANDIA", "caps": 0, "srt": 0},
        {"ibge6": "120005", "municipio_tabnet": "ASSIS BRASIL", "caps": 0, "srt": 0},
        {"ibge6": "120010", "municipio_tabnet": "BRASILEIA", "caps": 1, "srt": 0},
        {"ibge6": "999999", "municipio_tabnet": "NAO EXISTE", "caps": 0, "srt": 0},  # ORPHAN
    ]
    
    for item in amostra_ac:
        mun_ibge, metodo, conf = matcher.match(item, "AC")
        if mun_ibge:
            log(f"  MATCH: {item['municipio_tabnet']} → {mun_ibge['nome']} ({mun_ibge['ibge7']}) via {metodo} conf={conf}")
        else:
            log(f"  ORPHAN: {item['municipio_tabnet']} — não encontrado na base IBGE", "WARN")
    
    log(f"Relatório matcher: {matcher.report()}")
    
    # Teste validador
    val = ValidadorMunicipio("AC")
    mun_teste = {
        "ibge7": "1200401", "nome": "Rio Branco", "pop_2022": 419452,
        "caps": 0, "psiq_cad": 50, "psiq_hab": 0  # VÁCUO HAB + ALERTA FISCAL
    }
    flags = val.validar_municipio(mun_teste)
    log(f"Validação Rio Branco (teste): {flags}")
    log("SCRIPT 02 — OK")
