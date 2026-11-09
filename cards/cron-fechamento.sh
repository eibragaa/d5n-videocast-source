#!/usr/bin/env bash
set -euo pipefail
# Wrapper for generating and sending the fechamento card
# Uses the Python script gerar_fechamento.py via the pilpython wrapper
# Assumes $TELEGRAM_BOT_TOKEN is available (loaded from ~/.hermes/.env)

# Paths
PYTHON_WRAPPER="$HOME/.local/bin/pilpython"
SCRIPT="$HOME/.hermes/scripts/cards/gerar_fechamento.py"
OUT_DIR="$HOME/.hermes/cards"
mkdir -p "$OUT_DIR"

# Generate card(s)
"$PYTHON_WRAPPER" "$SCRIPT" --out "$OUT_DIR"

# Send most recent PNG to Telegram channel
CARD=$(ls -t "$OUT_DIR"/*.png | head -n1)
if [ -z "$CARD" ]; then
    echo "No card generated"
    exit 1
fi
# Load bot token from .env if not already set
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    set -a
    . "$HOME/.hermes/.env"
    set +a
fi
# Send via Telegram API
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto"     -F chat_id="-1004312849084" -F photo="@$CARD"
