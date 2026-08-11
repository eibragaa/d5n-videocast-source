#!/usr/bin/env bash
set -euo pipefail

REPO="${D5N_BASE:-/root/repositorio/d5n-videocast-source}"
VERIFY_SCRIPT="${D5N_VERIFY_SCRIPT:-/root/.hermes/scripts/d5n-verify-site.py}"
FEED="manha-conectada.xml"

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

# Alterações staged de outros pipelines não impedem commit --only. Apenas um
# conflito real pode bloquear a publicação; nesse caso o cron deve falhar.
if [ -n "$(git ls-files --unmerged 2>/dev/null)" ]; then
    printf 'ERRO: Git possui conflitos não resolvidos.\n' >&2
    exit 1
fi

python3 gerar_pagina_d5n.py --site-only
python3 scripts/gerar_manha_conectada_feed.py --repo "$REPO"
python3 scripts/gerar_manha_conectada_feed.py --repo "$REPO" --check-date "$RELEASE_DATE"
python3 "$VERIFY_SCRIPT"

# Publicação seletiva: nunca incorpora arquivos estranhos que estejam no checkout.
git add -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html "$FEED"
if git diff --cached --quiet -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html "$FEED"; then
  printf 'Site da Manhã Conectada já está publicado para %s.\n' "$RELEASE_DATE"
  exit 0
fi

git commit --only -m "feat: publicar Manhã Conectada de $RELEASE_DATE" -- \
  "$AUDIO" "$SOURCE" "$MANIFEST" index.html "$FEED"

if ! git fetch origin; then
  printf 'ERRO: falha ao atualizar as refs de origin; push cancelado.\n' >&2
  exit 1
fi

if git merge-base --is-ancestor origin/master HEAD; then
  : # O push abaixo é fast-forward.
else
  ancestor_status=$?
  if [ "$ancestor_status" -ne 1 ]; then
    printf 'ERRO: não foi possível comparar HEAD com origin/master; push cancelado.\n' >&2
    exit 1
  fi

  SAFETY_BRANCH="manha/pre-push-$RELEASE_DATE"
  if ! git branch -f "$SAFETY_BRANCH" HEAD; then
    printf 'ERRO: não foi possível criar a branch de segurança %s; push cancelado.\n' \
      "$SAFETY_BRANCH" >&2
    exit 1
  fi

  if ! git reset --mixed origin/master; then
    printf 'ERRO: falha ao reconciliar com origin/master; estado anterior preservado em %s.\n' \
      "$SAFETY_BRANCH" >&2
    exit 1
  fi

  for release_file in "$AUDIO" "$SOURCE" "$MANIFEST" index.html "$FEED"; do
    if [ ! -s "$release_file" ]; then
      printf 'ERRO: arquivo da release ausente ou vazio após reconciliação: %s; push cancelado.\n' \
        "$release_file" >&2
      exit 1
    fi
  done

  if ! git add -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html "$FEED"; then
    printf 'ERRO: falha ao preparar os arquivos da release reconciliada; push cancelado.\n' >&2
    exit 1
  fi
  if ! git commit --only -m "feat: publicar Manhã Conectada de $RELEASE_DATE" -- \
    "$AUDIO" "$SOURCE" "$MANIFEST" index.html "$FEED"; then
    printf 'ERRO: falha ao recriar o commit da release sobre origin/master; push cancelado.\n' >&2
    exit 1
  fi
fi

if ! git push origin HEAD:master; then
  printf 'ERRO: push para origin/master rejeitado; publicação interrompida sem force push.\n' >&2
  exit 1
fi
printf 'Manhã Conectada publicada no site: %s\n' "$RELEASE_DATE"
