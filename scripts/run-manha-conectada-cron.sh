#!/usr/bin/env bash
set -euo pipefail

REPO="/root/repositorio/d5n-videocast-source"
LOG_DIR="/root/.hermes/profiles/d5n/cron/output/manha-conectada"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(TZ=America/Sao_Paulo date '+%Y-%m-%d_%H-%M-%S').log"
TMP_RESULT=$(mktemp)
trap 'rm -f "$TMP_RESULT"' EXIT

if ! python3 "$REPO/scripts/manha_conectada_pipeline.py" >"$TMP_RESULT" 2>"$LOG_FILE"; then
  printf 'ERRO: MANHÃ CONECTADA não foi gerada. Consulte o log operacional.\n'
  exit 1
fi
cat "$TMP_RESULT" >>"$LOG_FILE"

STATUS=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status", "error"))' "$TMP_RESULT" 2>/dev/null || echo error)
if [ "$STATUS" = "skip" ]; then
  exit 0
fi
if [ "$STATUS" != "ok" ]; then
  printf 'ERRO: MANHÃ CONECTADA retornou resultado inválido.\n'
  exit 1
fi

FILE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["file"])' "$TMP_RESULT")
SOURCE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source"])' "$TMP_RESULT")
MANIFEST=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["manifest"])' "$TMP_RESULT")
DURATION=$(python3 -c 'import json,sys; print(round(json.load(open(sys.argv[1]))["audio"]["duration"]))' "$TMP_RESULT")

if ! bash "$REPO/scripts/publish-manha-conectada-site.sh" "$FILE" "$SOURCE" "$MANIFEST" >>"$LOG_FILE" 2>&1; then
  printf 'ERRO: MANHÃ CONECTADA foi gerada, mas a publicação do site falhou. Consulte o log operacional.\n'
  exit 1
fi

# O scheduler do host está uma hora atrás de Brasília. A produção começa antes,
# mas a saída só é liberada às 11:00 em America/Sao_Paulo.
python3 - <<'PY'
from datetime import datetime, timedelta
from time import sleep
from zoneinfo import ZoneInfo
now = datetime.now(ZoneInfo("America/Sao_Paulo"))
target = now.replace(hour=11, minute=0, second=0, microsecond=0)
if target < now - timedelta(minutes=10):
    target = now
wait = (target - now).total_seconds()
if 0 < wait <= 1800:
    sleep(wait)
PY

DATE_BR=$(TZ=America/Sao_Paulo date '+%d/%m/%Y')
printf '🎙️ **MANHÃ CONECTADA — %s**\nBriefing do dia em %ss, com apresentação de Antonio.\nMEDIA:%s\n' "$DATE_BR" "$DURATION" "$FILE"
