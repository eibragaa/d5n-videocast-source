# Site Todo — Aperfeiçoamento Crítico (Sprint 6)

Loop Crítico→Executor AAA aplicado.

## Crítico (antes)
- D5N órfão: `player-bar` 3px vs 14px, sem `::before` cover, sem vars `--d5n`
- Split corta arte: `border-right` + `background:#101727` opaco esconde cover nos boxes MC/FM
- Cover 0.07 fraco

## Executor (corrigido)
- `--d5n:#94a3b8 --d5n-deep --d5n-line` + `player-bar` 14px + `::before podcast-cover.png` 0.06
- MC/FM: `intro` `rgba(16,23,39,0.88)` + `listen` `rgba(19,25,32,0.72)` + `blur(1px)`, cover 0.10
- `fechamento-intro` `rgba(13,26,43,0.85)`
- Ordem: D5N hero 5h → MC 11h → FM 17h (stack verificado)
- Tests 10/10, `index.html` 126KB, `--site-only` ok
