#!/usr/bin/env bash
# roda o pipeline telejornal com Pexels + DeepSeek keywords
set -e
cd /root/ig-reels/telejornal
export PEXELS_API_KEY=$(grep '^PEXELS_API_KEY=' /root/.hermes/.env | cut -d= -f2-)
export DEEPSEEK_API_KEY=$(grep '^DEEPSEEK_API_KEY=' /root/.hermes/.env | cut -d= -f2-)
/root/.venv-telejornal/bin/python telejornal.py --text "$(cat noticia.txt)" --out noticia_v2.mp4
