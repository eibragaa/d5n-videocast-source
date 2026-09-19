#!/usr/bin/env bash
# gerar_mapa.sh — Atualiza mapa.md escaneando automaticamente as pastas do repositório
# Use: ./gerar_mapa.sh [--output mapa.md]

set -euo pipefail

REPO_DIR="/root/repositorio/d5n-videocast-source"
OUTPUT="${1:-/root/repositorio/d5n-videocast-source/mapa.md}"

# Obter lista de diretórios e arquivos importantes
echo "# Mapa do Repositório D5N" > "$OUTPUT"
echo "**Atualizado automaticamente:** $(date '+%Y-%m-%d %H:%M')" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "## Pastas" >> "$OUTPUT"
echo "" >> "$OUTPUT"

# Listar diretórios não ocultos no root
for dir in "$REPO_DIR"/*/; do
    if [ -d "$dir" ]; then
        dirname=$(basename "$dir")
        if [[ "$dirname" != .* ]]; then
            echo "- **$dirname**: $(ls "$dir" 2>/dev/null | wc -l) arquivos" >> "$OUTPUT"
        fi
    fi
done

echo "" >> "$OUTPUT"
echo "## Scripts" >> "$OUTPUT"
echo "" >> "$OUTPUT"

for file in "$REPO_DIR"/scripts/*.sh "$REPO_DIR"/scripts/*.py; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        lines=$(wc -l < "$file")
        echo "- **$filename**: $lines linhas" >> "$OUTPUT"
    fi
done

echo "" >> "$OUTPUT"
echo "*Gerado automaticamente por gerar_mapa.sh*" >> "$OUTPUT"

echo "✔ Mapa gerado: $OUTPUT"
