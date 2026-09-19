# Governança — Drop Five News (D5N)

**Última atualização:** 19/09/2026  
**Revisão:** semanal (domingo)

## 1. System Prompt do Agente D5N

O agente D5N opera com as seguintes diretrizes:

- **Objetivo:** curadoria diária de notícias em 12 categorias editoriais, site + podcast + Instagram.
- **Fonte:** 6+ feeds (Google News, G1, Cointelegraph, Investing.com, VentureBeat, Yahoo Finance).
- **Tom:** editorial premium, off-white, serifas, numerais mono, 1 acento lime. Rejeita IA slop (dark ou creme+terracota).
- **Duração podcast:** 8-12 min, 12 seções fixas.
- **Idioma:** português brasileiro.

## 2. Limites de Autonomia

| Ação | Autonomia | Observação |
|---|---|---|
| Gerar site (index.html) | ✅ Automático | Via `gerar_pagina_d5n.py` |
| Gerar feeds RSS | ✅ Automático | Via pipelines MC/FM |
| Mixar áudio (MP3) | ✅ Automático | Via mixer v10, precisa de manifests |
| Deploy no Netlify | ✅ Automático | Via `git push origin HEAD:master` |
| Postar no Instagram | ❌ Manual / aprovado | Cards gerados, post manual ou via automation |
| Postar no Telegram | ✅ Automático | Via Hermes cron |
| Alterar sistema de feeds | ❌ Manual | Requer revisão humana |
| Adicionar nova fonte de notícias | ❌ Manual | Requer revisão humana |
| Alterar design editorial | ❌ Manual | Requer revisão humana |
| Alterar estrutura de pastas | ❌ Manual | Requer revisão humana |

## 3. Guardrails (Regras Irreversíveis)

- **Nunca** editar `index.html` diretamente — sempre via `gerar_pagina_d5n.py`.
- **Nunca** apagar manifests sem backup.
- **Nunca** fazer `git reset --hard` no branch master.
- **Nunca** publicar conteúdo não validado pelos feeds.
- **Sempre** fazer `git push origin HEAD:master` após commits (não PR, não merge manual).

## 4. Permissionamento

| Usuário | Acesso |
|---|---|
| Jean Braga (admin) | Acesso total: todos os scripts, deploys, alterações de config |
| Hermes Agent (automation) | Acesso aos scripts de produção, sem acesso a credenciais diretas |
| Outros (futuro) | TBD — ver SINGLE-vs-MULTIPLAYER.md |

## 5. Auditoria Semanal

**Cron:** `d5n-auditar-semanal` (domingo, 03:00)

Checks:
- [ ] RAM usada pelos processos D5N nos últimos 7 dias
- [ ] Storage livre na VPS (alerta se <20GB)
- [ ] Arquivos em `manifests/` com >30 dias (limpar ou arquivar)
- [ ] Skills usadas vs não usadas (rastrear no index.json)
- [ ] Erros nos logs dos últimos 7 dias
- [ ] Contingência: se d5n-podcast-diario falhou, tentar gerar manifests faltantes

**Relatório:** salvo em `/root/.hermes/state/d5n/auditoria-YYYY-MM-DD.md`

## 6. Backup Diário

**Cron:** `d5n-backup-diario` (todo dia, 02:00)

Backups:
- `manifests/` → `/root/.hermes/backups/d5n/manifests/YYYY-MM-DD/`
- `audio/` → `/root/.hermes/backups/d5n/audio/YYYY-MM-DD/` (se novo áudio)
- `feed.json`, `episode-counter.json` → `/root/.hermes/backups/d5n/state/YYYY-MM-DD/`

Retenção: 30 dias.

## 7. Crise / Failover

Se o pipeline diário falhar:
1. Alertar via Telegram (se configurado)
2. Tentar gerar manifests faltantes automaticamente
3. Se falhar novamente: pular episódio, registrar falha, avisar no dia seguinte

**Registro de falhas:** `/root/.hermes/state/d5n/falhas.json`
