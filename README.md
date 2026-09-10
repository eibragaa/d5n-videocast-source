# Drop Five News (D5N)

**Curadoria diária de notícias via IA** — site, podcast, cards Instagram e distribuição multi-canal.

**Padrão vigente:** [docs/PADRAO_EDITORIAL_AUDIO.md](docs/PADRAO_EDITORIAL_AUDIO.md)

**Site:** [d5n-daily.netlify.app](https://d5n-daily.netlify.app/)

**Instagram:** [@minho.oficial](https://instagram.com/minho.oficial)  
**Telegram:** @minho.oficial  
**Telegram:** @d5n-daily  

## O que é

D5N é um boletim diário de notícias curado por IA, publicado automaticamente todo dia útil. O pipeline coleta notícias de 6+ fontes (Google News, G1, Cointelegraph, Investing.com, VentureBeat, Yahoo Finance), processa via LLM, gera um site estático premium, podcast em áudio (TTS edge-tts) e cards para Instagram — tudo automatizado via Hermes Agent.

### Pilares editoriais

| Pilar | Ícone | Cobertura |
|------|-------|-----------|
| **Global** | 🌍 | Geopolítica, conflitos, diplomacia |
| **Tech & IA** | 🤖 | Tecnologia, inteligência artificial, startups |
| **Economia & Crypto** | 💰 | Mercado financeiro, BCB, criptomoedas |
| **Brasil** | 🇧🇷 | Política nacional, economia doméstica |

### Formatos de saída

| Formato | Descrição |
|---------|-----------|
| **Site HTML** | Página estática com design premium (Libre Baskerville + DM Sans) |
| **Podcast MP3** | **8–12 min** (sempre ≥8 min), 12 seções premium (coldopen, intro, mundo, brasil, tecnologia, economia, interacao, ofertas, frase, recomendacoes, historia, outro). Apresentação alternada entre Thalita e Francisca; sexta-feira usa ambas. |
| **Cards Instagram** | PNG 1080×1080 com foto de fundo + headline + ícone de programa |
| **Feed JSON/RSS** | Para apps e agregadores |
| **Arquivo Markdown** | Histórico diário em DOCX para a turma Pré-Maternal |

### Arquitetura do site

- **Home**: Hierarquia editorial clara (Hero → Programas → Agenda → Footer)  
- **Cards de programa**: Componente master `ProgramCard` com variação de tema, ícone e accent color  
- **Player**: Camada visual própria envolve o HTML5, com play/pause, progresso, velocidade e download  
- **Archivo**: Listagem por mês (ex: `SETEMBRO 2026`), com filtros por programa e histórico de data  

### Pipeline de áudio

1. `gerar_pagina_d5n.py` → gera `index.html` com dados reais dos feeds  
2. `manha-conectada_pipeline.py` → gera feed e áudio para MC  
3. `fechamento_pipeline.py` → gera feed e áudio para FM  
4. `drop5news-mixer-v10.py` → mixa trilhas e gera MP3 final  
5. `validate_feeds.py` → valida feeds e gera relatório  

### Atualizações recentes (09/09/2026)

- **Sprint 1**: Atualização do site com design premium (tokens, ProgramCard, covers)  
- **Sprint 2**: Paginação do arquivo + cover art nos cards  
- **Sprint 3**: Header scrolled + microinterações premium  
- **Sprint 4**: Teste final e documentação  

### Como contribuir

1. **Clone o repositório**  
2. **Crie uma branch** para sua alteração  
3. **Siga o padrão de commits**: `feat: [tipo] [descrição]`  
4. **Teste localmente** com `python3 scripts/validate_feeds.py`  
5. **Submeta PR** com descrição clara do problema e solução  

**Não** faça alterações diretas no `index.html` — use sempre o `gerar_pagina_d5n.py` para evitar corrupção.