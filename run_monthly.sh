#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# DMD Saude Brasil — Pipeline mensal CNES (rodar no computador local)
#
# O TabNet DATASUS bloqueia IPs de datacenter, entao o scraper
# precisa rodar localmente. Ao fazer push do patch, o GitHub
# Actions carrega automaticamente no Supabase.
#
# Uso:
#   ./run_monthly.sh           # usa mes anterior
#   ./run_monthly.sh 032026    # competencia especifica
#
# Requisitos:
#   pip install requests
# ═══════════════════════════════════════════════════════════════

set -e

# Competencia: argumento ou mes anterior
if [ -n "$1" ]; then
    COMP="$1"
else
    # macOS e Linux compativel
    COMP=$(date -v-1m +%m%Y 2>/dev/null || date -d "last month" +%m%Y 2>/dev/null)
fi

REF="${COMP:0:2}/${COMP:2:4}"
echo "══════════════════════════════════════════════"
echo "  DMD Saude Brasil — Pipeline Mensal CNES"
echo "  Competencia: $REF"
echo "══════════════════════════════════════════════"
echo ""

# Verificar que estamos no diretorio do repositorio
if [ ! -f "cnes_scraper.py" ]; then
    echo "ERRO: Execute este script na raiz do repositorio dmd-saude-brasil"
    exit 1
fi

# Verificar Python e requests
python3 -c "import requests" 2>/dev/null || {
    echo "ERRO: 'requests' nao instalado. Rode: pip install requests"
    exit 1
}

# Passo 1: Coletar dados do TabNet
echo "[1/3] Coletando dados CNES do TabNet..."
echo ""
python3 cnes_scraper.py --competencia "$COMP"

PATCH="cnes_data/cnes_patch_${COMP}.json"
AUDIT="cnes_data/cnes_auditoria_${COMP}.csv"

if [ ! -f "$PATCH" ]; then
    echo ""
    echo "ERRO: Patch nao foi gerado: $PATCH"
    exit 1
fi

echo ""
echo "[2/3] Enviando patch para o repositorio..."
git add "$PATCH"
[ -f "$AUDIT" ] && git add "$AUDIT"
git commit -m "data: CNES patch $REF"
git push origin main

echo ""
echo "[3/3] GitHub Actions vai carregar no Supabase automaticamente"
echo ""
echo "  Acompanhe em:"
echo "  https://github.com/kbarrosfinal-netizen/dmd-saude-brasil/actions"
echo ""
echo "══════════════════════════════════════════════"
echo "  Concluido!"
echo "══════════════════════════════════════════════"
