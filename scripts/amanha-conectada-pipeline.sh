#!/usr/bin/env bash
# amanha-conectada-pipeline.sh — Pipeline completo do "Amanhã Conectada"
# Uso: bash amanha-conectada-pipeline.sh [--date=YYYY-MM-DD] [--dry-run]
#
# Etapas:
#   1. Coleta (já feita pelo cron 08c8645433ec às 10h) - usa o trends do dia
#   2. LLM escolhe 3-5 destaques + gera roteiro (3-5min)
#   3. TTS via edge-tts
#   4. Mix com trilhas + sidechain
#   5. Valida duração
#   6. Move pra /audio/ do site
#
# Saída: /root/repositorio/d5n-videocast-source/audio/amanha-conectada-{date}.mp3

set -euo pipefail

# Parse args
DATE="${DATE:-$(date +%Y-%m-%d)}"
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --date=*) DATE="${arg#*=}" ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Arg desconhecido: $arg"; exit 1 ;;
    esac
done

# Calcular dia da semana em PT-BR
WEEKDAY_PT=$(python3 -c "
from datetime import date
dias = ['segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado','domingo']
d = date.fromisoformat('$DATE')
print(dias[d.weekday()])
")
echo "📅 Hoje: $DATE ($WEEKDAY_PT)"

# Paths
REPO="/root/repositorio/d5n-videocast-source"
SCRIPTS="$REPO/scripts"
TRENDS_FILE="$HOME/.hermes/cron/output/drop5news-trends-$DATE.txt"
ROTEIRO_FILE="/tmp/amanha-conectada-${DATE}-roteiro.txt"
VOZ_FILE="/tmp/amanha-conectada-${DATE}-voz.mp3"
OUTPUT_FILE="$REPO/audio/amanha-conectada-${DATE}.mp3"
SOURCE_FILE="$REPO/source-amanha-${DATE}.md"

# Config
TRILHAS_DIR="/root/d5n-trilhas/audios_extraidos"
export TRILHAS_DIR
OPENCODE_GO_MODEL="deepseek-v4-flash"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ☀️ AMANHÃ CONECTADA — $DATE"
echo "════════════════════════════════════════════════════════"
echo ""

# Etapa 1: Verifica trends
echo "📂 Etapa 1/6: Verificando trends do dia..."
if [ ! -f "$TRENDS_FILE" ]; then
    echo "❌ Trends não encontradas: $TRENDS_FILE"
    echo "   O cron 08c8645433ec (Notícias 10h) precisa rodar antes"
    exit 1
fi
echo "   ✅ $TRENDS_FILE ($(wc -l < $TRENDS_FILE) linhas)"
echo ""

# Etapa 2: LLM gera roteiro
echo "🧠 Etapa 2/6: Gerando roteiro via $OPENCODE_GO_MODEL..."

# Prepara prompt - versão ENXUTA (o modelo consome muito em reasoning)
PROMPT=$(cat <<'PROMPT_EOF'
Você é apresentador do flash "Amanhã Conectada" (3min30s, pt-BR coloquial, ~600 palavras).

HOJE É ${WEEKDAY_PT} (${DATE}). Use o dia da semana correto no hook — NUNCA diga outro dia.

TAREFA: Escolha 3 destaques das notícias abaixo e gere roteiro EXPANDIDO com:
- HOOK (1-2 frases, 10-15s)
- BLOCO 1, 2, 3 (3-4 frases cada, COM CONTEXTO)
- CTA (10-15s, comentar/compartilhar)

REGRAS:
- Linguagem coloquial brasileira
- NÃO mencione fontes técnicas
- Total: 3min30s ± 30s (entre 540-660 palavras)
- Sem emojis
- Cada bloco deve ter CONTEXTO: explique o "porquê" importa, não só o fato

NOTÍCIAS DO DIA:
PROMPT_EOF
)

# Adiciona trends ao prompt (top 12 pra não sobrecarregar reasoning)
PROMPT="$PROMPT
$(head -30 $TRENDS_FILE)"

if [ "$DRY_RUN" = true ]; then
    echo "   [DRY-RUN] Pulando LLM"
    cp "$TRENDS_FILE" "$ROTEIRO_FILE"  # placeholder
else
    # Chama opencode-go via router-bridge (padrão homelab)
    # Usa Python direto pra pegar o content completo (sem o limit[:300] do bridge CLI)
    # max_tokens=8000 pra acomodar reasoning_tokens do deepseek-v4-flash (~4000 thinking)
    echo "$PROMPT" > /tmp/amanha-conectada-prompt.txt
    ROTEIRO_RAW=$(python3 <<'PYEOF'
import sys, json, time, urllib.request
from pathlib import Path

auth = json.load(open("/root/.hermes/auth.json"))
api_key = auth["credential_pool"]["opencode-go"][0]["access_token"]

with open("/tmp/amanha-conectada-prompt.txt") as f:
    prompt = f.read()

payload = json.dumps({
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 12000,  # margem pros 4000+ reasoning do deepseek-v4-flash
    "temperature": 0.7,
}).encode()

req = urllib.request.Request(
    "https://opencode.ai/zen/go/v1/chat/completions",
    data=payload,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    },
)
start = time.time()
try:
    r = urllib.request.urlopen(req, timeout=180)  # 3min — modelo tem reasoning longo
    elapsed = round(time.time() - start, 2)
    data = json.loads(r.read())
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        usage = data.get("usage", {})
        print(f"DEBUG: usage={usage}", file=sys.stderr)
        print(f"DEBUG: finish_reason={data.get('choices', [{}])[0].get('finish_reason')}", file=sys.stderr)
        print(f"ERRO: content vazio após {elapsed}s", file=sys.stderr)
        sys.exit(1)
    print(content)
except urllib.error.HTTPError as e:
    print(f"ERRO HTTP {e.code}: {e.read()[:200]}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERRO: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)
    echo "$ROTEIRO_RAW" > "$ROTEIRO_FILE"
    echo "   ✅ Roteiro salvo em $ROTEIRO_FILE"
    echo "   (chars: $(echo -n "$ROTEIRO_RAW" | wc -c))"
fi
echo ""

# Etapa 3: TTS via edge-tts
echo "🎙️ Etapa 3/6: Gerando voz (edge-tts)..."
if [ "$DRY_RUN" = true ]; then
    echo "   [DRY-RUN] Pulando TTS"
else
    # Extrai apenas o texto (sem headers === HOOK === etc)
    TEXTO=$(grep -v "^===" "$ROTEIRO_FILE" | grep -v "^$" | tr '\n' ' ')

    # Voz masculina pt-BR (mesma do D5N: 'pt-BR-AntonioNeural')
    edge-tts --voice pt-BR-AntonioNeural --rate "+0%" --pitch "+0Hz" \
        --text "$TEXTO" --write-media "$VOZ_FILE" 2>&1 | tail -3

    if [ ! -f "$VOZ_FILE" ]; then
        echo "❌ Falha no TTS"
        exit 1
    fi
    VOZ_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VOZ_FILE" | cut -d. -f1)
    echo "   ✅ Voz gerada: ${VOZ_DUR}s em $VOZ_FILE"

    # Validação de duração
    if [ "$VOZ_DUR" -lt 180 ]; then
        echo "⚠️  Áudio com ${VOZ_DUR}s — MENOR que 180s mínimo"
        echo "   O roteiro precisa ser expandido"
    elif [ "$VOZ_DUR" -gt 300 ]; then
        echo "⚠️  Áudio com ${VOZ_DUR}s — MAIOR que 300s máximo"
        echo "   O roteiro precisa ser condensado"
    fi
fi
echo ""

# Etapa 4: Mix
echo "🎚️ Etapa 4/6: Mixando voz + trilhas..."
if [ "$DRY_RUN" = true ]; then
    echo "   [DRY-RUN] Pulando mix"
else
    cd "$REPO"
    python3 "$SCRIPTS/amanha_conectada_mixer.py" \
        --voz "$VOZ_FILE" \
        --output "$OUTPUT_FILE"
fi
echo ""

# Etapa 5: Validação final
echo "✅ Etapa 5/6: Validação final..."
if [ "$DRY_RUN" = false ] && [ -f "$OUTPUT_FILE" ]; then
    FINAL_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_FILE" | cut -d. -f1)
    FINAL_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    FINAL_PEAK=$(ffmpeg -hide_banner -i "$OUTPUT_FILE" -af "volumedetect" -f null - 2>&1 | grep max_volume | awk '{print $5}')

    echo "   Duração: ${FINAL_DUR}s"
    echo "   Tamanho: $FINAL_SIZE"
    echo "   Peak: $FINAL_PEAK dB"
fi
echo ""

# Etapa 6: Gera source.md (formato leve)
echo "📝 Etapa 6/6: Gerando source.md..."
if [ "$DRY_RUN" = false ]; then
    cat > "$SOURCE_FILE" <<SOURCE_EOF
# AMANHÃ CONECTADA — ${DATE}

## Apresentação
Flash informativo diário — 3-5min — o que bombou nos principais portais e redes sociais.

## Pilares
- GLOBAL, BRASIL, TECH, ECONOMIA

## Roteiro

$(cat $ROTEIRO_FILE)

## Áudio
- Arquivo: amanha-conectada-${DATE}.mp3
- Duração: ${FINAL_DUR}s
- Tamanho: ${FINAL_SIZE}

## CTA
Compartilhe, comente, siga @jeanbraga.ia
SOURCE_EOF
    echo "   ✅ $SOURCE_FILE"
fi
echo ""

echo "════════════════════════════════════════════════════════"
echo "  ☀️ AMANHÃ CONECTADA — PIPELINE CONCLUÍDO"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📁 Arquivos gerados:"
echo "   - Roteiro: $ROTEIRO_FILE"
echo "   - Voz:     $VOZ_FILE"
echo "   - MP3:     $OUTPUT_FILE"
echo "   - Source:  $SOURCE_FILE"
echo ""
