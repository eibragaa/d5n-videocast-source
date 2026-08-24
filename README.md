# Drop Five News (D5N)

**Curadoria diária de notícias via IA** — site, podcast, cards Instagram e distribuição multi-canal.

📘 **Padrão vigente:** [docs/PADRAO_EDITORIAL_AUDIO.md](docs/PADRAO_EDITORIAL_AUDIO.md)

🌐 **Site:** [d5n-daily.netlify.app](https://d5n-daily.netlify.app/)
📱 **Instagram:** [@jeanbraga.ai](https://instagram.com/jeanbraga.ai)
🎧 **Podcast:** Spotify / Discord (segunda a sábado; domingo reservado para manutenção)
📡 **RSS:** `/d5n-feed.xml` · `/manha-conectada.xml` · `/fechamento.xml` (Fechamento 17h) | **JSON Feed:** `/feed.json`

---

## Estado Atual (2026-08-22 — produção `master`)
- **Master** `f61ed88` live em https://d5n-daily.netlify.app — `d5n-daily` `cc6d8958` `master` production
- **Cron** `fechamento-diario` `30 16 * * 1-5` (host = 17h BRT seg-sex) + `d5n-fechamento-mercado` 17h card intacto + `manha-conectada` 11h
- **Feeds:** `/2026-08-22` epis, `/d5n-feed.xml` + `/manha-conectada.xml` + `/fechamento.xml` (`fechamento-cover.png` 1400)
- **Custo:** DeepSeek v4-flash `thinking disabled` — `f61ed88` 496s 1335w LUFS -16.98 — `compression` `nvidia nemotron` 401 corrigido
- **Cadeia de roteiro (MC/FM):** DeepSeek direto → opencode-go → **Groq `gpt-oss-120b`** (fallback gratuito) → Hermes CLI. Chaves em `/root/.hermes/.env` (`DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`)
- **Site AAA:** `d5n-program 05h` grafite `0.10` + `MC 11h` âmbar `0.14` + `FM 17h` petróleo `0.14`/`17`, `51 chapter-segment`, `4 covers`, stack `5h→11h→17h`

---

## O que é

D5N é um boletim diário de notícias curado por IA, publicado automaticamente todo dia útil. O pipeline coleta notícias de 6+ fontes (Google News, G1, Cointelegraph, Investing.com, VentureBeat, Yahoo Finance), processa via LLM, gera um site estático premium, podcast em áudio (TTS edge-tts) e cards para Instagram — tudo automatizado via Hermes Agent.

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
| **Hub 3 programas** | D5N 05h + Manhã 11h + Fechamento 17h — mesma grade 14px, covers opacas, capítulos na barra |
| **Podcast MP3** | **8–12 min** (sempre ≥8 min), 12 seções premium (coldopen, intro, mundo, brasil, tecnologia, economia, interacao, ofertas, frase, recomendacoes, historia, outro). Apresentação alternada entre Thalita e Francisca; sexta-feira usa ambas; headers com Antonio. Trilhas próprias do D5N + ducking. Segunda a sábado: `d5n-ep{NNN}-{DATE}.mp3`; domingo não há episódio. |
| **Cards Instagram** | PNG 1080×1080 com foto de fundo + headline |
| **Feed JSON/RSS** | Para apps e agregadores |
| **Arquivo Markdown** | Histórico diário em `/2026/YYYY-MM-DD.md` |
| **Manhã Conectada** | Briefing matinal (seg-sex, 11h BR) em `manha-conectada/` — pipeline, mixer e assets próprios, voz Antonio, ducking sidechain. |

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
                   │  (Netlify)  │     │  (Telegram)  │     │ (Instagram)│
                   └────────────┘     └──────────────┘     └────────────┘
```

### Pipeline de áudio (detalhado)

O pipeline de áudio é a parte mais crítica do D5N. Funciona em 5 etapas:

```
gerar_pagina_d5n.py::gerar_source_md()
    │
    ▼
source.md (roteiro com 13 seções)
    │
    ├──▶ /tmp/d5n_audio/source.md (staging)
    │
    ▼
d5n-inject-date.py + d5n-date-context.py
    │  (injeta data correta: "Hoje é [dia], [data]")
    │
    ▼
gerar-secoes-v2.py
    │  (divide source.md em 13 arquivos .txt)
    │
    ▼
drop5news-mixer-v9.py
    │  (TTS via edge-tts + mixagem com trilhas)
    │
    ▼
d5n_mixado_v9.mp3 (áudio final ~6 min)
```

### As 13 seções do mixer v9

Os headers usam Antonio. O conteúdo usa a **apresentadora definida pela data editorial**; na sexta-feira, Francisca e Thalita alternam naturalmente a cada bloco disponível. Seções opcionais ausentes não quebram a alternância.

| # | Seção | Trilha | Origem |
|:-:|-------|--------|:---------:|
| 1 | intro | intro_bg | Mixer (lê intro.txt) |
| 2 | mundo | trilha1 | Agente (mundo.txt/mp3) |
| 3 | cta | trilha2 | Legado opcional; CTA deve ficar no outro |
| 4 | brasil | trilha2 | Agente (brasil.txt/mp3) |
| 5 | saude | ciencia_bg | Opcional |
| 6 | ciencia | ciencia_bg | Opcional |
| 7 | politica | economia_bg | Opcional |
| 8 | tecnologia | tech_bg | Agente (tecnologia.txt/mp3) |
| 9 | economia | economia_bg | Agente (economia.txt/mp3) |
| 10 | ofertas | mensagem_bg | Agente (ofertas.txt/mp3) |
| 11 | frase | mensagem_bg | Agente (frase.txt/mp3) |
| 12 | historia | tech_bg | Agente (historia.txt/mp3) |
| 13 | outro | trilha1 | Mixer (lê outro.txt) |

### Sistema de vozes (Edge TTS local)

| Regra editorial | Voz edge-tts |
|---|---|
| Segunda, quarta e sábado | Thalita — `pt-BR-ThalitaMultilingualNeural` |
| Terça e quinta | Francisca — `pt-BR-FranciscaNeural` |
| Sexta-feira especial | Francisca + Thalita, alternadas por bloco |
| Headers de seção | Antonio — `pt-BR-AntonioNeural` |
| Domingo | Sem episódio; manutenção |

A seleção usa `D5N_EDITORIAL_DATE` ou a data corrente em `America/Sao_Paulo`; nunca o dia de execução de um reprocessamento histórico. Gemini TTS permanece proibido.

### Cronograma diário

| Horário | Tarefa | Descrição |
|---------|--------|-----------|
| 03:00 | Geração do site | `gerar_pagina_d5n.py` coleta, curadoria, HTML, feeds |
| 04:00 | Pipeline do podcast | TTS + mixagem → MP3 final, de segunda a sábado; domingo é manutenção |
| 08:00 | Radar matinal | Prévia dos 5 temas quentes do dia |
| 10:00 | Global + Brasil | Bloco de notícias globais e nacionais |
| 14:00 | Tech & IA | Bloco de tecnologia e inteligência artificial |
| 17:00 | Kinetic + Telegram | D5N Kinetic Pipeline (Remotion) → entrega Telegram. **Fds:** pulado |
| 21:00 | Seleção do Dia | Curadoria final para o episódio |

---

## Estrutura do repositório

```
d5n-videocast-source/
├── gerar_pagina_d5n.py          # Script principal — gera HTML, feeds, source.md
├── gerar_cards_pipeline.py      # Gera cards PNG para Instagram
├── gerar_cards_instagram_d5n.py # Cards individuais por notícia
├── deploy_d5n_site.sh           # Deploy: valida MP3, copia com/sem número (fds) para audio/, atualiza contador e faz git push
├── deploy_netlify_direct.py     # Deploy direto via API Netlify (backup)
│
├── index.html                   # Site principal (gerado diariamente)
├── feed.json                    # JSON Feed (gerado diariamente)
├── d5n-feed.xml                  # RSS Feed (gerado diariamente)
├── source.md                    # Roteiro do podcast (gerado diariamente)
├── episode-counter.json         # Contador persistente de episódios (dias úteis apenas — fds não incrementa)
├── autoavaliacao-score.json     # Score diário de qualidade
├── autoavaliacao-issues.json    # Issues de qualidade detectadas
│
├── 2026/                        # Arquivo histórico (1 .md por dia)
│   ├── 2026-05-24.md
│   ├── 2026-05-25.md
│   └── ...
│
├── audio/                       # Episódios MP3
│   ├── d5n-ep004-2026-05-28.mp3
│   ├── d5n-ep032-2026-06-29.mp3
│   ├── d5n-ep033-2026-07-09.mp3
│   └── d5n-weekend-2026-07-12.mp3  # sem número (fim de semana)
│
├── cards-instagram/             # Cards PNG por data
│   └── YYYY-MM-DD/
│       ├── resumo_YYYY-MM-DD.png
│       └── individuais/
│
├── manha-conectada/             # Projeto isolado da Manhã Conectada
├── fechamento/                # Fechamento do Mercado 17h (pipeline, mixer, RSS, capa 1400)
│   ├── scripts/                 # Pipeline, mixer, RSS, publicação e cron
│   ├── assets/                  # Capa 1400 + identidade sonora
│   ├── audio/                   # Episódios FM
│   ├── manifests/               # Manifests
│   ├── roteiros/                # source-fechamento-YYYY-MM-DD.md
│   ├── feeds/                   # RSS próprio
│   └── docs/                    # Contrato/RSS

│   ├── scripts/                 # Pipeline, mixer, RSS, publicação e cron
│   ├── assets/                  # Capa e identidade sonora próprias
│   ├── audio/                   # Episódios da MC
│   ├── manifests/               # Histórico de manifests
│   ├── roteiros/                # source-manha-YYYY-MM-DD.md
│   ├── feeds/                   # RSS próprio (URL pública preservada por rewrite)
│   ├── docs/                    # Diretrizes editoriais
│   └── cron-prompt.txt          # Prompt operacional do cron diário
│
├── scripts/                     # Scripts auxiliares do D5N
│   ├── d5n-babysitter.py            # Validação automática
│   ├── d5n_marketing.py              # Geração de copy marketing
│   ├── validate_mp3.py              # Validação de MP3
│   └── reports/                      # Relatórios de qualidade
│
├── trilhas/                     # Trilhas sonoras do podcast
│   ├── intro_bg.mp3             # Background da intro
│   ├── trilha1.mp3              # Trilha principal (mundo/brasil)
│   ├── trilha2.mp3              # Trilha secundária (cta/brasil)
│   ├── tech_bg.mp3              # Background tech
│   ├── economia_bg.mp3          # Background economia
│   ├── ciencia_bg.mp3           # Background ciência/saúde
│   └── mensagem_bg.mp3          # Background ofertas/frase
│
├── docs/                        # Documentação
│   └── SPRINTS_CORRECAO.md      # Plano de correção em sprints
│
├── privacidade.html             # Política de privacidade
├── netlify.toml                 # Config Netlify (headers, redirects)
├── og-image.png                 # Open Graph image
│
├── .github/workflows/
│   └── update.yml               # GitHub Actions (cron 04:00 UTC)
│
├── README.md                    # Este arquivo
├── CHANGELOG.md                 # Histórico de mudanças
├── CONTRIBUTING.md              # Guia de contribuição
├── ARCHITECTURE.md              # Documentação de arquitetura
└── .gitignore
```

### Scripts do pipeline de áudio (Hermes Agent Skills)

Os scripts de áudio vivem em dois perfis do Hermes Agent:

```
# Profile default
~/.hermes/skills/media/trends-podcast/scripts/
├── d5n-inject-date.py           # Injeta data correta no source.md
├── d5n-date-context.py          # Provê contexto de data (weekday, mês, etc)
├── drop5news-mixer-v9.py        # Mixer principal (13 seções, TTS, mixagem)
├── pipeline_selecao.py          # Seleção matinal de 3-5 tópicos
├── gerar-secoes-v2.py           # Divide source.md em 13 arquivos .txt
└── d5n-pre-gen-gate.py          # Gate de pré-validação

# Profile d5n (cópia sincronizada)
~/.hermes/profiles/d5n/skills/media/trends-podcast/scripts/
└── (mesmos arquivos)

# Scripts do scheduler
~/.hermes/scripts/
├── drop5news-pipeline.sh        # Pipeline orquestrador
├── drop5news-mixer-exec.sh      # Executor do mixer (sync source.md + inject-date)
└── _deprecated/
    └── split_roteiro.py         # Código morto (movido em 12/07/2026)
```

---

## Como funciona

### Geração diária (local — servidor homelab)

```bash
# Pipeline completo (via cron do Hermes Agent)
python3 gerar_pagina_d5n.py --data $(date +%Y-%m-%d)

# Sem podcast (apenas site)
python3 gerar_pagina_d5n.py --data 2026-07-08 --no-podcast

# Mixer (áudio only)
cd /tmp/d5n_audio
python3 ~/.hermes/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py

# Deploy
git add -A && git commit -m "D5N $(date +%Y-%m-%d)" && git push
```

### Pipeline de áudio (passo a passo)

```bash
# 1. Copiar source.md para staging
cp /root/repositorio/d5n-videocast-source/source.md /tmp/d5n_audio/source.md

# 2. Injetar data correta
python3 ~/.hermes/skills/media/trends-podcast/scripts/d5n-inject-date.py

# 3. Dividir em seções
cd /tmp/d5n_audio
python3 ~/.hermes/skills/media/trends-podcast/scripts/gerar-secoes-v2.py

# 4. Mixar
python3 ~/.hermes/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py

# 5. Output: /tmp/d5n_mixado_v9.mp3
```

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

### Vozes oficiais (padrão vigente)
- **Thalita** — conteúdo de segunda, quarta e sábado — `pt-BR-ThalitaMultilingualNeural`
- **Francisca** — conteúdo de terça e quinta — `pt-BR-FranciscaNeural`
- **Sexta-feira** — edição especial com Francisca e Thalita alternadas por bloco.
- **Antonio** — headers de seção — `pt-BR-AntonioNeural`
- A data editorial determina o plano de vozes; Gemini TTS permanece apenas como legado proibido.

---

## Configuração

### Variáveis de ambiente

```bash
D5N_BASE=/root/repositorio/d5n-videocast-source  # Diretório base
```

### Dependências

```bash
# Python 3.11+
# Para site: apenas stdlib (sem dependências externas)
# Para TTS: edge-tts, pydub
# Para cards: Pillow, requests
# Para deploy: curl, git
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

Validação automática diária (05:05):
- ✅ Arquivo MP3 existe e tem duração > 0
- ✅ HTML tem > 10 notícias
- ✅ Source.md gerado corretamente
- ✅ Feeds (JSON + RSS) válidos
- ✅ 4 pilares presentes

Validators:
- `d5n-audio-check.py` — valida MP3 (duração, tamanho)
- `d5n-pilares-check.py` — valida presença dos 4 pilares
- `d5n-date-check.py` — valida data no source.md

### Auto-avaliação

Scores diários em `autoavaliacao-score.json`:
- Qualidade da curadoria
- Diversidade de fontes
- Cobertura de pilares
- Duração do podcast

---

## Plano de Correção — Sprint 2026-07-12

Em 12/07/2026, foram identificados e corrigidos 11 bugs no pipeline D5N que causavam:
- Data errada nos áudios ("sábado" em vez de "domingo")
- Voz errada ("Marina" — nome inexistente no persona system)
- Seções não processadas (frase e historia ignoradas)
- Hook com dia errado no "Amanhã Conectada"

Ver [docs/SPRINTS_CORRECAO.md](docs/SPRINTS_CORRECAO.md) para o plano completo de sprints.

### Bugs críticos corrigidos

| # | Bug | Severidade | Root Cause |
|:-:|-----|:----------:|------------|
| 1 | inject-date: path inexistente | CRÍTICO | `os.popen()` retornava vazio, `json.loads("")` falhava |
| 2 | source.md stale em /tmp/ | CRÍTICO | Mixer lê .txt do disco; .txt desatualizado = áudio errado |
| 3 | pipeline_selecao: KeyError | CRÍTICO | Dict só tinha MUNDO; append para GLOBAL quebrava |
| 4 | Mixer: nomes marina/talita | ALTO | Variáveis apontavam para vozes erradas |
| 5 | Mixer: mensagem vs ofertas | CRÍTICO | dual_sections e regenação TTS desalinhados com SECOES |
| 6 | Validador: falso positivo | MÉDIO | Substring search por "sábado" pegava notícias |
| 7 | intro.txt: "Aqui é Marina" | ALTO | Nome não existe no persona system |
| 8 | SKILL.md: refs Marina | MÉDIO | 16 referências desatualizadas |
| 9 | split_roteiro.py: código morto | BAIXO | Não referenciado em pipeline ativo |
| 10 | frase/historia ignorados | MÉDIO | Gerador criava arquivos não processados |
| 11 | Amanhã Conectada: hook errado | MÉDIO | LLM não recebia dia da semana |
| **12** | **Fim de semana consome números de sequência** | **MÉDIO** | `deploy_d5n_site.sh` agora detecta sáb/dom e salva `d5n-weekend-{DATE}.mp3` sem incrementar `last_episode`. `find_latest_podcast()` pula entradas de fds no histórico. |

---

## Histórico

| Data | Marco |
|------|-------|
| **Mai 2026** | Lançamento — site básico + podcast |
| **Jun 2026** | 32 episódios, cards Instagram, analytics |
| **Jul 2026** | Sprint 1-3: Bug fixes, visual upgrade, busca/filtros |
| **12/07/2026** | Sprint correção: 11 bugs corrigidos, 13 seções no mixer |
| **13/07/2026** | Fim de semana não consome número de episódio — `d5n-weekend-{DATE}.mp3`, skip em `find_latest_podcast()` |

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
