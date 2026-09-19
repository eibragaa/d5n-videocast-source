#!/usr/bin/env bash
# backup-diario-d5n.sh — Backup diário dos manifests e episódios do D5N
# Insight 2 (Higienização) + Insight 10 (Automação de auditoria)
# Executar via cron diariamente às 02:00

set -euo pipefail

REPO_DIR="/root/repositorio/d5n-videocast-source"
BACKUP_BASE="/root/.hermes/backups/d5n"
DATA=$(date +%Y-%m-%d)
BACKUP_DIR="$BACKUP_BASE/daily/$DATA"

mkdir -p "$BACKUP_DIR/manifests"
mkdir -p "$BACKUP_DIR/audio"
mkdir -p "$BACKUP_DIR/state"

# 1. Backup dos manifests
if [ -d "$REPO_DIR/manifests" ]; then
  rsync -a --delete "$REPO_DIR/manifests/" "$BACKUP_DIR/manifests/" 2>/dev/null || cp -r "$REPO_DIR/manifests" "$BACKUP_DIR/manifests"
  echo "[backup] manifests → $BACKUP_DIR/manifests"
fi

# 2. Backup dos áudios recentes (últimos 7 dias)
if [ -d "$REPO_DIR/audio" ]; then
  find "$REPO_DIR/audio" -type f -name "*.mp3" -mtime -7 -exec cp {} "$BACKUP_DIR/audio/" \; 2>/dev/null || true
  echo "[backup] áudios recentes → $BACKUP_DIR/audio"
fi

# 3. Backup de estado (feed.json, episode-counter.json, etc.)
for f in feed.json episode-counter.json podcast.xml d5n-feed.xml manha-conectada.xml fechamento.xml; do
  if [ -f "$REPO_DIR/$f" ]; then
    cp "$REPO_DIR/$f" "$BACKUP_DIR/state/"
    echo "[backup] $f → $BACKUP_DIR/state/"
  fi
done

# 4. Limpeza: manter apenas últimos 30 dias de backups diários
find "$BACKUP_BASE/daily" -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true

# 5. Relatório
REPORT="/root/.hermes/state/d5n/backup-$DATA.log"
{
  echo "Backup D5N diário — $DATA"
  echo "Destino: $BACKUP_DIR"
  echo "Tamanho total: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
  echo "Arquivos: $(find "$BACKUP_DIR" -type f | wc -l)"
  echo "Retidos: $(find "$BACKUP_BASE/daily" -type d | wc -l) dias"
} > "$REPORT"

echo "✔ Backup concluído: $BACKUP_DIR"
