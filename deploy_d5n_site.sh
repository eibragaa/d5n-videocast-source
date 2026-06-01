#!/usr/bin/env bash
# deploy_d5n_site.sh — Gera site D5N e faz deploy no Netlify com validação
# Totalmente no_agent (zero tokens por execução)
# Só faz push se passar em todas as validações.
# Em caso de falha, marca /tmp/.deploy-d5n-failed para recuperação

set -euo pipefail

DATE=$(date +%Y-%m-%d)
REPO="/root/repositorio/d5n-videocast-source"
LOG="/tmp/deploy-d5n-${DATE}.log"
FAILED=0

echo "[$(date '+%H:%M:%S')] 🚀 Deploy D5N - ${DATE}" | tee "$LOG"

cd "$REPO"

# Salvar hash do último commit bom ANTES de qualquer alteração
LAST_GOOD=$(git rev-parse HEAD)
echo "$LAST_GOOD" > /tmp/.deploy-d5n-last-good
echo "✅ Último commit bom salvo: ${LAST_GOOD:0:8}" | tee -a "$LOG"

# ── Validação 1: Pipeline rodou? ──
TRENDS_FILE="/root/.hermes/cron/output/drop5news-trends-${DATE}.txt"
FALLBACK_FILE="${REPO}/source.md"

if [ -f "$TRENDS_FILE" ]; then
    echo "✅ Pipeline: trends encontrados ($(wc -l < "$TRENDS_FILE") linhas)" | tee -a "$LOG"
elif [ -f "$FALLBACK_FILE" ] && [ -s "$FALLBACK_FILE" ]; then
    echo "⚠️  Pipeline sem trends — usando fallback de source.md" | tee -a "$LOG"
else
    echo "❌ BLOQUEADO: Sem trends e sem source.md de fallback" | tee -a "$LOG"
    FAILED=1
fi

# ── Validação 2: Áudio do pipeline ──
CRON_AUDIO="/root/.hermes/cron/output"
mkdir -p audio
LATEST_MP3=$(ls -t "$CRON_AUDIO"/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    # Extrair o próximo número de episódio da pasta audio/
    # Formato válido: d5n-ep{NNN}-{DATE}.mp3 ou d5n-ep{NNN}.mp3
    LAST_NUM=$(ls audio/d5n-ep*.mp3 2>/dev/null | grep -oP 'ep\K\d+' | sort -n | tail -1)
    if [ -z "$LAST_NUM" ]; then
        NEXT_NUM=1
    else
        NEXT_NUM=$((10#$LAST_NUM + 1))
    fi
    EP_NUM=$(printf "%03d" "$NEXT_NUM")
    DEST="audio/d5n-ep${EP_NUM}-${DATE}.mp3"
    if [ ! -f "$DEST" ] || [ "$LATEST_MP3" -nt "$DEST" ]; then
        cp "$LATEST_MP3" "$DEST"
        echo "✅ Áudio copiado: $DEST (ep #$EP_NUM, $(du -h "$DEST" | cut -f1))" | tee -a "$LOG"
    else
        echo "ℹ️  Áudio já atualizado" | tee -a "$LOG"
    fi
else
    echo "ℹ️  Nenhum MP3 novo no pipeline" | tee -a "$LOG"
fi

# ── Gerar site (se falhar, script aborta com exit 1) ──
if [ "$FAILED" -eq 0 ]; then
    echo "📄 Gerando site..." | tee -a "$LOG"
    if python3 gerar_pagina_d5n.py 2>&1 | tee -a "$LOG"; then
        echo "✅ Site gerado com sucesso" | tee -a "$LOG"
    else
        echo "❌ BLOQUEADO: gerar_pagina_d5n.py falhou" | tee -a "$LOG"
        FAILED=1
    fi
fi

# ── Validação 3: Site tem notícias? ──
if [ "$FAILED" -eq 0 ]; then
    NEWS_COUNT=$(grep -oP '<strong>\K\d+(?=</strong><span>notícias)' index.html || echo "0")
    if [ "$NEWS_COUNT" -eq 0 ]; then
        echo "❌ BLOQUEADO: index.html gerado com 0 notícias" | tee -a "$LOG"
        FAILED=1
    else
        echo "✅ Validação: $NEWS_COUNT notícias no index.html" | tee -a "$LOG"
    fi
fi

# ── Validação 4: source.md tem conteúdo? ──
if [ "$FAILED" -eq 0 ]; then
    if [ -f "source.md" ] && [ "$(wc -c < source.md)" -gt 100 ]; then
        echo "✅ Validação: source.md com $(wc -c < source.md) bytes" | tee -a "$LOG"
    else
        echo "⚠️  source.md vazio ou inexistente — deploy continua" | tee -a "$LOG"
    fi
fi

# ── Git push (só se passou em tudo) ──
if [ "$FAILED" -eq 0 ]; then
    echo "⬆️  Push para GitHub..." | tee -a "$LOG"
    git add .
    if git diff --quiet && git diff --staged --quiet; then
        echo "📭 Nada novo para commitar" | tee -a "$LOG"
    else
        git commit -m "📰 D5N - ${DATE}" 2>&1 | tee -a "$LOG"
        git push origin master 2>&1 | tee -a "$LOG"
        echo "✅ Push feito! Netlify fará deploy automático." | tee -a "$LOG"
    fi
    # Limpar marcador de falha se existir
    rm -f /tmp/.deploy-d5n-failed
else
    echo "❌ DEPLOY BLOQUEADO — Validações falharam. Site não foi atualizado." | tee -a "$LOG"
    echo "   Log: $LOG" | tee -a "$LOG"
    # Marcar para recuperação por outro agente
    echo "$DATE" > /tmp/.deploy-d5n-failed
    echo "Motivo:" >> /tmp/.deploy-d5n-failed
    grep 'BLOQUEADO\|ERRO\|❌' "$LOG" | head -3 >> /tmp/.deploy-d5n-failed
    echo "Log: $LOG" >> /tmp/.deploy-d5n-failed
fi

echo ""
echo "═══════════════════════════════════" | tee -a "$LOG"
if [ "$FAILED" -eq 0 ]; then
    echo "✅ Deploy D5N concluído $(date '+%H:%M:%S')" | tee -a "$LOG"
else
    echo "❌ Deploy D5N FALHOU $(date '+%H:%M:%S')" | tee -a "$LOG"
fi
echo "🌐 https://d5n-daily.netlify.app/" | tee -a "$LOG"
echo "═══════════════════════════════════" | tee -a "$LOG"
exit "$FAILED"
