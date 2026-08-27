# STANDARDS — Drop Five News Podcast Pipeline

> Arquitetura, padrões e procedimentos para os 3 programas de áudio do D5N:
> **D5N** (Drop Five News), **MC** (Manhã Conectada), **FM** (Fechamento do Mercado).

---

## 🎯 Arquitetura de Feeds

Cada programa tem **2 cópias** do feed XML:

| Feed | Usado por | Onde está |
|---|---|---|
| `*.xml` (root) | Agregadores externos (AntennaPod, Pocket Casts, etc.) | Raiz do repo |
| `feeds/*.xml` | Redirect Netlify `/programa.xml` → `/programa/feeds/` | `feeds/` de cada programa |

Os **redirects Netlify** (netlify.toml) mapeiam:
```
/manha-conectada.xml  → /manha-conectada/feeds/manha-conectada.xml
/fechamento.xml       → /fechamento/feeds/fechamento.xml
/audio/fechamento-*   → /fechamento/audio/fechamento-:splat
/audio/manha-conectada-* → /manha-conectada/audio/manha-conectada-:splat
```

**REGRA:** Após regenerar qualquer feed, **copiar para ambas as localizações**:
```bash
# MC
python3 manha-conectada/scripts/gerar_manha_conectada_feed.py
cp manha-conectada/feeds/manha-conectada.xml manha-conectada.xml

# FM
python3 fechamento/scripts/gerar_fechamento_feed.py
cp feeds/fechamento.xml ../fechamento.xml

# D5N
python3 scripts/gerar_podcast_feed.py   # já gera em podcast.xml (root)
```

---

## 🏛️ Regras de Ouro

### 1. Sempre `git push origin HEAD:master`
O Netlify builda **apenas** o branch `master`. Commits em outros branches não vão ao ar.
```bash
# ✅ CERTO — push direto para master
git add ... && git commit -m "..." && git push origin HEAD:master

# ❌ ERRADO — vai para branch, Netlify não builda
git add ... && git commit -m "..." && git push origin HEAD:test/fechamento-mercado
```

**Verificação:** após push, confirmar com `git log master --oneline | head -3`

### 2. Sempre validar antes de pushar
Rodar `scripts/validate_feeds.py` após gerar feeds:
```bash
python3 scripts/validate_feeds.py
# Saída deve mostrar: ✅ ALL 3/3 feeds PASS
```

### 3. Sempre verificar URLs de enclosure
Um enclosure **DEVE** apontar para o caminho real do MP3:

| Programa | Caminho do enclosure |
|---|---|
| D5N | `https://d5n-daily.netlify.app/audio/{arquivo}.mp3` |
| MC | `https://d5n-daily.netlify.app/manha-conectada/audio/{arquivo}.mp3` |
| FM | `https://d5n-daily.netlify.app/fechamento/audio/{arquivo}.mp3` |

**NUNCA** usar `/audio/` para MC ou FM — esses programas têm subdiretórios próprios.

### 4. O episódio só entra no feed se o MP3 existir
Os scripts de feed **validam que o arquivo existe** antes de incluir. Feed com enclosure fantasma (MP3 que não existe) = podcast quebrado para os ouvintes.

---

## 📡 Estado Atual dos Feeds (2026-08-27)

| Programa | Episódios | Último | ttl | Capas | Caminho MP3 |
|---|---|---|---|---|---|
| D5N | 54 | 27/08 (ep065) | ✅ 60 | ✅ cover.jpg | `/audio/` |
| MC | 13 | 17/08 | ✅ 60 | ✅ cover.jpg | `/manha-conectada/audio/` |
| FM | 2 | 26/08 | ✅ 60 | ✅ cover.jpg | `/fechamento/audio/` |

### Sobre os episódios ausentes (24-26/08)
- **D5N ep062-064 (24-26/ago):** Manifests existem mas MP3s não foram gerados. Pendente pipeline.
- **MC 24-26/ago:** Sem manifestos — episódio não foi gerado pela pipeline.
- **FM 24-25/ago:** MP3s ausentes.

---

## 🔄 Cron Jobs (automação)

| Cron | Schedule | O que faz | Status |
|---|---|---|---|
| `d5n-podcast-diario` | seg-sex 03:00 BRT | Gera D5N feed + valida + push | ✅ |
| `manha-conectada-diario` | seg-sex 09:00 BRT | Gera MC feed + valida + push | ✅ |
| `fechamento-diario` | seg-sex 16:30 BRT | Gera FM feed + valida + push | ✅ |
| `d5n-fechamento-mercado` | seg-sex 17:00 BRT | Card B3 fechamento mercado | ⚠️ erro |
| `fm-publish-watchdog` | seg-sex 18:00 BRT | Verifica FM no feed, regenera se ausente | ✅ |

---

## 📁 Estrutura do Repo

```
d5n-videocast-source/
├── audio/                         # D5N MP3s (ep001-ep065)
│   └── d5n-ep{NNN}-{DATA}.mp3
├── manifests/
│   └── d5n/
│       └── {DATA}/manifest.json   # Um por episódio gerado
├── manha-conectada/
│   ├── audio/                     # MC MP3s
│   ├── feeds/                     # Feed MC (redirect Netlify)
│   │   └── manha-conectada.xml
│   ├── manifests/                  # Um por episódio MC
│   │   └── {DATA}.json
│   └── scripts/
│       └── gerar_manha_conectada_feed.py
├── fechamento/
│   ├── audio/                     # FM MP3s
│   ├── feeds/                     # Feed FM (redirect Netlify)
│   │   └── fechamento.xml
│   ├── manifests/
│   └── scripts/
│       └── gerar_fechamento_feed.py
├── scripts/
│   ├── gerar_podcast_feed.py      # Gera podcast.xml (D5N)
│   ├── validate_feeds.py          # Pre-flight validation
│   └── gerar_pagina_d5n.py
├── podcast.xml                    # Feed D5N (root)
├── manha-conectada.xml           # Feed MC (root, redirect → feeds/)
├── fechamento.xml                 # Feed FM (root, redirect → feeds/)
├── episode-counter.json           # Contador global D5N (legado)
├── netlify.toml                   # Headers + redirects
└── STANDARDS.md                   # Este arquivo
```

---

## 🧪 Pre-Flight Validation

```bash
# Validar todos os feeds
python3 scripts/validate_feeds.py

# Validar um específico
python3 scripts/validate_feeds.py --feed D5N

# Validar vs live (Netlify)
python3 scripts/validate_feeds.py --live
```

**O que verifica:**
- ✅ XML bem formado
- ✅ `<ttl>60</ttl>` presente
- ✅ MP3s respondem HTTP 200 (sample 5 episódios)
- ✅ Enclosures são URLs válidas

**Exit codes:** 0 = OK, 1 = FAIL (não pushar)

---

## ⚠️ Armadilhas Conhecidas

### 1. Episode counter vs manifests
O D5N feed é gerado pelos **manifests** (`manifests/d5n/{date}/manifest.json`), não pelo `episode-counter.json`. Se um manifest tem `prototype: false` e `audio.file` pointing to an existing MP3, entra no feed. Se falta `audio.file`, não entra.

**Para adicionar episódio ao D5N:** criar `manifests/d5n/{data}/manifest.json` com:
```json
{
  "prototype": false,
  "audio": {"file": "d5n-ep{NNN}-{DATA}.mp3"},
  "sha256": "..."
}
```

### 2. MC: manifest sem `audio.file`
Os manifests MC (`manha-conectada/manifests/{DATA}.json`) têm `audio` como objeto com `duration/size/lufs` mas **sem campo `file`**. O script deriva o nome do arquivo da data do manifest (`{DATA}` → `manha-conectada-{DATA}.mp3`).

### 3. Reverts destroem trabalho
Se um `git revert` ou reset for feito no master, todo o trabalho pode ser perdido. Sempre verificar `git log master --oneline` após operações de git.

### 4. Namespace dos capítulos
Os namespaces de capítulo devem ser:
```xml
xmlns:psrc="https://podcastindex.org/namespace/1.0"
xmlns:psc="http://podlove.org/simple-chapters"
```
Namespace `podcastindex.org/namespace/podcast/chapters` é **incorreto** — causa XML inválido.

### 5. Caminhos de enclosure em scripts
Se o `BASE_URL` ou o caminho no enclosure for mudado, verificar:
- O **Netlify redirect** correspondente existe em `netlify.toml`
- O **script de validação** `validate_feeds.py` verifica URLs contra o `mp3_base` em cada config
- O **diretório de destino** no Netlify coincide com a URL

---

## 🔧 Comandos Úteis

```bash
# Verificar feeds live
curl -sI https://d5n-daily.netlify.app/podcast.xml | head -1
curl -sI https://d5n-daily.netlify.app/manha-conectada.xml | head -1
curl -sI https://d5n-daily.netlify.app/fechamento.xml | head -1

# Verificar MP3 específico
curl -sI https://d5n-daily.netlify.app/audio/d5n-ep065-2026-08-27.mp3 | head -1

# Forçar rebuild Netlify (via Git push)
git add -A && git commit -m "trigger" && git push origin HEAD:master

# Ver git state vs Netlify
git log master --oneline -3
curl -s https://d5n-daily.netlify.app/podcast.xml | grep lastBuildDate

# Count episodes
grep -c '<item>' podcast.xml manha-conectada.xml fechamento.xml
```
