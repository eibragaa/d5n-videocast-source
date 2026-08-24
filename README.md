# Drop Five News (D5N)

**Curadoria diária de notícias via IA — 3 programas sonoros, site premium e distribuição multi-canal.**

> 🎙️ **D5N 05h** (podcast principal) · ☀️ **Manhã Conectada 11h** · 📈 **Fechamento do Mercado 17h**
> Produção 100% automatizada via Hermes Agent no homelab; publicação contínua no Netlify.

[![Site](https://img.shields.io/badge/site-d5n--daily.netlify.app-0ea5e9)](https://d5n-daily.netlify.app/)
[![RSS D5N](https://img.shields.io/badge/RSS-D5N-f59e0b)](https://d5n-daily.netlify.app/podcast.xml)
[![RSS MC](https://img.shields.io/badge/RSS-Manh%C3%A3%20Conectada-f59e0b)](https://d5n-daily.netlify.app/manha-conectada.xml)
[![RSS FM](https://img.shields.io/badge/RSS-Fechamento%2017h-f59e0b)](https://d5n-daily.netlify.app/fechamento.xml)

🌐 **Site:** [d5n-daily.netlify.app](https://d5n-daily.netlify.app/) · 📱 **Instagram:** [@jeanbraga.ai](https://instagram.com/jeanbraga.ai)

---

## Os três programas

| Programa | Horário (BR) | RSS | Diretório | Voz |
|---|---|---|---|---|
| **Drop Five News** (principal) | Diário · 05h | `/podcast.xml` | raiz + `audio/` | Thalita / Francisca (+ Antonio nos headers) |
| **Manhã Conectada** | Seg–Sex · 11h | `/manha-conectada.xml` | `manha-conectada/` | Antonio |
| **Fechamento do Mercado** | Seg–Sex · 17h | `/fechamento.xml` | `fechamento/` | Antonio |

Todos os episódios ficam disponíveis também no player do site (grade única 05h→11h→17h) e nos apps de podcast via RSS próprio.

---

## O que é

O D5N é um boletim diário de notícias curado por IA. O pipeline coleta notícias de 6+ fontes (Google News, G1, Cointelegraph, Investing.com, VentureBeat, Yahoo Finance), processa via LLM com gates editoriais rigorosos, gera um site estático premium, podcasts em áudio (edge-tts + mixagem própria) e cards para Instagram.

### Pilares editoriais

| Pilar | Cobertura |
|-------|-----------|
| 🌍 **Global** | Geopolítica, conflitos, diplomacia |
| 🤖 **Tech & IA** | Tecnologia, inteligência artificial |
| 💰 **Economia & Crypto** | Mercado financeiro, BCB, criptomoedas |
| 🇧🇷 **Brasil** | Política nacional, economia doméstica |

---

## Arquitetura (visão geral)

```
Fontes (scraping) ──▶ Curadoria LLM ──▶ gerar_pagina_d5n.py
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
              index.html              Podcasts MP3             Cards PNG
            (site + feeds)         (3 programas/dia)          (Instagram)
                    │                       │
                    └──── git push ────▶ Netlify (auto-deploy)
```

### Cadeia de LLM para roteiros (MC/FM)

1. **DeepSeek direto** (`deepseek-v4-flash`, thinking disabled) — primário
2. opencode-go — fallback legado
3. **Groq `gpt-oss-120b`** — camada gratuita (`GROQ_API_KEY`)
4. Hermes CLI — último recurso

Chaves em `/root/.hermes/.env`: `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`.

### Publicação

Cada programa publica via script dedicado que regenera o site, atualiza o feed, commita apenas artefatos canônicos e faz push:

```bash
manha-conectada/scripts/publish-manha-conectada-site.sh AUDIO SOURCE MANIFEST
fechamento/scripts/publish-fechamento-site.sh        AUDIO SOURCE MANIFEST
```

A publicação é **imediata após o pipeline** — o RSS sai assim que o áudio fica pronto (sem esperar o horário de exibição).

---

## Pipeline de áudio D5N (mixer v10)

O mixer vigente é o **v10** (`scripts/drop5news-mixer-v10.py`) — identidade sonora premium do contrato D5N v3, com 12 seções canônicas e duração obrigatória de **8–12 min**:

```
coldopen → intro → mundo → brasil → tecnologia → economia →
interacao → ofertas → frase → recomendacoes → historia → outro
```

- CTA integrado ao `outro` (não há seção `cta` separada)
- Trilhas próprias em `assets/audio/d5n/` (14 trilhas), ducking sidechain e lead musical
- Mínimos garantidos por gate: `MIN_SECONDS=480`, `MIN_WORDS=1100`
- ⚠️ O `drop5news-mixer-v9.py` permanece no repo apenas como referência histórica — **não usar**

### Sistema de vozes (edge-tts local)

| Regra editorial | Voz |
|---|---|
| Segunda, quarta e sábado | Thalita — `pt-BR-ThalitaMultilingualNeural` |
| Terça e quinta | Francisca — `pt-BR-FranciscaNeural` |
| Sexta-feira | Francisca + Thalita alternadas por bloco |
| Headers de seção (D5N) / apresentação (MC e FM) | Antonio — `pt-BR-AntonioNeural` |

A data editorial (`D5N_EDITORIAL_DATE` ou fuso `America/Sao_Paulo`) determina o plano de vozes — nunca o dia de execução de um reprocessamento histórico.

---

## Estrutura do repositório

```
d5n-videocast-source/
├── gerar_pagina_d5n.py           # Gera site, feeds e players dos 3 programas
├── scripts/
│   ├── drop5news-mixer-v10.py    # Mixer vigente (contrato v3, 12 seções)
│   ├── drop5news-mixer-v9.py     # Legado (referência histórica)
│   ├── d5n-babysitter.py         # Validação automática diária
│   ├── d5n-podcast-quality-gate.py   # Gate editorial (roteiro, vozes, mix)
│   ├── d5n_daily_release_gate.py     # Gate de release antes da publicação
│   ├── d5n_chapter_manifest.py       # Capítulos para a barra do player
│   ├── validate_mp3.py               # Validação de MP3
│   └── ...
├── audio/                        # Episódios D5N: d5n-ep{NNN}-{DATA}.mp3
├── chapters/                     # Capítulos por episódio (JSON)
├── manifests/                    # Manifests de produção
├── podcast-scripts/              # Histórico de roteiros gerados (JSON)
├── cards-instagram/              # Cards PNG por data
├── 2026/                         # Arquivo diário (.md por dia)
│
├── manha-conectada/              # ☀️ Manhã Conectada (projeto isolado)
│   ├── scripts/                  # pipeline, feed, publish-site
│   ├── assets/ audio/ manifests/ roteiros/ feeds/ docs/
│   └── cron-prompt.txt
├── fechamento/                   # 📈 Fechamento do Mercado (projeto isolado)
│   ├── scripts/                  # pipeline, mixer sidechain, publish-site
│   ├── assets/ audio/ manifests/ roteiros/ feeds/ docs/
│   └── cron-prompt.txt
│
├── index.html / feed.json / podcast.xml / d5n-feed.xml   # Gerados diariamente
├── netlify.toml                  # Headers + redirects (URLs públicas preservadas)
├── docs/
│   ├── PADRAO_EDITORIAL_AUDIO.md # Padrão editorial vigente
│   ├── TRILHAS_D5N_PREMIUM.md    # Identidade sonora v3
│   ├── GATEDURANCE.md            # Sistema gatedurance
│   └── SPRINTS_CORRECAO.md       # Histórico de correções
├── ARCHITECTURE.md · CHANGELOG.md · CONTRIBUTING.md · README.md
└── .github/workflows/update.yml  # Backup de deploy via GitHub Actions
```

---

## Cronograma de produção (America/Sao_Paulo)

| Horário BR | Programa | Cron Hermes | Fluxo |
|---|---|---|---|
| 03:00 (host) | D5N | `d5n-podcast-diario` | Curadoria → roteiro → gates → mix v10 → publicação |
| 09:00 (host) | Manhã Conectada | `manha-conectada-diario` | pipeline MC → publish imediato |
| 16:30 (host) | Fechamento | `fechamento-diario` | pipeline FM → publish imediato |

Domingo é reservado à manutenção — nenhum cron gera episódio.

---

## Qualidade e validação

Gates executados antes de qualquer publicação:

- ✅ `d5n-pre-gen-gate.py` — data/weekday corretos no roteiro (preventivo)
- ✅ `d5n-mensagem-validate.py` — CTA/Mensagem sem clichês (blocklist)
- ✅ `d5n-podcast-quality-gate.py` — MP3, vozes, loudness e padrão editorial
- ✅ `d5n_daily_release_gate.py` — release diária fora do padrão bloqueia publicação
- ✅ `d5n-verify-site.py` — site + 3 feeds respondendo 200 antes do push
- ✅ Babysitter diário — integridade de MP3, contador, pilares e player

---

## Deploy

- **Primário:** `git push` → Netlify auto-deploy (branch `master`, ~2 min)
- **Backup:** GitHub Actions (04:00 UTC) se o cron local falhar
- **Headers/redirects:** `netlify.toml` — URLs públicas da MC/FM preservadas por rewrite

---

## Configuração

```bash
# Requisitos: Python 3.11+, edge-tts, pydub, ffmpeg
D5N_BASE=/root/repositorio/d5n-videocast-source   # diretório base

# Site (apenas stdlib)
python3 gerar_pagina_d5n.py --data $(date +%Y-%m-%d)

# Somente regenerar HTML/feeds sem tocar em fontes
python3 gerar_pagina_d5n.py --site-only
```

---

## Histórico

| Data | Marco |
|------|-------|
| Mai 2026 | Lançamento — site básico + podcast |
| Jun 2026 | 32 episódios, cards Instagram, analytics |
| Jul 2026 | Sprints 1–3: bug fixes, visual upgrade, busca/filtros |
| Ago 2026 | Mixer v10 (contrato v3) · Manhã Conectada isolada · Fechamento do Mercado · grade 05h→11h→17h |
| Ago 2026 | Groq `gpt-oss-120b` como fallback gratuito de roteiro (MC/FM) · publicação imediata via RSS |

Ver [CHANGELOG.md](CHANGELOG.md) e [ARCHITECTURE.md](ARCHITECTURE.md) para detalhes completos.

---

## Licença e contato

Projeto pessoal de **Jean Braga** — código disponível para referência.

- 📱 Instagram: [@jeanbraga.ai](https://instagram.com/jeanbraga.ai)
- 🌐 Site: [d5n-daily.netlify.app](https://d5n-daily.netlify.app/)
