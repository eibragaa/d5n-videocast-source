#!/usr/bin/env bash
# auditoria-agente.sh — Auditoria semanal do agente D5N
# Insight 2 (Higienização) + Insight 10 (Automação de auditoria) do vídeo Bruno Okamoto
# Uso: ./auditar-agente.sh [report-path]
# Exemplo: ./auditar-agente.sh /root/.hermes/state/d5n/auditoria-2026-09-19.md

set -euo pipefail

REPO_DIR="/root/repositorio/d5n-videocast-source"
REPORT_FILE="${1:-/root/.hermes/state/d5n/auditoria-$(date +%Y-%m-%d).md}"
STATE_DIR="/root/.hermes/state/d5n"
MANIFESTS_DIR="$REPO_DIR/manifests"
AUDIO_DIR="$REPO_DIR/audio"
BACKUP_DIR="/root/.hermes/backups/d5n"

mkdir -p "$STATE_DIR"
mkdir -p "$(dirname "$REPORT_FILE")"

echo "# Auditoria Semanal D5N — $(date +%Y-%m-%d)" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. RAM e processos
echo "## 1. Uso de RAM e Processos (últimos 7 dias)" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "Data: $(date)" >> "$REPORT_FILE"
if command -v free >/dev/null 2>&1; then
  free -h >> "$REPORT_FILE" 2>&1 || echo "free não disponível" >> "$REPORT_FILE"
else
  echo "free não disponível" >> "$REPORT_FILE"
fi
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 2. Storage
echo "## 2. Storage" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
if command -v df >/dev/null 2>&1; then
  df -h / >> "$REPORT_FILE" 2>&1 || echo "df não disponível" >> "$REPORT_FILE"
else
  echo "df não disponível" >> "$REPORT_FILE"
fi
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 3. Arquivos parados em manifests (>30 dias)
echo "## 3. Manifests com >30 dias (arquivar)" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
if [ -d "$MANIFESTS_DIR" ]; then
  find "$MANIFESTS_DIR" -type f -name "*.txt" -mtime +30 2>/dev/null | while read -r f; do
    echo "- $f (modificado em $(stat -c %y "$f" 2>/dev/null || echo '?'))"
  done
  echo "Total: $(find "$MANIFESTS_DIR" -type f -name '*.txt' -mtime +30 2>/dev/null | wc -l) arquivos"
else
  echo "Diretório manifests não existe"
fi
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 4. Skills usadas vs não usadas (rastro pelo index.json)
echo "## 4. Skills / Execuções Recentes" >> "$REPORT_FILE"
INDEX_FILE="$STATE_DIR/index.json"
if [ -f "$INDEX_FILE" ]; then
  echo "Últimas execuções (do index.json):" >> "$REPORT_FILE"
  python3 -c "
import json, sys
from datetime import datetime, timedelta
try:
    with open('$INDEX_FILE') as f:
        data = json.load(f)
    executions = data.get('execucoes', [])[-10:]
    for e in executions:
        print(f\"- {e.get('data','?')}: {e.get('script','?')} — status: {e.get('status','?')}\")
    # Skills não usadas nos últimos 30 dias
    uso_recrecente = set()
    cutoff = datetime.now() - timedelta(days=30)
    for e in data.get('execucoes', []):
        try:
            d = datetime.fromisoformat(e.get('data','2000-01-01'))
            if d > cutoff:
                uso_recrecente.add(e.get('script'))
        except:
            pass
    todas_skills = {'gerar_pagina_d5n.py', 'manha-conectada_pipeline.py', 'fechamento_pipeline.py', 'drop5news-mixer-v10.py', 'validate_feeds.py'}
    nao_usadas = todas_skills - uso_recrecente
    if nao_usadas:
        print(f'\nSkills não usadas nos últimos 30 dias: {nao_usadas}')
    else:
        print('\n Todas as skills foram usadas nos últimos 30 dias')
except Exception as ex:
    print(f'Erro ao ler index: {ex}')
" 2>&1 >> "$REPORT_FILE" || echo "Erro ao processar index" >> "$REPORT_FILE"
else
  echo "index.json não encontrado — execute primeiro o script de indexação" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 5. Erros nos logs
echo "## 5. Erros Recentes (logs dos últimos 7 dias)" >> "$REPORT_FILE"
LOG_DIR="/root/.hermes/logs"
if [ -d "$LOG_DIR" ]; then
  find "$LOG_DIR" -type f -name "*.log" -mtime -7 2>/dev/null | while read -r log; do
    erros=$(grep -i "error\|erro\|falhou\|failed" "$log" 2>/dev/null | tail -20)
    if [ -n "$erros" ]; then
      echo "### $log" >> "$REPORT_FILE"
      echo '```' >> "$REPORT_FILE"
      echo "$erros" >> "$REPORT_FILE"
      echo '```' >> "$REPORT_FILE"
    fi
  done
  echo "Log verificado: $LOG_DIR" >> "$REPORT_FILE"
else
  echo "Diretório de logs não encontrado: $LOG_DIR" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 6. Status dos pipelines
echo "## 6. Status dos Pipelines" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
# Verifica se há manifests recentes para D5N
if [ -d "$MANIFESTS_DIR/d5n" ]; then
  manifests_d5n=$(find "$MANIFESTS_DIR/d5n" -type f -name "*.txt" -mtime -1 2>/dev/null | wc -l)
  echo "D5N: $([ "$manifests_d5n" -gt 0 ] && echo "✅ manifests hoje" || echo "⚠️ sem manifests hoje ($manifests_d5n encontrado(s) em 24h)")"
else
  echo "D5N: ⚠️ pasta manifests/d5n não existe"
fi

# Verifica último áudio gerado
if [ -d "$AUDIO_DIR" ]; then
  ultimo_audio=$(find "$AUDIO_DIR" -type f -name "*.mp3" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
  if [ -n "$ultimo_audio" ]; then
    echo "Último áudio: $ultimo_audio"
  else
    echo "Não há áudios em $AUDIO_DIR"
  fi
else
  echo "Diretório audio não encontrado"
fi
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "---" >> "$REPORT_FILE"
echo "*Gerado automaticamente por auditoria-agente.sh*" >> "$REPORT_FILE"

echo "✔ Auditoria salva em: $REPORT_FILE"
