# Estado Atual — 2026-08-22

## Produção
- **Branch:** `master` `f61ed88` live https://d5n-daily.netlify.app — site `d5n-daily` `cc6d8958` `master` production (build `6a899873` clear-cache)
- **Preview:** `test/fechamento-mercado` `e70aad7` — PR #1 closed após merge
- **allowed_branches:** `['master','test/fechamento-mercado']`

## Cron
- `fechamento-diario` `30 16 * * 1-5` host = 17h BRT seg-sex — `fechamento_pipeline.py` DeepSeek v4-flash thinking disabled
- `d5n-fechamento-mercado` `0 17 * * 1-5` card 17h intacto
- `manha-conectada` `0 9 * * 1-5` 11h intacto

## Fechamento
- `fechamento/audio/fechamento-2026-08-22.mp3` 8:16 496s 1335w LUFS -16.98 TP -1.7
- `fechamento/feeds/fechamento.xml` → `/fechamento.xml` 200 — `head` + `footer` RSS FECHAMENTO
- `fechamento/assets/fechamento-cover.png` 1400 1.98MB — `fechamento-cover.jpg` backup

## Site AAA
- `d5n-program 05h` grafite `0.10` + `MC 11h` âmbar `0.14` + `FM 17h` petróleo `0.14`/`17` — mesma grade 14px, `51 chapter-segment`, `4 covers`, stack `5h→11h→17h`
- `player-chapters` igual D5N em MC/FM, `valuemax` 296/496

## Custo
- DeepSeek v4-flash `thinking disabled` — `f61ed88` ~$0.001/ep — $1.98 saldo
- `compression` `nvidia/llama-3.1-nemotron-nano-8b-v1` timeout 180s — 401 corrigido

## Docs
- `fechamento/docs/SITE_APERFEICOAMENTO_CRITICO.md`, `FECHAMENTO_RSS.md`, `MELHORIAS_SPRINT5.md`, `FECHAMENTO_CONTRATO.md`, `ESTADO_ATUAL.md`
- `README.md` Estado Atual + fechamento/ + custo, `ARCHITECTURE.md` Fase 4b + hub, `CHANGELOG.md` [Unreleased Fechamento]
