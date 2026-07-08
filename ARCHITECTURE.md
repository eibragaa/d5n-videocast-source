# Arquitetura do D5N

Este documento descreve a arquitetura técnica do projeto Drop Five News.

---

## 📋 Visão Geral

D5N é um sistema de curadoria automatizada de notícias que opera 24/7 sem intervenção humana. O pipeline coleta, processa e distribui conteúdo em múltiplos formatos.

```
┌─────────────────────────────────────────────────────────────────┐
│                        D5N ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────┘

                    COLETA (Cron 03:00 BRT)
                    ┌──────────────┐
                    │  6+ Fontes   │
                    │  (scraping)  │
                    └──────┬───────┘
                           │
                           ▼
                    PROCESSAMENTO
                    ┌──────────────┐
                    │  LLM (Claude)│
                    │  Curadoria   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
         ┌─────────┐ ┌──────────┐ ┌──────────┐
         │gerar_   │ │  TTS     │ │  Cards   │
         │pagina_  │ │  (voz)   │ │ Pipeline │
         │d5n.py   │ │          │ │          │
         └────┬────┘ └────┬─────┘ └────┬─────┘
              │            │            │
              ▼            ▼            ▼
         ┌─────────┐ ┌──────────┐ ┌──────────┐
         │index    │ │  MP3     │ │  PNG     │
         │.html    │ │  (audio) │ │  (cards) │
         │feed.json│ │          │ │          │
         │source.md│ │          │ │          │
         └────┬────┘ └────┬─────┘ └────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                    DISTRIBUIÇÃO
              ┌────────────────────────┐
              │  Git push → Netlify    │
              │  Telegram Bot          │
              │  Instagram (manual)    │
              │  Spotify (manual)      │
              └────────────────────────┘
```

---

## 🔄 Pipeline Diário

### Fase 1: Coleta (03:00 BRT)

**Script:** Hermes Agent cron job  
**Duração:** ~2 minutos

1. **Yahoo Finance BR** — Notícias de mercado
2. **Folha de S.Paulo** — Política e economia
3. **UOL** — Notícias gerais
4. **Outras fontes** — Tech, economia, global

**Saída:** `drop5news-trends-YYYY-MM-DD.txt`

### Fase 2: Curadoria (03:02 BRT)

**Script:** `gerar_pagina_d5n.py`  
**LLM:** Claude 3.5 Sonnet / GPT-4  
**Duração:** ~3 minutos

1. **Análise** — LLM lê todas as notícias coletadas
2. **Seleção** — Escolhe 18-25 notícias mais relevantes
3. **Organização** — Agrupa por pilar (Global, Tech, Economia, Brasil)
4. **Ranking** — Ordena por impacto dentro de cada pilar

**Saída:** Lista estruturada de notícias com:
- Título
- Pilar
- Fonte
- URL original
- Resumo (opcional)

### Fase 3: Geração (03:05 BRT)

**Script:** `gerar_pagina_d5n.py`  
**Duração:** ~1 minuto

Gera múltiplos arquivos de saída:

#### 3.1 HTML Principal
```
index.html (40-50KB)
├── Header com tech bar (dados de mercado)
├── Hero section (stats do dia)
├── Ticker animado (últimas 15 notícias)
├── Seções por pilar (cards de notícias)
├── Podcast player (se disponível)
├── Archive dropdown (episódios anteriores)
└── Footer (links + créditos)
```

#### 3.2 Roteiro do Podcast
```
source.md (2-3KB)
├── Instruções para TTS
├── Personalidade do dia (Thalita/Francisca)
├── Notícias organizadas por pilar
└── Transições entre blocos
```

#### 3.3 Feeds
```
feed.json (2-3KB) — JSON Feed v1
d5n-feed.xml (1-2KB) — RSS 2.0
```

#### 3.4 Arquivo Histórico
```
2026/YYYY-MM-DD.md (1-2KB) — Markdown da edição
```

### Fase 4: Podcast (03:06 BRT)

**Script:** Pipeline Hermes (TTS + mixer)  
**Duração:** ~2 minutos

1. **TTS** — Gera áudio via OpenAI/ElevenLabs
2. **Mixer v9** — Adiciona vinheta + trilhas
3. **Normalização** — -1.5dBFS master

**Saída:** `audio/d5n-ep{NNN}-YYYY-MM-DD.mp3` (~5-7 min)

### Fase 5: Cards Instagram (03:08 BRT)

**Script:** `gerar_cards_pipeline.py`  
**Duração:** ~3 minutos

1. **Leonardo AI** — Gera imagem de fundo
2. **Pillow** — Renderiza card PNG
3. **Layout** — 1080×1080 com headline + resumo

**Saída:**
```
cards-instagram/YYYY-MM-DD/
├── resumo_YYYY-MM-DD.png (resumo do dia)
└── individuais/
    ├── 01_categoria_YYYY-MM-DD.png
    ├── 02_categoria_YYYY-MM-DD.png
    └── ... (1 card por notícia)
```

### Fase 6: Deploy (03:11 BRT)

**Script:** Git push automático  
**Duração:** ~30 segundos

1. **Git add** — Adiciona arquivos gerados
2. **Git commit** — Mensagem: "📰 Atualização D5N - YYYY-MM-DD"
3. **Git push** — Para branch `master`
4. **Netlify** — Auto-deploy em ~2 minutos

**Fallback:** GitHub Actions (04:00 UTC) se cron local falhar

### Fase 7: Distribuição (03:12 BRT)

**Script:** Telegram bot + manual  
**Duração:** ~1 minuto

1. **Telegram** — Envia MP3 + link do site
2. **Instagram** — Upload manual dos cards
3. **Spotify** — Upload manual do MP3

---

## 🏗️ Componentes Principais

### 1. gerar_pagina_d5n.py (900+ linhas)

**Responsabilidade:** Gerar site HTML + feeds + source.md

**Funções principais:**
```python
load_today_news(date_str)              # Carrega notícias do trends file
load_episode_history()                 # Carrega histórico de episódios
get_last_episode_num()                 # Retorna último número de episódio
get_duration(mp3_path)                 # Calcula duração do MP3
list_episodes()                        # Lista episódios disponíveis
gerar_html(...)                        # Gera HTML completo
gerar_source_md(...)                   # Gera roteiro do podcast
gerar_feeds_json(...)                  # Gera JSON Feed
gerar_feed_rss(...)                    # Gera RSS Feed
```

**Entradas:**
- `drop5news-trends-YYYY-MM-DD.txt` (notícias coletadas)
- `episode-counter.json` (histórico de episódios)
- `audio/*.mp3` (podcasts anteriores)

**Saídas:**
- `index.html` (site principal)
- `feed.json` (JSON Feed)
- `d5n-feed.xml` (RSS Feed)
- `source.md` (roteiro do podcast)
- `2026/YYYY-MM-DD.md` (arquivo histórico)

### 2. gerar_cards_pipeline.py (800+ linhas)

**Responsabilidade:** Gerar cards PNG para Instagram

**Funções principais:**
```python
gerar_imagem_fundo(titulo, categoria)  # Leonardo AI + fallback Bing
renderizar_card(noticia, imagem)        # Pillow rendering
gerar_resumo_ia(titulo)                 # Gemini API
criar_card_individual(noticia)          # Card 1080×1080
criar_card_resumo(noticias)             # Resumo do dia
```

**Dependências:**
- Pillow (rendering)
- requests (APIs)
- google-generativeai (resumos)

### 3. scripts/d5n-babysitter.py

**Responsabilidade:** Validação automática diária

**Checks:**
- ✅ MP3 existe e tem duração > 0
- ✅ HTML tem > 10 notícias
- ✅ Source.md gerado
- ✅ Feeds válidos
- ✅ 4 pilares presentes

**Saída:** `autoavaliacao-score.json`

### 4. scripts/validate_mp3.py

**Responsabilidade:** Validar integridade de arquivos MP3

**Checks:**
- ✅ Arquivo não corrompido
- ✅ Duração > 60 segundos
- ✅ Bitrate >= 128kbps
- ✅ Metadata válido

---

## 📊 Fluxo de Dados

### Arquivos de Entrada

```
drop5news-trends-YYYY-MM-DD.txt
├── Gerado por: Hermes Agent (scraping)
├── Formato: JSON lines
├── Campos: titulo, pilar, fonte, url, resumo
└── Tamanho: ~50-100 notícias

episode-counter.json
├── Gerado por: gerar_pagina_d5n.py
├── Formato: JSON
├── Campos: last_episode, history[]
└── Persistente entre execuções

audio/d5n-ep{NNN}-YYYY-MM-DD.mp3
├── Gerado por: Pipeline TTS Hermes
├── Formato: MP3 128kbps
├── Duração: ~5-7 minutos
└── ~35 arquivos (1 por dia útil)
```

### Arquivos de Saída

```
index.html
├── Gerado por: gerar_pagina_d5n.py
├── Tamanho: ~40-50KB
├── Regenerado: Diariamente
└── Deploy: Netlify (git push)

feed.json
├── Gerado por: gerar_pagina_d5n.py
├── Formato: JSON Feed v1
├── Items: Últimos 30 episódios
└── Deploy: Netlify

source.md
├── Gerado por: gerar_pagina_d5n.py
├── Uso: Roteiro para TTS
├── Regenerado: Diariamente
└── Deploy: Netlify

2026/YYYY-MM-DD.md
├── Gerado por: gerar_pagina_d5n.py
├── Formato: Markdown
├── Conteúdo: Notícias do dia
└── Persistente (arquivo histórico)

cards-instagram/YYYY-MM-DD/*.png
├── Gerado por: gerar_cards_pipeline.py
├── Formato: PNG 1080×1080
├── Quantidade: 1 resumo + N individuais
└── Uso: Instagram (upload manual)
```

---

## 🌐 Infraestrutura

### Hosting

**Netlify** (gratuito)
- Auto-deploy via GitHub
- CDN global
- HTTPS automático
- Headers customizados (netlify.toml)

### Domínio

**d5n-daily.netlify.app** (sem domínio customizado)

### Backup

**GitHub Actions** (04:00 UTC)
- Fallback se cron local falhar
- Garante publicação diária

### Analytics

**Umami** (self-hosted, GDPR-friendly)
- Sem cookies
- Sem tracking invasivo
- Métricas básicas (pageviews, referrers)

---

## 🔧 Dependências

### Python 3.11+

**stdlib apenas** (gerar_pagina_d5n.py):
- `os`, `sys`, `re`, `json`, `argparse`
- `datetime`, `timedelta`
- `xml.sax.saxutils`

**Para cards** (gerar_cards_pipeline.py):
- `Pillow` (rendering)
- `requests` (APIs)
- `google-generativeai` (resumos)

### APIs Externas

**Curadoria:**
- Claude 3.5 Sonnet (Anthropic)
- GPT-4 (OpenAI) — fallback

**TTS:**
- OpenAI TTS (vozes Thalita/Francisca)
- ElevenLabs — alternativa

**Imagens de fundo:**
- Leonardo AI (primário)
- Bing Images (fallback)

**Dados de mercado:**
- ExchangeRate API (USD/BRL)
- CoinGecko API (BTC)
- Brapi API (PETR4)

---

## 🎯 Decisões de Design

### Por que estático?

- **Velocidade** — HTML pré-gerado carrega instantaneamente
- **Custo** — Netlify gratuito (sem servidor)
- **Confiabilidade** — Sem downtime de servidor
- **Simplicidade** — Sem banco de dados, sem backend

### Por que cron local + GitHub Actions?

- **Redundância** — Se um falha, o outro garante publicação
- **Controle** — Cron local tem acesso a APIs e arquivos locais
- **Backup** — GitHub Actions como fallback

### Por que não usar CMS?

- **Automação** — Pipeline 100% automatizado
- **Customização** — Controle total do HTML/CSS
- **Performance** — Sem overhead de CMS
- **Custo** — Zero (sem licenças)

### Por que múltiplos formatos?

- **Acessibilidade** — Site para leitura, MP3 para áudio, cards para visual
- **Distribuição** — Múltiplos canais (web, Telegram, Instagram, Spotify)
- **SEO** — Múltiplos pontos de entrada

---

## 📈 Escalabilidade

### Limites Atuais

- **Notícias/dia:** 18-25 (curadoria LLM)
- **Episódios:** ~250/ano (dias úteis)
- **Storage:** ~500MB/ano (MP3 + HTML + cards)
- **Custo:** ~$0.50/dia (LLM + TTS)

### Gargalos

1. **LLM API** — Latência ~3 min para curadoria
2. **TTS API** — Latência ~2 min para gerar MP3
3. **Leonardo AI** — Latência ~3 min para imagens
4. **Netlify deploy** — ~2 min para publicar

### Otimizações Possíveis

- **Paralelização** — Gerar cards enquanto TTS roda
- **Cache** — Reutilizar imagens de fundo similares
- **CDN** — Netlify já faz (sem ação necessária)

---

## 🔒 Segurança

### Dados Sensíveis

- **API keys** — Armazenadas em variáveis de ambiente (não no código)
- **Credenciais** — `.env` no `.gitignore`
- **Deploy scripts** — `deploy_netlify_direct.sh` no `.gitignore`

### Headers HTTP

```toml
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

### Validação

- **Babysitter** — Valida arquivos antes do deploy
- **Validate MP3** — Checa integridade de áudio
- **Lint** — Ruff + mypy para Python

---

## 🚀 Deploy

### Automático (primário)

```bash
# Cron Hermes Agent (03:00 BRT)
python3 gerar_pagina_d5n.py --data $(date +%Y-%m-%d)
git add .
git commit -m "📰 Atualização D5N - $(date +%Y-%m-%d)"
git push origin master

# Netlify detecta push e faz deploy (~2 min)
```

### Manual (emergência)

```bash
# Deploy direto via API Netlify
python3 deploy_netlify_direct.py

# Ou via Netlify CLI
netlify deploy --prod
```

### Rollback

```bash
# Reverter para commit anterior
git revert HEAD
git push origin master

# Netlify faz deploy automaticamente
```

---

## 📊 Monitoramento

### Métricas

**Umami Analytics:**
- Pageviews
- Unique visitors
- Referrers
- Bounce rate

**Auto-avaliação:**
- Qualidade da curadoria (1-10)
- Diversidade de fontes (1-10)
- Cobertura de pilares (1-10)
- Duração do podcast (segundos)

**Babysitter:**
- Validações diárias (pass/fail)
- Issues detectadas
- Score geral

### Alertas

**Telegram bot:**
- Notifica se pipeline falhar
- Envia MP3 + link do site diariamente

**GitHub Actions:**
- Email se workflow falhar
- Logs detalhados no GitHub

---

## 🎓 Aprendizados

### O que funcionou bem

1. **Pipeline automatizado** — Zero intervenção humana
2. **Netlify gratuito** — Confiável e rápido
3. **Git como CMS** — Versionamento automático
4. **Múltiplos formatos** — Alcance maior
5. **Backup via GitHub Actions** — Redundância

### O que poderia melhorar

1. **Monitoramento** — Adicionar mais métricas
2. **Testes** — Cobertura de testes automatizados
3. **API pública** — Para desenvolvedores consumirem
4. **Transcrições** — Automáticas via Whisper
5. **Newsletter** — Captura de leads

---

## 📚 Recursos

### Documentação

- [README.md](README.md) — Visão geral do projeto
- [CHANGELOG.md](CHANGELOG.md) — Histórico de mudanças
- [CONTRIBUTING.md](CONTRIBUTING.md) — Como contribuir
- [CARDS_INSTAGRAM.md](CARDS_INSTAGRAM.md) — Pipeline de cards

### Código

- [gerar_pagina_d5n.py](gerar_pagina_d5n.py) — Script principal
- [gerar_cards_pipeline.py](gerar_cards_pipeline.py) — Cards Instagram
- [netlify.toml](netlify.toml) — Config Netlify
- [.github/workflows/update.yml](.github/workflows/update.yml) — GitHub Actions

### Links

- **Site:** https://d5n-daily.netlify.app
- **GitHub:** https://github.com/eibragaa/d5n-videocast-source
- **Instagram:** https://instagram.com/jeanbraga.ai

---

**Última atualização:** 08 Jul 2026  
**Mantido por:** [Jean Braga](https://instagram.com/jeanbraga.ai)
