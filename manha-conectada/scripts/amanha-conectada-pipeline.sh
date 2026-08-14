#!/usr/bin/env bash
# Compatibilidade: encaminha o pipeline legado para a implementação atual.
set -euo pipefail
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --date=*) ARGS+=("--date" "${arg#*=}") ;;
    --allow-nonbusiness-day|--prototype) ARGS+=("$arg") ;;
    --dry-run) python3 -m py_compile "$(dirname "$0")/manha_conectada_pipeline.py" "$(dirname "$0")/amanha_conectada_mixer.py"; exit 0 ;;
    *) echo "Argumento desconhecido: $arg" >&2; exit 2 ;;
  esac
done
exec python3 "$(dirname "$0")/manha_conectada_pipeline.py" "${ARGS[@]}"
