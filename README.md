# Drop Five News (D5N)

**Curadoria diária de notícias via IA** — site, podcast, cards Instagram e distribuição multi-canal.

🌐 **Site:** [d5n-daily.netlify.app](https://d5n-daily.netlify.app/)  
📱 **Instagram:** [@jeanbraga.ai](https://instagram.com/jeanbraga.ai)  
🎧 **Podcast:** Spotify / Telegram (diário, seg-sex)  
📡 **RSS:** `/d5n-feed.xml` | **JSON Feed:** `/feed.json`

---

## O que é

D5N é um boletim diário de notícias curado por IA, publicado automaticamente todo dia útil. O pipeline coleta notícias de 6+ fontes (Yahoo Finance BR, Folha, UOL, etc.), processa via LLM (Claude/GPT), gera um site estático, podcast em áudio (TTS) e cards para Instagram — tudo sem intervenção humana.

### Pilares editoriais

| Pilar | Ícone | Cobertura |
|-------|-------|-----------|
| **Global** | 🌍 | Geopolítica, conflitos, diplomacia |
| **Tech & IA** | 🤖 | Tecnologia, inteligência artificial, startups |
| **Economia & Crypto** | 💰 | Mercado financeiro, BCB, criptomoedas |
| **Brasil** | 🇧🇷 | Política nacional, economia doméstica |

### Formatos de saída

| Formato | Descrição |
|---------|-----------|
| **Site HTML** | Página estática com design premium (Libre Baskerville + DM Sans) |
| **Podcast MP3** | ~5-7 min, vozes alternadas (Thalita/Francisca) |
| **Cards Instagram** | PNG 1080×1080 com foto de fundo + headline |
| **Feed JSON/RSS** | Para apps e agregadores |
| **Arquivo Markdown** | Histórico diário em `/2026/YYYY-MM-DD.md` |

---

## Arquitetura

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│  6+ Fontes   │───▶│  LLM (Claude) │───▶│ gerar_pagina_  │
│  (scraping)  │    │  Curadoria    │    │ d5n.py         │
└─────────────┘    └──────────────┘    └───────┬────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                   ┌────────────┐     ┌──────────────┐     ┌────────────┐
                   │ index.html  │     │  MP3 (TTS)   │     │  Cards PNG │
                   │  (Netlify)  │     │  (Spotify)   │     │ (Instagram)│
                   └────────────┘     └──────────────┘     └────────────┘
```

### Fluxo diário (cron 03:00 BRT)

1. **Coleta** — 6+ fontes via scraping (Yahoo Finance BR, Folha, UOL, etc.)
2. **Curadoria** — LLM seleciona e organiza 18-25 notícias por pilar
3. **Geração** — `gerar_pagina_d5n.py` cria HTML, source.md, feed.json, RSS
4. **Podcast** — TTS via OpenAI/ElevenLabs (vozes Thalita/Francisca alternadas)
5. **Deploy** — Git push → Netlify auto-deploy
6. **Distribuição** — Telegram bot + Instagram cards

---

## Estrutura do repositório

```
d5n-videocast-source/
├── gerar_pagina_d5n.py      # Script principal — gera HTML, feeds, source.md
├── gerar_cards_pipeline.py   # Gera cards PNG para Instagram
├── gerar_cards_instagram_d5n.py  # Cards individuais por notícia
├── deploy_d5n_site.sh        # Script de deploy (legacy)
├── deploy_netlify_direct.py  # Deploy direto via API Netlify (backup)
│
├── index.html                # Site principal (gerado diariamente)
├── feed.json                 # JSON Feed (gerado diariamente)
├── d5n-feed.xml              # RSS Feed (gerado diariamente)
├── source.md                 # Roteiro do podcast (gerado diariamente)
├── episode-counter.json      # Contador persistente de episódios
│
├── 2026/                     # Arquivo histórico (1 .md por dia)
│   ├── 2026-05-24.md
│   ├── 2026-05-25.md
│   └── ...
│
├── audio/                    # Episódios MP3
│   ├── d5n-ep004-2026-05-28.mp3
│   ├── d5n-ep032-2026-06-29.mp3
│   └── ...
│
├── cards-instagram/          # Cards PNG por data
│   └── YYYY-MM-DD/
│       ├── resumo_YYYY-MM-DD.png
│       └── individuais/
│
├── scripts/                  # Scripts auxiliares
│   ├── amanha-conectada/     # Programa "Amanhã Conectada"
│   ├── amanha_conectada_mixer.py
│   ├── d5n-babysitter.py     # Validação automática
│   ├── d5n_marketing.py      # Geração de copy marketing
│   ├── validate_mp3.py       # Validação de arquivos MP3
│   └── reports/              # Relatórios de qualidade
│
├── trilhas/                  # Trilhas sonoras do podcast
├── privacidade.html          # Política de privacidade
├── netlify.toml              # Config Netlify (headers, redirects)
├── og-image.png              # Open Graph image
│
├── .github/workflows/
│   └── update.yml            # GitHub Actions (cron 04:00 UTC)
│
└── .gitignore
```

---

## Como funciona

### Geração diária (local — servidor homelab)

```bash
# Pipeline completo (via cron do Hermes Agent)
python3 gerar_pagina_d5n.py --data $(date +%Y-%m-%d)

# Sem podcast (apenas site)
python3 gerar_pagina_d5n.py --data 2026-07-08 --no-podcast

# Cards Instagram
python3 gerar_cards_pipeline.py --data 2026-07-08
```

### GitHub Actions (backup)

O workflow `.github/workflows/update.yml` roda diariamente às 04:00 UTC como fallback caso o cron local falhe.

### Deploy

- **Primário:** Git push → Netlify auto-deploy (branch `master`)
- **Secundário:** Deploy direto via API Netlify (`deploy_netlify_direct.py`)
- **Domínio:** `d5n-daily.netlify.app` (sem domínio customizado)

---

## Features do site

### Visual (Sprint 2 — Julho 2026)
- **Dark mode premium** — Paleta refinada (azul profundo #0f172a)
- **Cards de notícias** — Bordas coloridas por pilar (hover com elevação)
- **Tech bar** — Dados de mercado em tempo real (USD, BTC, PETR4)
- **Contexto rápido** — 1 frase de contexto por seção
- **Tipografia** — Libre Baskerville (serif) + DM Sans (sans-serif)

### Interatividade (Sprint 3 — Julho 2026)
- **Busca em tempo real** — Filtra notícias por texto
- **Filtros por pilar** — Botões Global / Tech / Economia / Brasil
- **Ticker animado** — Últimas 15 notícias em scroll horizontal
- **Scroll reveal** — Notícias aparecem com animação ao rolar
- **Archive dropdown** — 3 episódios visíveis + "Ver mais"

### Personalidades (Sprint 1 — Julho 2026)
- **Thalita** (Seg/Qua/Sáb) — Tom formal, preciso
- **Francisca** (Ter/Qui/Dom) — Tom casual, envolvente
- **Dual** (Sexta) — Ambos os estilos

---

## Configuração

### Variáveis de ambiente

```bash
D5N_BASE=/root/repositorio/d5n-videocast-source  # Diretório base
```

### Dependências

```bash
# Python 3.11+
# Sem dependências externas — usa apenas stdlib
# Para TTS: openai, elevenlabs (via pipeline Hermes)
# Para cards: Pillow, requests, google-generativeai
```

### Netlify

Configuração em `netlify.toml`:
- **Build:** Nenhum (site estático pré-gerado)
- **Publish:** `/` (raiz do repo)
- **Headers:** Security headers + Content-Type para feeds
- **Redirects:** 404 → index.html

---

## Qualidade e validação

### Babysitter (via Hermes Agent)

Validação automática diária:
- ✅ Arquivo MP3 existe e tem duração > 0
- ✅ HTML tem > 10 notícias
- ✅ Source.md gerado corretamente
- ✅ Feeds (JSON + RSS) válidos
- ✅ 4 pilares presentes

### Auto-avaliação

Scores diários em `autoavaliacao-score.json`:
- Qualidade da curadoria
- Diversidade de fontes
- Cobertura de pilares
- Duração do podcast

---

## Histórico

| Data | Marco |
|------|-------|
| **Mai 2026** | Lançamento — site básico + podcast |
| **Jun 2026** | 32 episódios, cards Instagram, Umami analytics |
| **Jul 2026** | Sprint 1-3: Bug fixes, visual upgrade, busca/filtros, dados de mercado |

Ver [CHANGELOG.md](CHANGELOG.md) para detalhes completos.

---

## Licença

Projeto pessoal de [Jean Braga](https://instagram.com/jeanbraga.ai).  
Código fonte disponível para referência.

---

## Contato

- **Instagram:** [@jeanbraga.ai](https://instagram.com/jeanbraga.ai)
- **GitHub:** [eibragaa](https://github.com/eibragaa)
- **Site:** [d5n-daily.netlify.app](https://d5n-daily.netlify.app)
