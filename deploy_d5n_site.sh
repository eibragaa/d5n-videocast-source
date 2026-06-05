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
COUNTER_FILE="episode-counter.json"
VALIDATOR="${REPO}/scripts/validate_mp3.py"
LATEST_MP3=$(ls -t "$CRON_AUDIO"/d5n-podcast-*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    # 🔒 VALIDAÇÃO MULTI-CAMADA: só copia se o MP3 for realmente do D5N
    # Camada 1: Nome (d5n-podcast-*.mp3), Camada 2: Tamanho >5MB,
    # Camada 3: Header MP3, Camada 4: Duração >3min
    if python3 "$VALIDATOR" "$LATEST_MP3" 2>/dev/null; then
        echo "✅ Validação MP3: aprovado ($(du -h "$LATEST_MP3" | cut -f1))" | tee -a "$LOG"
    else
        echo "❌ BLOQUEADO: MP3 inválido — $(python3 "$VALIDATOR" "$LATEST_MP3" 2>&1 | head -1)" | tee -a "$LOG"
        FAILED=1
        # Pula copia/contador, vai direto pro bloco de validação final
    fi

    if [ "$FAILED" -eq 0 ]; then
        # 🔥 CORREÇÃO: verificar se já existe episódio para a DATA DE HOJE
        # Se sim, reutilizar o número (sobrescrever) em vez de criar novo
        TODAY_EP=""
        if [ -f "$COUNTER_FILE" ]; then
            TODAY_EP=$(python3 -c "
import json
d=json.load(open('$COUNTER_FILE'))
history=d.get('history',[])
# Procura episódio com a data de hoje
for e in history:
    if e.get('date')=='$DATE':
        print(e['num'])
        break
" 2>/dev/null)
        fi

        if [ -n "$TODAY_EP" ]; then
            # Já existe episódio para hoje — REUTILIZAR número e sobrescrever
            EP_NUM="$TODAY_EP"
            echo "♻️  Episódio #$EP_NUM já existe para hoje — sobrescrevendo" | tee -a "$LOG"
        else
            # Lê o contador persistente e calcula próximo
            if [ -f "$COUNTER_FILE" ]; then
                LAST_NUM=$(python3 -c "import json; d=json.load(open('$COUNTER_FILE')); print(d.get('last_episode',0))" 2>/dev/null)
            else
                LAST_NUM=0
            fi
            if [ -z "$LAST_NUM" ] || [ "$LAST_NUM" = "0" ]; then
                LAST_NUM=$(ls audio/d5n-ep*.mp3 2>/dev/null | grep -oP 'ep\K\d+' | sort -n | tail -1)
                LAST_NUM=${LAST_NUM:-0}
            fi
            NEXT_NUM=$((10#$LAST_NUM + 1))
            EP_NUM=$(printf "%03d" "$NEXT_NUM")
        fi

        DEST="audio/d5n-ep${EP_NUM}-${DATE}.mp3"
        cp "$LATEST_MP3" "$DEST"
        echo "✅ Áudio copiado: $DEST (ep #$EP_NUM, $(du -h "$DEST" | cut -f1))" | tee -a "$LOG"

        # Atualiza contador persistente (sempre, mesmo se sobrescrevendo)
        python3 -c "
import json
with open('$COUNTER_FILE') as f: d=json.load(f)
if 'history' not in d: d['history']=[]
today_idx = next((i for i,e in enumerate(d['history']) if e.get('date')=='$DATE'), -1)
if today_idx >= 0:
    d['history'][today_idx]['exists']=True
    d['history'][today_idx]['file']='d5n-ep$EP_NUM-$DATE.mp3'
else:
    d['history'].append({'num':'$EP_NUM','date':'$DATE','file':'d5n-ep$EP_NUM-$DATE.mp3','exists':True})
# last_episode só avança se EP_NUM > actual
ep_int = int('$EP_NUM')
if ep_int > d.get('last_episode',0):
    d['last_episode']=ep_int
else:
    d['last_episode']=d.get('last_episode',ep_int)
d['updated']='$DATE'
json.dump(d,open('$COUNTER_FILE','w'),indent=2)
"
        echo "✅ Contador atualizado: episode-counter.json → #$EP_NUM" | tee -a "$LOG"
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
