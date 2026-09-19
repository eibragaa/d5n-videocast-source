# D5N IA Best Practices — aplicação dos 10 insights de Bruno Okamoto

**Fonte:** vídeo "10 coisas que eu gostaria de saber antes de criar meu agente de IA" — Bruno Okamoto, 2026.

## 1. Prompt vs Skills

**Insight:** menos agentes, mais skills. Um agente com muitas skills > vários agentes espalhados. Skill = processo repetitivo transformado em resultado esperado e reutilizável.

**Aplicação D5N:**
- Cada pipeline (D5N, MC, FM) vira uma **skill** documentada, não um script solto.
- O mixer (`drop5news-mixer-v10.py`) é a skill de "monta o episódio".
- O `gerar_pagina_d5n.py` é a skill de "gera o site".
- Skills não devem depender umas das outras — cada uma roda standalone e pode ser testada isolada.

**Ação:** consolidar em `/root/.hermes/skills/d5n-pipeline/` com README claro de inputs/outputs.

---

## 2. Higienização e Manutenção

**Insight:** agente = computador. Precisa de manutenção como um carro: auditoria mensal de RAM/storage, limpeza de arquivos parados, backup diário, auditoria de skills (usadas vs não usadas).

**Aplicação D5N:**
- VPS Hostinger KVM2: 2GB RAM/agente, até 3 agentes, 100GB espaço.
- Cron semanal: verificar uso de RAM, storage livre, arquivos >30 dias sem acesso.
- Backup diário dos manifests e dos episódios gerados.
- Auditoria de skills: rastrear quais skills foram usadas e com quantas correções.

**Ação:** script `scripts/auditar-agente.sh` + crons de manutenção.

---

## 3. Governança

**Insight:** permissionamento, regras, system prompt, limites de autonomia, até onde o agente pode ir. Better: um agente com múltiplas auditorias internas do que 10 agentes para auditar.

**Aplicação D5N:**
- Cada pipeline tem **system prompt** definido (não hardcodeado no script).
- Limites explícitos: o que o agente pode publicar sem aprovação, o que precisa de review.
- Guardrails: quais ações são irreversíveis (deploy no Netlify, post no Instagram).

**Ação:** arquivo `GOVERNANCA.md` por pipeline com: system prompt, limites, permissionamento, guardrails.

---

## 4. Segundo Cérebro (Estrutura de Pastas + Mapa)

**Insight:** segundo cérebro = composição de pastas bem organizadas. Pasta `memory/` padrão, `daily-note` por interação, mapa.md por pasta explicando o que tem lá.

**Aplicação D5N:**
- Raiz do repo: `mapa.md` com descrição de todas as pastas.
- Cada pasta crítica: `mapa.md` explicando os arquivos.
- Pasta `memory/`: logs de interações, contexto acumulado.
- Pasta `manifests/`: manifests dos episódios (input do mixer).

**Ação:** criar mapa.md nos repos críticos.

---

## 5. Memória por Usuário (Roncho-like)

**Insight:** agente que lembra de cada usuário, suas preferências, feedbacks, decisões. Camada de personalização.

**Aplicação D5N:**
- D5N é single-player (apenas o Jean usa). Mas a estrutura deve suportar multiplayer no futuro.
- Persistir: preferências editoriais, ajustes de roteiro, feedbacks dados.
- Estado em `/root/.hermes/state/d5n/` (JSON por execução).

**Ação:** criar estrutura de estado por pipeline.

---

## 6. Gbrain / Indexação de Memória

**Insight:** indexar o cérebro do agente para busca. GraphRAG: download + indexação offline. Funciona universalmente (Claude, Codex, Ollama).

**Aplicação D5N:**
- Indexar histórico de episódios, roteiros, correções.
- Busca sobre: "qual foi o último episódio sobre X?", "quantos episódios por mês?".
- Implementação simples: SQLite ou arquivo JSON indexado.

**Ação:** índice de episódios em `/root/.hermes/state/d5n/index.json`.

---

## 7. Single Player vs Multiplayer

**Insight:** single player = agente para você, acesso total, poucas regras. Multiplayer = agente para outros, precisa de permissionamento, backup de conversas, decisões categorizadas, até onde cada pessoa pode usar.

**Aplicação D5N:**
- Hoje: single player (Jean). Agent e tem acesso total aos feeds.
- Se escalarmos para multiplayer (outras pessoas acessando o D5N): repensar estrutura, adicionar auth, permissionamento por usuário, log de ações por usuário.

**Ação:** documento `SINGLE-vs-MULTIPLAYER.md` com trigger points para migrar.

---

## 8. LLMs e Custos

**Insight:** usar API em vez de assinatura pessoal para agentes (Antropic não permite assinatura personal em agentes). Custo pragmático: $0.052/M in, $0.17/M out para deepseek-v4-flash.

**Aplicação D5N:**
- Provider atual: deepseek-v4-flash (via API directa).
- Alternativas no config: xiaomi/mimo-v2.5, groq/llama-3.3, cerebras, openrouter.
- Auditar custo por episódio: quantos tokens por pipeline, qual provider é mais barato.

**Ação:** dashboard de custo em `scripts/custo-episodio.sh` (estimativa baseada em contador de tokens).

---

## 9. Padronização / SOP

**Insight:** processos documentados. Qualquer trabalho repetitivo tem processo. Repetição = o que faz o dinheiro rodar.

**Aplicação D5N:**
- PADRAO.md unificado com: como gerar episódio, como validar, como fazer deploy, como adicionar fonte.
- Cada script tem --help claro.
- Padrão de commits: `feat:`, `fix:`, `chore:`, `docs:`.

**Ação:** `PADRAO.md` na raiz do repo D5N.

---

## 10. Automação de Auditoria

**Insight:** crons para auto-auditoria. Agente audita a si mesmo: VPS, skills, contexto, brain. Manutenção não pode depender de ação manual.

**Aplicação D5N:**
- Cron `d5n-auditar-semanal` (domingo): RAM, storage, skills usadas, erros dos últimos 7 dias.
- Cron `d5n-backup-diario`: backup dos manifests + episódios.
- Watchdog: se d5n-podcast-diario falhar, alertar + tentar auto-heal.

**Ação:** 2 crons + watchdog no Hermes.

---

## Prioridade de implementação

| Prioridade | Ação | Esforço |
|---|---|---|
| 1 | `mapa.md` nos repos críticos (D5N, financas-pessoal, instagram-premium) | 30 min |
| 2 | `GOVERNANCA.md` por pipeline (D5N, MC, FM) | 45 min |
| 3 | Script de auditoria semanal (`scripts/auditar-agente.sh`) | 1h |
| 4 | Crons de manutenção no Hermes | 30 min |
| 5 | `PADRAO.md` unificado D5N | 30 min |
| 6 | Índice de episódios (`index.json`) | 20 min |
| 7 | Consolidar scripts em skills (`/root/.hermes/skills/d5n-pipeline/`) | 1h |
| 8 | Dashboard de custo por episódio | 30 min |
| 9 | `SINGLE-vs-MULTIPLAYER.md` | 20 min |
| 10 | Watchdog para d5n-podcast-diario | 40 min |

---

**Status:** pending implementation.
