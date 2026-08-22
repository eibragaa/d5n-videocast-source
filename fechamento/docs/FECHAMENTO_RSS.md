# Fechamento do Mercado — RSS

Feed canônico: `fechamento/feeds/fechamento.xml`
URL pública: `/fechamento.xml` via redirect `netlify.toml` → `/fechamento/feeds/fechamento.xml`
Áudio: `/audio/fechamento-YYYY-MM-DD.mp3` → `/fechamento/audio/fechamento-...`

## Metadados
- `itunes:image`: `/fechamento-cover.png` → `/fechamento/assets/fechamento-cover.png` (placeholder `manha-conectada-cover.png`, aguardar ilustração do usuário)
- Channel: Fechamento do Mercado — Fechamento diário 17h, Radar Amanhã
- `podcast:guid`: fechamento.d5n-daily.netlify.app

## Troca de capa
1. Substituir `fechamento/assets/fechamento-cover.png`
2. Regenerar feed: `python3 fechamento/scripts/gerar_fechamento_feed.py`
3. Verificar: `curl -I /fechamento.xml` 200, `python3 -c "import ...; feed_has_episode(...)"`
