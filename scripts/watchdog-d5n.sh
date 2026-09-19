#!/usr/bin/env bash
# watchdog-d5n.sh — Watchdog para o pipeline diário D5N
# Insight 10 (Automação de auditoria) do vídeo Bruno Okamoto
# Verifica se o d5n-podcast-diario executou hoje. Se não, alerta e tenta resolver.

set -euo pipefail

STATE_DIR="/root/.hermes/state/d5n"
MANIFESTS_DIR="/root/repositorio/d5n-videocast-source/manifests/d5n"
FALHAS_FILE="$STATE_DIR/falhas.json"
DATA=$(date +%Y-%m-%d)
HOJE="$DATA"
ALERTA_TELEGRAM="${ALERTA_TELEGRAM:-telegram:-1004312849084}"

mkdir -p "$STATE_DIR"

# 1. Verificar se há manifests para hoje
if [ -d "$MANIFESTS_DIR/$HOJE" ]; then
  manifest_count=$(find "$MANIFESTS_DIR/$HOJE" -type f | wc -l)
  if [ "$manifest_count" -ge 10 ]; then
    echo "✅ D5N: manifests para hoje encontrados ($manifest_count arquivos)"
    # Atualizar falhas.json — resetar contador se houver manifests
    python3 -c "
import json, os
from datetime import datetime
falhas_file = '$FALHA_FILE'
data = {'falhas': [], 'ultimo_aviso': None}
if os.path.exists(falhas_file):
    try:
        with open(falhas_file) as f:
            data = json.load(f)
    except:
        pass
# Remove aviso se hoje tem manifests
data['falhas'] = [f for f in data.get('falhas',[]) if f.get('data') != '$HOJE']
if data['falhas']:
    data['ultimo_aviso'] = None
with open(falhas_file,'w') as f:
    json.dump(data, f, indent=2)
print('Falhas de hoje limpas do registry')
" 2>/dev/null || true
    exit 0
  fi
fi

# 2. Se não há manifests, tentar gerar
echo "⚠️ D5N: sem manifests para hoje ($HOJE). Tentando gerar..."

# Verificar se existe o script de geração de manifests
GERADOR="/root/repositorio/d5n-videocast-source/scripts/gerar_manifests.py"
if [ -f "$GERADOR" ]; then
  echo "Executando gerador de manifests..."
  if python3 "$GERADOR" --data "$HOJE" 2>&1; then
    echo "✅ Manifests gerados com sucesso"
    exit 0
  else
    echo "❌ Falha ao gerar manifests"
  fi
else
  echo "⚠️ Script de geração de manifests não encontrado: $GERADOR"
fi

# 3. Registrar falha
python3 -c "
import json, os
from datetime import datetime
falhas_file = '$FALHA_FILE'
data = {'falhas': [], 'ultimo_aviso': None}
if os.path.exists(falhas_file):
    try:
        with open(falhas_file) as f:
            data = json.load(f)
    except:
        pass
data['falhas'].append({
    'data': '$HOJE',
    'tipo': 'sem_manifests',
    'acao': 'nenhuma',
    'timestamp': datetime.now().isoformat()
})
# Mantém apenas últimas 30 falhas
data['falhas'] = data['falhas'][-30:]
with open(falhas_file,'w') as f:
    json.dump(data, f, indent=2)
print('Falha registrada')
" 2>/dev/null || true

# 4. Alertar (se configurado)
if [ -n "$ALERTA_TELEGRAM" ] && command -v curl >/dev/null 2>&1; then
  MSG="⚠️ D5N: sem manifests para $HOJE. Pipeline diário não poderá rodar. Verificar /root/.hermes/state/d5n/falhas.json"
  # Nota: isso exigiria um bot token configurado — verificar se disponível
  echo "Alerta via Telegram configurado para: $ALERTA_TELEGRAM"
  echo "Mensagem: $MSG"
fi

echo "❌ D5N: falha no pipeline diário detectada. Ver logs."
exit 1
