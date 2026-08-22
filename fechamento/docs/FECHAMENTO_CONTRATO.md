# Fechamento do Mercado — Contrato Editorial e Técnico

Programa diário seg-sex 17:30 BRT, isolado em `fechamento/` no mesmo repo D5N (1 Netlify).
Branch: `test/fechamento-mercado` — não mergear em master sem validar.

## Isolamento
- `fechamento/` não toca `d5n-fecho-card.sh`, `enviar_fechamento.py`, `d5n-destaque-semanal.sh`.
- Cards 17h e altas/quedas sexta permanecem intocados.

## Formato (modelo Sextouro + D5N/MC)
- Duração 8-10min, 1100-1500 palavras, 6 blocos numerados
- Cold open 3-4 manchetes tiro (números fortes, sem contexto) → Vinheta → Intro "Boa noite! Eu sou Antonio — Fechamento do Mercado — data"
- Blocos: Ibovespa → Dólar/Juros (Focus BCB) → Destaque do dia → Gringo/Fluxo (Nasdaq) → Setor em foco → Radar Amanhã
- Cada bloco: gancho → detalhe/contexto → consequência "o que muda pra você" + punchline opinativa, títulos provocativos
- Interação opcional sem header
- Outro: síntese + CTA RSS Fechamento + "Bom dia!" + bordão

## Técnico
- Provider exclusivo: `custom:deepseek` model `deepseek-v4-flash`, thinking disabled, max_tokens 12000, temp 0.35
- Voz: `pt-BR-AntonioNeural` (-2% rate, -2Hz pitch)
- Mixer: sidechaincompress ducking, lead 3s, LUFS -16, TP -1.5
- Feed separado: `fechamento/feeds/fechamento.xml` (Apple/Spotify), redirects netlify.toml
- Hub portal: expandir `gerar_pagina_d5n.py` para 3 players (tabs D5N|Manhã|Fechamento)

## Gates
- Palavras 1100-1500, duração 480-600s, LUFS -17.5 a -14.5, TP < -1.0
- Marcadores obrigatórios: "Fechamento do Mercado" + "Drop Five News" + CTA + "Bom dia!"
- Sem URLs/emojis no texto falado, sem clichês FORBIDDEN
