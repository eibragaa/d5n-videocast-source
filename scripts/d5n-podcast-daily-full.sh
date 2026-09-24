#!/usr/bin/env bash
# d5n-podcast-daily-full.sh — Pipeline completo do episódio D5N diário.
#
# Fluxo completo (tudo automaticamente):
#   1. Gerar roteiros a partir de MC/FM (gerar_roteiro_d5n.py)
#   2. Copiar manifests para audio_dir (SEM apagar episódios antigos)
#   3. Sintetizar TTS (.txt → .mp3 via edge_tts)
#   4. Executar mixer v10 (mixa trilhas + TTS)
#   5. Gerar feeds RSS
#   6. Regenerar index.html
#   7. Git push para Netlify
#
# Usage: bash d5n-podcast-daily-full.sh [--date YYYY-MM-DD]
#
# FIX: não usa rm -rf audio/ — preserva episódios históricos.
# FIX: nomeia o episódio como d5n-ep{NNN}-{DATE}.mp3 com base no episode-counter.json.

set -euo pipefail

REPO="/root/repositorio/d5n-videocast-source"
SCRIPTS="$REPO/scripts"
TODAY="${1:-$(date +%Y-%m-%d)}"
AUDIO_DIR="$REPO/audio"
MANIFESTS_DIR="$REPO/manifests/d5n/$TODAY"

if [[ $(date -d "$TODAY" +%u) -eq 7 ]]; then
    echo "⚠ Domingo — pipeline em manutenção. Nada a fazer."
    exit 0
fi

cd "$REPO"

echo "============================================================"
echo "D5N DAILY PODCAST — PIPELINE COMPLETO"
echo "Data: $TODAY"
echo "============================================================"

# 1. Gerar roteiros a partir de MC/FM
echo ""
echo "[1/7] Gerando roteiros a partir de MC/FM..."
if [ -f "$SCRIPTS/gerar_roteiro_d5n.py" ]; then
    if python3 -B "$SCRIPTS/gerar_roteiro_d5n.py" 2>&1; then
        echo "  ✓ Roteiros gerados"
    else
        echo "  ⚠ Falha ao gerar roteiros (continuando com manifests existentes)"
    fi
else
    echo "  ⚠ gerar_roteiro_d5n.py não encontrado"
fi

# 2. Verificar manifests e preparar audio_dir
echo ""
echo "[2/7] Preparando manifestos..."
if [ -d "$MANIFESTS_DIR" ]; then
    count=$(find "$MANIFESTS_DIR" -name '*.txt' -type f | wc -l)
    echo "  ✓ $count manifests encontrados"
    # Clean only section .txt/.mp3 files, preserve old episode MP3s
    rm -f "$AUDIO_DIR"/*.txt "$AUDIO_DIR"/coldopen.mp3 "$AUDIO_DIR"/intro.mp3 "$AUDIO_DIR"/mundo.mp3 "$AUDIO_DIR"/brasil.mp3 "$AUDIO_DIR"/tecnologia.mp3 "$AUDIO_DIR"/economia.mp3 "$AUDIO_DIR"/interacao.mp3 "$AUDIO_DIR"/ofertas.mp3 "$AUDIO_DIR"/frase.mp3 "$AUDIO_DIR"/recomendacoes.mp3 "$AUDIO_DIR"/historia.mp3 "$AUDIO_DIR"/outro.mp3 "$AUDIO_DIR"/manifest.json "$AUDIO_DIR"/silence*.mp3 2>/dev/null || true
    mkdir -p "$AUDIO_DIR"
    cp "$MANIFESTS_DIR"/*.txt "$AUDIO_DIR/" 2>/dev/null || true
    echo "  ✓ Manifestos copiados para $AUDIO_DIR (episódios antigos preservados)"
else
    echo "  ✗ Sem manifests para $TODAY"
    exit 1
fi

# 3. Sintetizar TTS
echo ""
echo "[3/7] Sintetizando TTS (edge_tts)..."
if python3 -B "$SCRIPTS/d5n-tts-synthesize.py" \
    --audio-dir "$AUDIO_DIR" \
    --editorial-date "$TODAY" 2>&1; then
    echo "  ✓ TTS completo"
else
    echo "  ⚠ TTS parcial ou falhou (continuando se tiver áudio suficiente)"
fi

# 4. Determinar número do próximo episódio
echo ""
echo "[4/7] Determinando número do episódio..."
NEXT_EP=$(python3 -B -c "
import json
from pathlib import Path
counter = json.loads(Path('$REPO/episode-counter.json').read_text())
n = int(counter['last_episode']) + 1
print(f'{n:03d}')
" 2>/dev/null || echo "001")
EP_FILE="d5n-ep${NEXT_EP}-${TODAY}.mp3"
echo "  ✓ Próximo episódio: #$NEXT_EP → $EP_FILE"

# 5. Executar mixer v10
echo ""
echo "[5/7] Executando mixer D5N v10..."
TMP_OUTPUT="/tmp/d5n_mixado_${TODAY}.mp3"
if python3 -B "$SCRIPTS/drop5news-mixer-v10.py" \
    --audio-dir "$AUDIO_DIR" \
    --output "$TMP_OUTPUT" \
    --editorial-date "$TODAY" 2>&1; then
    echo "  ✓ Mixer executado com sucesso"
    if [ -f "$TMP_OUTPUT" ]; then
        cp "$TMP_OUTPUT" "$AUDIO_DIR/$EP_FILE"
        echo "  ✓ Áudio salvo em $AUDIO_DIR/$EP_FILE"
    fi
else
    echo "  ✗ Mixer falhou"
    exit 1
fi

# 6. Atualizar episode-counter.json
echo ""
echo "[6/7] Atualizando episode-counter.json..."
python3 -B -c "
import json
from pathlib import Path
counter = json.loads(Path('$REPO/episode-counter.json').read_text())
counter['last_episode'] = int('$NEXT_EP')
counter['updated'] = '$TODAY'
counter['history'].insert(0, {
    'num': '$NEXT_EP',
    'date': '$TODAY',
    'file': '$EP_FILE',
    'exists': True,
    'duration': '521'
})
Path('$REPO/episode-counter.json').write_text(json.dumps(counter, indent=2, ensure_ascii=False))
print(f'  ✓ Episode counter atualizado: episódio #$NEXT_EP')
" 2>&1

# 7. Gerar feeds RSS
echo ""
echo "[7/7] Gerando feeds RSS..."
python3 -B "$SCRIPTS/generate_all_feeds.py" 2>&1 || echo "  ⚠ Erro ao gerar feeds"

# 8. Regenerar index.html
echo ""
echo "[8/8] Regenerando index.html..."
python3 -B "$SCRIPTS/gerar_pagina_d5n.py" 2>&1 || echo "  ⚠ Erro ao regenerar index"

# 9. Git push
echo ""
echo "[9/9] Deploy via git push..."
cd "$REPO"
git add -A
git commit -m "feat: D5N ep$NEXT_EP $TODAY — automatic sync" 2>/dev/null || echo "  → Nada para commitar"
git push origin HEAD:master 2>&1 || echo "  ⚠ Push falhou"

echo ""
echo "============================================================"
echo "D5N DAILY PROCESS CONCLUIDO — Episódio #$NEXT_EP ($TODAY)"
echo "============================================================"
echo ""
echo "Site: https://d5n-daily.netlify.app/"
echo "Podcast: https://d5n-daily.netlify.app/podcast.xml"
echo "Episódio: https://d5n-daily.netlify.app/audio/$EP_FILE"