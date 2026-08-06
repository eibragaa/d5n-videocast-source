#!/usr/bin/env bash
# GateDurance Loop — orquestra a auto-correção e validação do roteiro até o texto
# ficar aprovado (GateDurance verde) ou esgotar as tentativas. É o "regenerate com
# correções" do pipeline: sempre tenta levar o texto a um estado publicável.
#
# Uso: bash d5n-gatedurance-loop.sh [--date YYYY-MM-DD] [--audio-dir /tmp/d5n_audio]
# Exit: 0 = roteiro aprovado (pronto para TTS)
#       2 = exaustão sem aprovação (restam erros que exigem regeneração LLM)
set -uo pipefail

DATE="$(TZ=America/Sao_Paulo date +%Y-%m-%d)"
AUDIO_DIR="/tmp/d5n_audio"
MAX_CORRECT=3

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    --audio-dir) AUDIO_DIR="$2"; shift 2 ;;
    *) echo "argumento desconhecido: $1"; exit 64 ;;
  esac
done

SCRIPTS="/root/repositorio/d5n-videocast-source/scripts"
GATE="$SCRIPTS/d5n-gatedurance-script-gate.py"
AUTOCORRECT="$SCRIPTS/d5n-gatedurance-autocorrect.py"
RESTORE="$SCRIPTS/d5n-gatedurance-snapshot-restore.py"
REPO="/root/repositorio/d5n-videocast-source"

echo "=== GateDurance Loop — $DATE ==="

# 0) FONTE DA VERDADE: se existe snapshot aprovado, restaura os txts a partir dele
#    (não confia em /tmp/d5n_audio, que jobs concorrentes podem corromper com
#    versões em inglês/markdown). O texto aprovado é o que vai para o TTS.
if [[ -f "$REPO/podcast-scripts/$DATE.json" ]]; then
  echo "Snapshot aprovado encontrado. Restaurando txts a partir dele..."
  python3 "$RESTORE" --date "$DATE" --snapshot-dir "$REPO/podcast-scripts" --audio-dir "$AUDIO_DIR"
  rc=$?
  if [[ $rc -eq 0 ]]; then
    echo "OK — txts restaurados do snapshot aprovado (pronto para TTS)."
    exit 0
  fi
  if [[ $rc -eq 2 ]]; then
    echo "Snapshot incompleto; seguindo para validação dos txts atuais."
  else
    echo "Snapshot restaurado mas reprovado; tentando autocorrect sobre ele..."
  fi
else
  echo "Sem snapshot aprovado para $DATE; validando/corrigindo txts atuais."
fi

# 1) Primeira validação (sem correção).
python3 "$GATE" --date "$DATE" --audio-dir "$AUDIO_DIR" >/dev/null 2>&1
rc=$?
if [[ $rc -eq 0 ]]; then
  echo "PASSOU direto no GateDurance (sem correção necessária)."
  exit 0
fi
echo "GateDurance bloqueou na 1ª passada. Aplicando auto-correção mecânica..."

# 2) Auto-correção determinística + re-validação, até MAX_CORRECT vezes.
for ((i=1; i<=MAX_CORRECT; i++)); do
  python3 "$AUTOCORRECT" --date "$DATE" --audio-dir "$AUDIO_DIR" >/dev/null 2>&1
  rc=$?
  if [[ $rc -eq 0 ]]; then
    echo "Aprovado após auto-correção (iteração $i)."
    exit 0
  fi
  echo "Iteração $i: ainda bloqueado — restam erros que exigem regeneração LLM."
done

# 3) Exaustão: mostra o estado atual para o agente regenerar e re-tentar.
echo ""
echo "=== EXAUSTÃO (GateDurance Loop) ==="
echo "Depois de $MAX_CORRECT auto-correções, o roteiro ainda não passa. O que resta"
echo "exige regeneração por LLM (traduzir inglês, escrever mais conteúdo, corrigir"
echo "data/estrutura). Estado atual:"
python3 "$GATE" --date "$DATE" --audio-dir "$AUDIO_DIR"
exit 2
