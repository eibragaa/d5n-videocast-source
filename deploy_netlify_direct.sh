#!/usr/bin/env bash
# deploy_netlify_direct.sh — PLAN B Deploy Netlify sem GitHub
# Le token de /root/.netlify-token (1 linha, sem espacos)
# Uso: NETLIFY_SITE_ID=d5n-daily ./deploy_netlify_direct.sh

set -euo pipefail
DATE=$(date +%Y-%m-%d)
REPO="/root/repositorio/d5n-videocast-source"
LOG="/tmp/deploy-netlify-direct-${DATE}.log"
SITE_ID="${1:-${NETLIFY_SITE_ID:-d5n-daily}}"

echo "[$(date '+%H:%M:%S')] Deploy DIRETO Netlify - ${DATE} (Plan B)" | tee "$LOG"

TF=/root/.netlify-token
if [ ! -f "$TF" ]; then
  echo "Token nao encontrado: ${TF}" | tee -a "$LOG"
  echo "Crie em https://app.netlify.com/user/applications"
  exit 1
fi
NKEY=$(cat "$TF" | tr -d '\n\r')
[ -z "$NKEY" ] && { echo "Token vazio"; exit 1; }
AH="Authorization: Bearer ${NKEY}"

cd "$REPO"
[ ! -f index.html ] && { echo "index.html nao encontrado"; exit 1; }

NC=$(grep -oP '<strong>\K\d+(?=</strong><span>notícias)' index.html || echo 0)
[ "$NC" -eq 0 ] && { echo "0 noticias - abortando"; exit 1; }
echo "OK: ${NC} noticias" | tee -a "$LOG"

echo "Criando deploy no Netlify (site: ${SITE_ID})..." | tee -a "$LOG"
DR=$(curl -sf -X POST \
  -H "${AH}" \
  -H "Content-Type: application/json" \
  "https://api.netlify.com/api/v1/sites/${SITE_ID}/deploys" \
  -d "{\"title\":\"D5N - ${DATE} (direct)\"}" 2>&1) || {
  echo "Falha ao criar deploy"; exit 1
}

DID=$(echo "$DR" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('id','ERROR'))")
echo "Deploy ID: ${DID}" | tee -a "$LOG"

echo "Enviando arquivos..." | tee -a "$LOG"
find . -type f \( -name '*.html' -o -name '*.json' -o -name '*.xml' -name '*.css' -name '*.js' \) -print0 | \
  while IFS= read -r -d '' f; do
    rp="${f#./}"
    curl -sf -X PUT \
      -H "${AH}" \
      -H "Content-Type: application/octet-stream" \
      --data-binary @"${f}" \
      "https://api.netlify.com/api/v1/deploys/${DID}/files/${rp}" > /dev/null 2>&1
    echo "  + ${rp}"
  done

find audio -name '*.mp3' -print0 | \
  while IFS= read -r -d '' f; do
    rp="${f#./}"
    curl -sf -X PUT \
      -H "${AH}" \
      -H "Content-Type: audio/mpeg" \
      --data-binary @"${f}" \
      "https://api.netlify.com/api/v1/deploys/${DID}/files/${rp}" > /dev/null 2>&1
    echo "  + ${rp}"
  done

sleep 3

echo "Verificando..." | tee -a "$LOG"
curl -sf -H "${AH}" \
  "https://api.netlify.com/api/v1/deploys/${DID}" | \
  python3 -c "
import sys,json
d=json.load(sys.stdin)
print('Estado:', d.get('state','?'))
print('URL:', d.get('ssl_url',d.get('url','?')))
"

rm -f /tmp/.deploy-d5n-failed
echo "Feito!" | tee -a "$LOG"
echo "https://d5n-daily.netlify.app/" | tee -a "$LOG"
