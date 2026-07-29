#!/usr/bin/env bash
set -euo pipefail

REPO="${D5N_BASE:-/root/repositorio/d5n-videocast-source}"
VERIFY_SCRIPT="${D5N_VERIFY_SCRIPT:-/root/.hermes/scripts/d5n-verify-site.py}"

if [ "$#" -ne 3 ]; then
  printf 'Uso: %s AUDIO SOURCE MANIFEST\n' "$0" >&2
  exit 2
fi

AUDIO=$(realpath -e "$1")
SOURCE=$(realpath -e "$2")
MANIFEST=$(realpath -e "$3")

for artifact in "$AUDIO" "$SOURCE" "$MANIFEST"; do
  case "$artifact" in
    "$REPO"/*) ;;
    *) printf 'ERRO: artefato fora do repositório: %s\n' "$artifact" >&2; exit 2 ;;
  esac
done

AUDIO_NAME=$(basename "$AUDIO")
if [[ ! "$AUDIO_NAME" =~ ^manha-conectada-([0-9]{4}-[0-9]{2}-[0-9]{2})\.mp3$ ]]; then
  printf 'ERRO: áudio não canônico: %s\n' "$AUDIO_NAME" >&2
  exit 2
fi
RELEASE_DATE="${BASH_REMATCH[1]}"
[ "$(basename "$SOURCE")" = "source-manha-$RELEASE_DATE.md" ] || { printf 'ERRO: source não corresponde à data do áudio.\n' >&2; exit 2; }
[ "$(basename "$MANIFEST")" = "$RELEASE_DATE.json" ] || { printf 'ERRO: manifesto não corresponde à data do áudio.\n' >&2; exit 2; }

cd "$REPO"

# Verifica estado Git antes de prosseguir
if ! git diff --cached --quiet --exit-code 2>/dev/null || [ -n "$(git ls-files --unmerged 2>/dev/null)" ]; then
    printf '⚠️ Git com conflitos — ignorando push, site pode estar desatualizado.\n'
    python3 gerar_pagina_d5n.py --site-only
    python3 "$VERIFY_SCRIPT"
    printf 'Site gerado localmente. Push não realizado (conflitos Git).\n'
    exit 0
fi

python3 gerar_pagina_d5n.py --site-only
python3 "$VERIFY_SCRIPT"

# Publicação seletiva: nunca incorpora arquivos estranhos que estejam no checkout.
git add -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html
if git diff --cached --quiet -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html; then
  printf 'Site da Manhã Conectada já está publicado para %s.\n' "$RELEASE_DATE"
  exit 0
fi

git commit --only -m "feat: publicar Manhã Conectada de $RELEASE_DATE" -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html
git push origin HEAD:master
printf 'Manhã Conectada publicada no site: %s\n' "$RELEASE_DATE"
