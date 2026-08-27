# Padrões do Projeto D5N — Estado Atual

> **Última atualização:** 2026-08-26
> **Live:** https://d5n-daily.netlify.app

---

## Os 3 Programas e Seus Feeds RSS

| Programa | Feed RSS (URL pública) | Script | Capítulos |
|---|---|---|---|
| Drop Five News (D5N) | `https://d5n-daily.netlify.app/podcast.xml` | `scripts/gerar_podcast_feed.py` | Labels sem timestamp (coldopen.txt) |
| Manhã Conectada (MC) | `https://d5n-daily.netlify.app/manha-conectada.xml` | `manha-conectada/scripts/gerar_manha_conectada_feed.py` | Com timestamp real (roteiro) |
| Fechamento do Mercado (FM) | `https://d5n-daily.netlify.app/fechamento.xml` | `fechamento/scripts/gerar_fechamento_feed.py` | Com timestamp real (roteiro) |

---

## Capas dos Programas (arte final)

| Programa | RSS / Agregador | Site (background) |
|---|---|---|
| D5N | `podcast-cover.jpg` (1400×1400) | `podcast-cover-bg.png` (400×400) |
| Manhã Conectada | `manha-conectada-cover.jpg` (1400×1400) | `manha-conectada-cover-bg.png` (400×400) |
| Fechamento | `fechamento-cover.jpg` (1400×1400) | `fechamento-cover-bg.png` (400×400) |

- **Origem das capas:** `/manha-conectada/assets/` e `/fechamento/assets/` (arte profissional)
- **D5N:** `/img_1e60980ddb60.jpg` (enviada via WhatsApp pelo Jean)
- **RSS:** JPEG para compatibilidade com agregadores
- **Site:** PNG 400×400 com `mix-blend-mode:luminosity` + backgrounds semi-transparentes

---

## Formato de Capítulos RSS

### Namespace
```xml
xmlns:podcast="https://podcastindex.org/namespace/1.0"
xmlns:psc="http://podlove.org/simple-chapters"
```

### D5N — labels sem timestamp (coldopen.txt sem timing real)
```xml
<podcast:chapters version="1.2" src="...mp3">
  <psrc:chapter title="Abertura"/>
  <psrc:chapter title="Brasil &amp; Política"/>
  <psrc:chapter title="Economia"/>
  <psrc:chapter title="Mundo"/>
  <psrc:chapter title="Tecnologia &amp; Inovações"/>
  <psrc:chapter title="Encerramento"/>
</podcast:chapters>
<psc:chapters version="2.0">
  <psc:chapter title="Abertura"/>
  ...
</psc:chapters>
```

### MC — timestamp real (proporcional ao roteiro)
```xml
<psrc:chapter startTime="0" title="Abertura"/>
<psrc:chapter startTime="1800" title="Agenda"/>
<psrc:chapter startTime="53312" title="Clima &amp; País"/>
...
```

---

## Gerar Todos os Feeds

```bash
cd /root/repositorio/d5n-videocast-source

# D5N
python3 scripts/gerar_podcast_feed.py

# MC
python3 manha-conectada/scripts/gerar_manha_conectada_feed.py

# FM
python3 fechamento/scripts/gerar_fechamento_feed.py

# Copiar para repo root (Netlify serve do root)
cp manha-conectada/feeds/manha-conectada.xml .
cp fechamento/feeds/fechamento.xml .

# Commit + push (dispara Netlify)
git add podcast.xml manha-conectada.xml fechamento.xml
git commit -m "chore: regenerate feeds"
git push origin HEAD:master
```

---

## Crons de Publicação

| Cron | Horário | O que faz |
|---|---|---|
| `d5n-podcast-diario` | 03:00 seg-sáb | Gera D5N + podcast.xml (chama `gerar_podcast_feed.py`) |
| `manha-conectada-diario` | 09:00 seg-sex | Gera MC (chama `gerar_manha_conectada_feed.py`) |
| `fechamento-diario` | 16:30 seg-sex | Gera FM (chama `gerar_fechamento_feed.py`) |
| `d5n-fechamento-mercado` | 17:00 seg-sex | Script card fechamento (no_agent) |
| `fm-publish-watchdog` | 18:00 seg-sex | Watchdog FM (no_agent) |

**Importante:** os crons rodam a pipeline completa que chama os scripts de feed. O site (`gerar_pagina_d5n.py`) também chama `gerar_podcast_feed.py` ao gerar.

---

## D5N — Como Gerar Capítulos

Os capítulos D5N usam o `coldopen.txt` do manifest do dia:
```
manifests/d5n/<data>/coldopen.txt  →  load_program_chapters("d5n", date, dur)
```

- Divide o coldopen em frases por pontuação forte
- Gera 6 labels: Abertura, Brasil & Política, Economia, Mundo, Tecnologia & Inovações, Encerramento
- **Sem timestamp real** — só labels (coldopen é texto corrido, sem timing)

Para episódios sem `coldopen.txt` → nenhum capítulo.

---

## MC/FM — Como Gerar Capítulos

MC e FM usam os roteiros aprovados:
```
manha-conectada/roteiros/source-manha-<data>.md
fechamento/roteiros/source-fechamento-<data>.md
  →  load_program_chapters("manha-conectada"|"fechamento", date, dur)
```

- Extrai parágrafos do bloco `## Roteiro aprovado`
- Pesa por tamanho para distribuir timestamps proporcionais
- **Com timestamp real**

### Labels MC (8 labels)
`Abertura → Agenda → Clima & País → Mundo → Tecnologia → Economia → Sinal 11 → Encerramento`

### Labels FM (6 labels)
`Abertura → Bolsa → Câmbio → Fluxo estrangeiro → Empresas & Radar Amanhã → Encerramento`

---

## CSS do Site — Backgrounds de Capas

Os painéis MC/FM/D5N usam `::before` com as capas bg:

```css
.d5n-program::before {
  background-image: url("/podcast-cover-bg.png");
  opacity: 0.55;
  mix-blend-mode: luminosity;
}
.morning-program#manha-conectada::before {
  background-image: url("/manha-conectada-cover-bg.png");
  opacity: 0.40;
}
.morning-program#fechamento::before {
  background-image: url("/fechamento-cover-bg.png");
  opacity: 0.50;
}
```

Backgrounds dos painéis semi-transparentes para o cover aparecer por baixo:
```css
background: rgba(10,16,30,0.45-0.55);
```

---

## Estrutura de Arquivos Chave

```
d5n-videocast-source/
├── _shared_chapters.py          # Funções compartilhadas de capítulos
├── scripts/gerar_podcast_feed.py # D5N feed RSS
├── manha-conectada/
│   ├── scripts/gerar_manha_conectada_feed.py
│   └── feeds/manha-conectada.xml
├── fechamento/
│   ├── scripts/gerar_fechamento_feed.py
│   └── feeds/fechamento.xml
├── podcast.xml                  # D5N (copiado do scripts/gerar_podcast_feed.py)
├── manha-conectada.xml          # MC (copiado)
├── fechamento.xml               # FM (copiado)
├── podcast-cover.jpg            # D5N RSS
├── podcast-cover-bg.png        # D5N site
├── manha-conectada-cover.jpg   # MC RSS
├── manha-conectada-cover-bg.png # MC site
├── fechamento-cover.jpg         # FM RSS
├── fechamento-cover-bg.png     # FM site
└── gerar_pagina_d5n.py         # Site completo + chama scripts de feed
```

---

## Regras de Ouro

1. **SEMPRE fazer `git push origin HEAD:master`** após commits — o Netlify builda apenas o `master`. Se commits ficarem num branch separado, verificar com `git log master --oneline` e corrigir com `git push origin <branch>:master`.
2. **ATUALIZAR FEEDS EM AMBOS OS LOCAIS** — o `netlify.toml` tem redirects: `/manha-conectada.xml` → `manha-conectada/feeds/manha-conectada.xml` e `/fechamento.xml` → `fechamento/feeds/fechamento.xml`. Sempre copiar: `cp manha-conectada.xml manha-conectada/feeds/ && cp fechamento.xml fechamento/feeds/`.
3. **MC script requer manifests canônicos** — `manha-conectada/scripts/gerar_manha_conectada_feed.py` exige `manifests/<data>.json` com `prototype: false` para cada episódio. Se o script gerar poucos episódios, os manifests podem ter sido movidos ou deletados. Nesse caso, usar o XML existente (ele foi gerado quando os manifests existiam) e atualizá-lo manualmente.
4. **Push para master ativa o Netlify** — o deploy é automático ao fazer push no master.
5. **Validar XML antes de push** — rodar `python3 -c "import xml.etree.ElementTree as ET; ET.parse('podcast.xml')"`.

## Estado Atual dos Feeds (2026-08-26)

| Programa | Episódios | lastBuildDate | ttl | Capas | Capítulos |
|---|---|---|---|---|---|
| D5N | 56 | 26/08 23:29 | 60 | ✅ .jpg | ✅ 5 eps com labels |
| MC | 16 | 26/08 23:50 | 60 | ✅ .jpg | ✅ timestamp real |
| FM | 3 | 26/08 17:30 | 60 | ✅ .jpg | ✅ labels proporcionais |

## URLs para Cadastro no Agregador

- **D5N:** `https://d5n-daily.netlify.app/podcast.xml`
- **MC:** `https://d5n-daily.netlify.app/manha-conectada.xml`
- **FM:** `https://d5n-daily.netlify.app/fechamento.xml`
