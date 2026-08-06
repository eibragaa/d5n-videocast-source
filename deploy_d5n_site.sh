#!/usr/bin/env bash
# Publicação diária D5N — fail-closed, idempotente e segura para retries.
# Todos os dias, inclusive domingo. Só cria recibo depois de push bem-sucedido.

set -euo pipefail

DATE="${D5N_DATE:-$(TZ=America/Sao_Paulo date +%Y-%m-%d)}"
REPO="${D5N_REPO:-/root/repositorio/d5n-videocast-source}"
STATE_DIR="${D5N_STATE_DIR:-/root/.hermes/logs/d5n-deploy}"
CRON_AUDIO="${D5N_CRON_AUDIO:-/root/.hermes/cron/output}"
CRON_AUDIO_D5N="${D5N_CRON_AUDIO_D5N:-/root/.hermes/profiles/d5n/cron/output}"
TRENDS_FILE="${D5N_TRENDS_FILE:-/root/.hermes/cron/output/drop5news-trends-${DATE}.txt}"
LOG="${STATE_DIR}/deploy-${DATE}.log"
FAILED_MARKER="${STATE_DIR}/failed"
LAST_GOOD_FILE="${STATE_DIR}/last-good"
RECEIPT="${STATE_DIR}/published-${DATE}.json"
STATUS_SCRIPT="${REPO}/scripts/d5n_release_status.py"
COUNTER_FILE="episode-counter.json"
VALIDATOR="${REPO}/scripts/validate_mp3.py"
CHAPTER_MANIFEST="/tmp/d5n_audio/manifest.json"
CHAPTER_DEST="chapters/${DATE}.json"

mkdir -p "$STATE_DIR"
cd "$REPO"
: > "$LOG"

log() {
    printf '[%s] %s\n' "$(TZ=America/Sao_Paulo date '+%H:%M:%S')" "$*" | tee -a "$LOG"
}

block() {
    local reason="$1"
    log "❌ BLOQUEADO: ${reason}"
    {
        printf '%s\n' "$DATE"
        printf 'Motivo: %s\n' "$reason"
        printf 'Log: %s\n' "$LOG"
    } > "$FAILED_MARKER"
    log "❌ DEPLOY BLOQUEADO — nenhuma publicação foi confirmada"
    exit 1
}

log "🚀 Release diária Drop Five News — ${DATE}"

# Retry idempotente: um recibo válido prova que áudio, contador e push já fecharam.
if python3 "$STATUS_SCRIPT" --repo "$REPO" --state-dir "$STATE_DIR" --date "$DATE" >> "$LOG" 2>&1; then
    log "✅ D5N_ALREADY_PUBLISHED — recibo íntegro; nenhuma mutação necessária"
    exit 0
fi

LAST_GOOD=$(git rev-parse HEAD) || block "repositório Git indisponível"
printf '%s\n' "$LAST_GOOD" > "$LAST_GOOD_FILE"
log "✅ Último commit local salvo: ${LAST_GOOD:0:8}"

# A fonte da data é obrigatória. Nunca usar source.md ou dados antigos como fallback.
[ -s "$TRENDS_FILE" ] || block "trends do dia ausentes ou vazios: $TRENDS_FILE"
TRENDS_BYTES=$(wc -c < "$TRENDS_FILE")
[ "$TRENDS_BYTES" -ge 200 ] || block "trends do dia insuficientes (${TRENDS_BYTES} bytes)"
for pillar in GLOBAL BRASIL TECH ECONOMIA; do
    grep -qi "$pillar" "$TRENDS_FILE" || block "trends sem pilar obrigatório: $pillar"
done
log "✅ Trends atuais: ${TRENDS_BYTES} bytes, quatro pilares presentes"

mkdir -p audio "$CRON_AUDIO" "$CRON_AUDIO_D5N"

# Somente áudio explicitamente datado de hoje pode entrar na release.
LATEST_MP3=$(ls -t \
    "$CRON_AUDIO"/d5n-ep*-${DATE}.mp3 \
    "$CRON_AUDIO_D5N"/d5n-ep*-${DATE}.mp3 \
    "$CRON_AUDIO"/d5n-podcast-${DATE}.mp3 \
    "$CRON_AUDIO_D5N"/d5n-podcast-${DATE}.mp3 2>/dev/null | head -1) || true
[ -n "$LATEST_MP3" ] || block "Nenhum MP3 válido para hoje (${DATE})"

MP3_MTIME=$(stat -c %Y "$LATEST_MP3" 2>/dev/null || printf '0')
TODAY_START=$(TZ=America/Sao_Paulo date -d "$DATE 00:00:00" +%s)
[ "$MP3_MTIME" -ge "$TODAY_START" ] || block "MP3 de hoje tem mtime anterior à data editorial"

if ! python3 "$VALIDATOR" "$LATEST_MP3" >> "$LOG" 2>&1; then
    block "validador básico rejeitou o MP3: $LATEST_MP3"
fi
log "✅ MP3 básico aprovado: $LATEST_MP3"

# Gates obrigatórios antes de cp, contador, página, commit ou push.
if ! python3 "$REPO/scripts/d5n-podcast-quality-gate.py" >> "$LOG" 2>&1; then
    block "gate técnico reprovou o episódio"
fi
if ! python3 "$REPO/scripts/d5n_daily_release_gate.py" \
    --date "$DATE" \
    --audio "$LATEST_MP3" \
    --audio-dir /tmp/d5n_audio \
    --history-dir "$REPO/podcast-scripts" \
    --write-snapshot >> "$LOG" 2>&1; then
    block "gate editorial diário reprovou o episódio"
fi
log "✅ Gates técnico e editorial aprovados"

# Retenção diária do manifesto e do roteiro (permite recovery retroativo).
# /tmp/d5n_audio/ é sobrescrito a cada dia; sem retenção o manifesto/roteiro de
# ontem se perde. Cópia idempotente e não bloqueante (nunca aborta o deploy).
RETENTION_DIR="manifests/d5n/${DATE}"
mkdir -p "$RETENTION_DIR"
if [ -f "$CHAPTER_MANIFEST" ]; then
    cp "$CHAPTER_MANIFEST" "$RETENTION_DIR/manifest.json" 2>/dev/null || true
fi
for _t in /tmp/d5n_audio/*.txt; do
    [ -e "$_t" ] && cp "$_t" "$RETENTION_DIR/" 2>/dev/null || true
done
log "✅ Retenção diária: $RETENTION_DIR"

# Reutiliza o número da mesma data em retries; nunca incrementa duas vezes.
TODAY_EP=$(python3 -c "import json; d=json.load(open('$COUNTER_FILE')); print(next((e['num'] for e in d.get('history', []) if e.get('date') == '$DATE'), ''))")
if [ -n "$TODAY_EP" ]; then
    EP_NUM="$TODAY_EP"
    log "♻️ Episódio #${EP_NUM} reutilizado para retry da mesma data"
else
    LAST_NUM=$(python3 -c "import json; d=json.load(open('$COUNTER_FILE')); print(d.get('last_episode', 0))")
    NEXT_NUM=$((10#$LAST_NUM + 1))
    EP_NUM=$(printf '%03d' "$NEXT_NUM")
fi

DEST="audio/d5n-ep${EP_NUM}-${DATE}.mp3"
cp "$LATEST_MP3" "$DEST"
if [ "$LATEST_MP3" != "$CRON_AUDIO/d5n-podcast-${DATE}.mp3" ]; then
    cp "$LATEST_MP3" "$CRON_AUDIO/d5n-podcast-${DATE}.mp3"
fi
if ! python3 "$REPO/scripts/d5n_chapter_manifest.py" \
    --manifest "$CHAPTER_MANIFEST" \
    --date "$DATE" \
    --audio "$DEST" \
    --output "$CHAPTER_DEST" >> "$LOG" 2>&1; then
    block "manifesto obrigatório de capítulos ausente ou inválido"
fi
log "✅ Nove capítulos reais validados e preparados"

python3 -c "
import json
from pathlib import Path
p=Path('$COUNTER_FILE')
d=json.loads(p.read_text())
d.setdefault('history', [])
entry={'num':'$EP_NUM','date':'$DATE','file':'d5n-ep$EP_NUM-$DATE.mp3','exists':True}
idx=next((i for i,e in enumerate(d['history']) if e.get('date')=='$DATE'), None)
if idx is None:
    d['history'].append(entry)
else:
    d['history'][idx]=entry
d['last_episode']=max(int(d.get('last_episode', 0)), int('$EP_NUM'))
d['updated']='$DATE'
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
"
log "✅ Áudio e contador preparados: episódio #${EP_NUM}"

if ! python3 gerar_pagina_d5n.py >> "$LOG" 2>&1; then
    block "gerar_pagina_d5n.py falhou"
fi
NEWS_COUNT=$(grep -oP '<strong>\K\d+(?=</strong><span>notícias)' index.html || printf '0')
[ "${NEWS_COUNT:-0}" -gt 0 ] || block "index.html gerado sem notícias"
[ -s source.md ] && [ "$(wc -c < source.md)" -gt 100 ] || block "source.md ausente ou vazio após geração"
# O áudio existir no site não informa os agregadores. A release só pode seguir
# quando o feed de podcast também anuncia exatamente este episódio.
[ -s podcast.xml ] || block "podcast.xml ausente ou vazio após geração"
PODCAST_GUID="d5n-${DATE}-ep${EP_NUM}"
grep -Fq "<guid isPermaLink=\"false\">${PODCAST_GUID}</guid>" podcast.xml \
    || block "podcast.xml não contém o episódio #${EP_NUM} de ${DATE}"
log "✅ Site gerado: ${NEWS_COUNT} notícias"

# Staging/commit seletivo: jamais absorver arquivos de outros pipelines.
git add -- "$DEST"
git add -- "$CHAPTER_DEST"
git add -- episode-counter.json index.html source.md podcast.xml scripts/d5n_chapter_manifest.py
RELEASE_PATHS=("$DEST" "$CHAPTER_DEST" episode-counter.json index.html source.md podcast.xml scripts/d5n_chapter_manifest.py)
for optional in feed.json d5n-feed.xml; do
    if [ -e "$optional" ]; then
        git add -- "$optional"
        RELEASE_PATHS+=("$optional")
    fi
done

if ! git diff --cached --quiet -- "${RELEASE_PATHS[@]}"; then
    if ! git commit --only -m "📰 D5N - ${DATE}" -- "${RELEASE_PATHS[@]}" >> "$LOG" 2>&1; then
        block "commit seletivo da release falhou"
    fi
else
    log "ℹ️ Release já estava commitada; confirmando push"
fi

COMMIT=$(git rev-parse HEAD)
if ! git push origin HEAD:master >> "$LOG" 2>&1; then
    block "push para origin/master falhou; remoto não confirmado"
fi
log "✅ Push confirmado: ${COMMIT:0:8}"

AUDIO_SHA=$(sha256sum "$DEST" | cut -d' ' -f1)
python3 -c "
import json
from pathlib import Path
receipt={
  'editorial_date':'$DATE',
  'episode':'$EP_NUM',
  'audio':'$DEST',
  'sha256':'$AUDIO_SHA',
  'commit':'$COMMIT'
}
Path('$RECEIPT').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\\n')
"

if ! python3 "$STATUS_SCRIPT" --repo "$REPO" --state-dir "$STATE_DIR" --date "$DATE" >> "$LOG" 2>&1; then
    rm -f "$RECEIPT"
    block "recibo pós-push não passou na verificação de integridade"
fi

rm -f "$FAILED_MARKER"
log "✅ D5N_RELEASED — episódio #${EP_NUM} publicado"
log "🌐 https://d5n-daily.netlify.app/"
exit 0
