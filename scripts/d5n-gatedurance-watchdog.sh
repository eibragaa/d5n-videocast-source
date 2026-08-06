#!/usr/bin/env bash
# GateDurance Watchdog — observador contínuo do episódio diário do Drop Five News.
#
# Papel: garantir que "o podcast sempre vai ao ar" pegando SEMPRE o texto aprovado.
# Roda a cada intervalo (via cron) e decide, para o dia corrente:
#   A. Já publicado?  → silêncio (exit 0, sem output) — nada a fazer.
#   B. Não publicado, roteiro GateDurance verde → informa "pronto para TTS/mix/deploy".
#   C. Não publicado, roteiro com erros mecânicos → aplica autocorrect e re-valida.
#   D. Não publicado, restam erros que exigem LLM → alerta (o job de recuperação
#      regenera e re-tenta; o watchdog apenas sinaliza, nunca contorna gates).
#
# Regra de ouro: NUNCA contorna, desativa ou burla um gate para forçar publicação.
# O watchdog só avança o que está genuinamente aprovado.
#
# Uso: bash d5n-gatedurance-watchdog.sh [--date YYYY-MM-DD] [--audio-dir /tmp/d5n_audio]
# Exit: 0 = ok/silencioso; 1 = alerta (algo precisa atenção); 2 = exaustão.
set -uo pipefail

DATE="$(TZ=America/Sao_Paulo date +%Y-%m-%d)"
AUDIO_DIR="/tmp/d5n_audio"
REPO="/root/repositorio/d5n-videocast-source"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    --audio-dir) AUDIO_DIR="$2"; shift 2 ;;
    *) echo "argumento desconhecido: $1"; exit 64 ;;
  esac
done

SCRIPTS="$REPO/scripts"
GATE="$SCRIPTS/d5n-gatedurance-script-gate.py"
AUTOCORRECT="$SCRIPTS/d5n-gatedurance-autocorrect.py"
STATUS="$SCRIPTS/d5n_release_status.py"

# A. Já publicado?
if python3 "$STATUS" --date "$DATE" >/dev/null 2>&1; then
  exit 0   # publicado — silêncio (watchdog pattern)
fi

# Sem textos de roteiro? Nada que este observador possa fazer; sai em silêncio.
if ! ls "$AUDIO_DIR"/*.txt >/dev/null 2>&1; then
  exit 0
fi

# B. Roteiro já aprovado?
if python3 "$GATE" --date "$DATE" --audio-dir "$AUDIO_DIR" >/dev/null 2>&1; then
  echo "[D5N watchdog $DATE] Roteiro APROVADO e pronto para TTS/mix/deploy, mas o episódio ainda NÃO foi publicado. Verifique se o ciclo de geração (4h) ou o job de recuperação prosseguiu com a síntese e o deploy."
  exit 1
fi

# C. Roteiro com erros mecânicos → autocorrect + re-valida.
echo "[D5N watchdog $DATE] Roteiro NÃO aprovado. Aplicando auto-correção mecânica (GateDurance autocorrect)..."
bash "$SCRIPTS/d5n-gatedurance-loop.sh" --date "$DATE" --audio-dir "$AUDIO_DIR"
rc=$?
if [[ $rc -eq 0 ]]; then
  echo "[D5N watchdog $DATE] Roteiro aprovado após auto-correção. Pronto para TTS/mix/deploy."
  exit 1
fi

# D. Restam erros que exigem LLM.
echo "[D5N watchdog $DATE] Roteiro ainda NÃO aprovado após auto-correção. Erros restantes exigem regeneração por LLM (ex.: traduzir inglês, escrever mais conteúdo, corrigir data). O job de recuperação deve regenerar e re-tentar."
python3 "$GATE" --date "$DATE" --audio-dir "$AUDIO_DIR" >&2
exit 2
