# Changelog

Todas as mudanças notáveis do projeto D5N serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/), e este projeto adere ao [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Changed
- **Episódios de fim de semana não consomem mais números de sequência** — `deploy_d5n_site.sh` detecta sáb/dom e salva áudio como `d5n-weekend-{DATE}.mp3` sem atualizar `last_episode` no contador. `find_latest_podcast()` pula entradas de fds no histórico para manter o player com sequência limpa.
- **README, CHANGELOG, ARCHITECTURE** — Documentação atualizada com novo comportamento de fim de semana.

### Planned
- Newsletter com captura de email (ConvertKit/Mailchimp)
- Transcrições automáticas via Whisper API
- Player de vídeo com slides (Remotion + áudio)
- Paywall soft (3 notícias grátis, resto requer cadastro)
- API pública para desenvolvedores
- Expansão para 6 pilares (+Esportes, +Cultura)

---

## [2.0.0] - 2026-07-08

### 🚀 Sprint 1-3: Major Upgrade

#### Added (Sprint 3)
- **Busca em tempo real** — Campo de busca filtra notícias por texto instantaneamente
- **Filtros por pilar** — Botões Global / Tech / Economia / Brasil para filtrar conteúdo
- **Dados de mercado em tempo real** — Tech bar com USD/BRL, BTC, PETR4 via APIs públicas
- **Atualização automática** — Dados de mercado atualizam a cada 5 minutos

#### Changed (Sprint 2)
- **Visual upgrade completo** — Nova paleta de cores (dark mode refinado #0f172a)
- **Cards de notícias** — Bordas coloridas por pilar com hover elevation
- **Tech bar no header** — IBOV, USD, BTC, PETR4 sempre visíveis
- **Contexto rápido** — 1 frase de contexto por seção
- **Tipografia refinada** — Libre Baskerville (serif) + DM Sans (sans-serif)

#### Fixed (Sprint 1)
- **Pilares mostra 4 em vez de 1** — Corrigido bug que exibia apenas 1 pilar
- **Duração do podcast** — Cache persistente para duração correta
- **Feed JSON** — Agora inclui últimos 30 episódios (não apenas o atual)
- **Personalidade v1** — Personas Thalita/Francisca implementadas

### Technical Details
- Commit: `111eef8` (Fix: Episódios + dados de mercado em tempo real)
- Commit: `2408510` (Sprint 1-3: Foundation fixes + visual upgrade + search/filters)
- JavaScript adicionado para interatividade (busca, filtros, market data)
- CSS reestruturado com variáveis CSS para fácil customização
- APIs integradas: ExchangeRate, CoinGecko, Brapi

---

## [1.0.0] - 2026-06-29

### 🎉 Lançamento Oficial

#### Added
- **Pipeline automático** — Cron diário 03:00 BRT via Hermes Agent
- **Coleta de 6+ fontes** — Yahoo Finance BR, Folha, UOL, etc.
- **Curadoria via LLM** — Claude/GPT seleciona 18-25 notícias
- **Site estático** — HTML premium com design editorial
- **Podcast diário** — MP3 ~5-7 min via TTS (OpenAI/ElevenLabs)
- **Cards Instagram** — PNG 1080×1080 com foto de fundo + headline
- **Feeds** — JSON Feed + RSS para agregadores
- **Arquivo histórico** — 1 arquivo .md por dia em `/2026/`
- **Contador de episódios** — `episode-counter.json` persistente
- **Deploy automático** — Git push → Netlify auto-deploy
- **GitHub Actions** — Workflow backup às 04:00 UTC
- **Umami Analytics** — Tracking GDPR-friendly (sem cookies)
- **Archive dropdown** — 3 episódios visíveis + "Ver mais"
- **Ticker animado** — Últimas 15 notícias em scroll horizontal
- **Scroll reveal** — Animações ao rolar a página

#### Infrastructure
- **Netlify** — Hosting gratuito com auto-deploy
- **Domínio:** `d5n-daily.netlify.app`
- **Branch:** `master` (produção)
- **Backup:** GitHub Actions como fallback do cron local

### Episodes
- **32 episódios** publicados (Ep #001 a #032)
- **25 episódios** com áudio disponível
- **7 episódios** placeholder (áudio perdido)

---

## [0.5.0] - 2026-06-20

### Beta Testing

#### Added
- **Cards Instagram pipeline** — `gerar_cards_pipeline.py`
- **Leonardo AI** — Geração de imagens de fundo via IA
- **Bing Images fallback** — Quando IA falha
- **Validação automática** — `d5n-babysitter.py`
- **Trilhas sonoras** — Background music para podcast
- **Mixer v9** — Áudio profissional (-28dB BG, crossfade 1.5s)

#### Changed
- **Mixer de áudio** — Upgrade para versão 9 com qualidade profissional
- **Vinheta** — "Começa agora Drop Five News" (6.5s)
- **Trilhas por pilar** — intro_bg, trilha1/2, tech_bg, economia_bg, etc.

---

## [0.3.0] - 2026-06-10

### Early Development

#### Added
- **Primeiros episódios** — Ep #004 a #015
- **Estrutura básica** — `gerar_pagina_d5n.py` inicial
- **Source.md** — Roteiro do podcast
- **Feeds básicos** — JSON Feed + RSS
- **Audio directory** — `/audio/` para MP3s

#### Fixed
- **Caminhos hardcoded** — Corrigido para funcionar em CI/CD
- **Encoding** — UTF-8 em todos os arquivos

---

## [0.1.0] - 2026-05-24

### 🌱 Início do Projeto

#### Added
- **Primeiro episódio** — Ep #001 (24 Mai 2026)
- **Script inicial** — `gerar_pagina_d5n.py` v0.1
- **Netlify setup** — Config básica de deploy
- **README básico** — Documentação inicial

---

## Métricas do Projeto

### Conteúdo
- **37 dias** de publicação contínua
- **32 episódios** de podcast
- **700+ notícias** curadas
- **4 pilares** editoriais

### Qualidade
- **Score médio:** 8.5/10 (auto-avaliação)
- **Uptime:** 99%+ (Netlify + GitHub Actions backup)
- **Custo operacional:** ~$0.50/dia (LLM + TTS)

### Alcance
- **Instagram:** @jeanbraga.ai
- **Telegram:** Canal de distribuição
- **Spotify:** Podcast diário
- **Web:** d5n-daily.netlify.app

---

## Próximos Passos

### Curto Prazo (1-2 semanas)
1. ✅ ~~Sprint 1-3: Bug fixes + visual upgrade + search/filters~~ (COMPLETO)
2. Implementar newsletter com captura de email
3. Adicionar transcrições automáticas (Whisper API)
4. Criar player de vídeo com slides (Remotion + áudio)

### Médio Prazo (1-2 meses)
5. Paywall soft (3 notícias grátis, resto requer cadastro)
6. API pública para desenvolvedores (R$0.01/request)
7. Expandir para 6 pilares (+Esportes, +Cultura)

### Longo Prazo (3-6 meses)
8. App mobile (PWA)
9. Parcerias com brokers para monetização
10. Internacionalização (inglês/espanhol)

---

## Agradecimentos

- **Nous Research** — Hermes Agent (automação completa)
- **Anthropic** — Claude (curadoria de notícias)
- **OpenAI** — TTS (vozes do podcast)
- **Netlify** — Hosting gratuito e confiável
- **Umami** — Analytics GDPR-friendly

---

**Mantido por:** [Jean Braga](https://instagram.com/jeanbraga.ai)  \n**Última atualização:** 13 Jul 2026
