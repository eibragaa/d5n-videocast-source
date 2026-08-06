# D5N — GateDurance: Sistema de Correção e Publicação Garantida

> Documento de operação. LER por qualquer agente que gere, corrija ou publique o
> Drop Five News. Explica o que o pipeline faz, por quê, e as regras imutáveis.

## 1. Problema que este sistema resolve

O roteiro é escrito por um LLM. Historicamente o episódio **não ia ao ar** quando o
LLM escrevia um roteiro que os gates finais rejeitavam, por exemplo:
- notícias **não traduzidas** (texto em inglês no meio do português);
- marcações de leitura que o TTS lê literalmente: `(hum...)`, `(pausa)`, `(pensando)`;
- numeração por extenso: `1 (um), 2 (dois)`;
- markdown/links/emoji dentro do texto falado;
- roteiro abaixo de 850 palavras;
- data editorial incorreta.

O custo de descobrir isso nos gates **finais** (após o TTS) é alto: tokens, tempo e
às vezes o dia fica sem episódio. A solução é validar e corrigir o roteiro **em
texto, antes do TTS** — barato e repetível — com um loop de auto-correção e um
observador que garante que o que foi aprovado é o que vai ao ar.

## 2. Arquitetura (defesa em profundidade, 4 camadas)

```
roteiro (.txt em /tmp/d5n_audio)
   │
   ▼
[1] GateDurance (validação em texto, pré-TTS)  ← BLOQUEIA cedo, sem gastar TTS
   │  se bloqueou (erros MECÂNICOS) →
   ▼
[2] Autocorrect (correção determinística, sem LLM)
   │  re-valida; se ainda bloqueado →
   ▼
[3] GateDurance Loop (orquestra 1+2 até MAX_CORRECT=3)
   │  se exaustão (restam erros que exigem LLM) →
   ▼
[4] Regeneração LLM (job principal / recuperação) → volta ao [1]
   │
   ▼
gates FINAIS (d5n-podcast-quality-gate + d5n_daily_release_gate) → deploy
   │
   ▼
[5] Watchdog (observador contínuo, cron a cada 2h) — garante que o dia não
    fecha sem episódio; pega SEMPRE o texto aprovado.
```

## 3. Componentes e comandos

Todos vivem em `/root/repositorio/d5n-videocast-source/scripts/`.

### 3.1 `d5n-gatedurance-script-gate.py` — o validador (gate)
- **Quando**: sempre depois de escrever os `.txt` de seção e **antes** de qualquer TTS.
- **Comando**:
  ```
  python3 .../scripts/d5n-gatedurance-script-gate.py --date YYYY-MM-DD --audio-dir /tmp/d5n_audio
  ```
- **Exit** `0` = pronto para TTS. `1` = bloqueado (lista de erros).
- **Regras validadas**: ≥9 seções; seções essenciais presentes; texto 100% PT-BR
  (flag trecho em inglês); data editorial + dia da semana na intro; intro começa
  com "Bom dia!"; outro termina com "Bom dia!"; sem `(hum...)`/`(pausa)`; sem
  `1 (um)`; sem emoji/URL/markdown no texto falado; 850–1900 palavras; clichês
  proibidos; despedida/CTA fora do lugar.

### 3.2 `d5n-gatedurance-autocorrect.py` — a correção determinística
- **Quando**: o gate bloqueou por erros **mecânicos**.
- **Comando**:
  ```
  python3 .../scripts/d5n-gatedurance-autocorrect.py --date YYYY-MM-DD --audio-dir /tmp/d5n_audio
  ```
- **Exit** `0` = aprovado após correção. `1` = restam erros que exigem LLM.
- **O que corrige (sem inventar conteúdo)**: remove `(hum...)`/`(pausa)`/`(pensando)`;
  `1 (um)` → `1`; emojis; URLs; markdown (`[x](y)`, `**`, `_`, `` ` ``); colapsa
  reticências espaçadas; remove numeradores/marcadores de lista; garante "Drop
  Five News" em algum segmento; garante que `outro.txt` termina com "Bom dia!".
- **O que NUNCA faz**: não traduz inglês, não inventa notícias, não aumenta a
  contagem para atingir o mínimo, não altera a data.

### 3.3 `d5n-gatedurance-loop.sh` — o orquestrador (regenerate com correções)
- **Quando**: para levar o roteiro ao estado aprovado antes do TTS.
- **Comando**: `bash .../scripts/d5n-gatedurance-loop.sh [--date ...] [--audio-dir ...]`
- **Exit** `0` = aprovado (pronto para TTS). `2` = exaustão (restam erros LLM).
- **Lógica**: valida → se bloqueado, autocorrect+re-valida até 3x → se ainda
  bloqueado, mostra os erros restantes (que exigem regeneração LLM) e sai com `2`.

### 3.4 `d5n-gatedurance-watchdog.sh` — o observador contínuo
- **Quando**: cron `no_agent` a cada 2h (job `[D5N] GateDurance Watchdog`).
- **Comando**: `bash .../scripts/d5n-gatedurance-watchdog.sh [--date ...] [--audio-dir ...]`
- **Exit** `0` = já publicado ou nada a fazer (silêncio, watchdog pattern).
  `1` = roteiro aprovado mas ainda não publicado (sinaliza prosseguir TTS/deploy).
  `2` = exaustão (precisa regeneração LLM; o job de recuperação assume).
- **Regra de ouro**: NUNCA contorna um gate para forçar publicação. Só avança o
  que está genuinamente aprovado.

## 4. Regras de funcionamento (obrigatórias para o agente)

1. **GateDurance sempre antes do TTS.** Depois de escrever TODOS os `.txt` e antes
   de sintetizar QUALQUER áudio, rode o gate. Nunca sintetize com o gate vermelho —
   desperdiça tokens e tempo.
2. **Corrija somente o que o gate apontou.** Diagnóstico → correção do artefato
   específico → re-validação. Não reescreva seções saudáveis.
3. **Auto-correção mecânica primeiro.** Se o bloqueio for por artefatos mecânicos
   (markdown, `(hum...)`, emoji, reticências, `1 (um)`), use o autocorrect antes de
   gastar LLM. Só chame o LLM para o que o autocorrect não resolve (inglês, conteúdo
   abaixo de 850 palavras, data/estrutura).
4. **O texto aprovado é o que vai ao ar.** Se o GateDurance/Loop aprovar um roteiro,
   é esse roteiro que deve seguir para TTS → gates finais → deploy. Não troque por
   outro após a aprovação.
5. **Limite de tentativas.** Respeite `MAX_ATTEMPTS=4` no job principal. Esgotado
   sem `published=true`, pare (exaustão segura) e deixe o watchdog/job de recuperação
   retomar. Nunca loop infinito.
6. **Nunca contorne gate.** Não desative, edite temporariamente ou burle um validador
   para fazer uma tentativa passar. Se um gate falha, o roteiro/áudio precisa de
   correção legítima, não de bypass.
7. **Recibo = verdade.** Publicado só quando `d5n_release_status.py --date ...`
   retorna `published=true` (recibo + hash + feed + commit válidos). Nunca declare
   sucesso sem recibo.

## 5. Fluxo diário esperado

- **04:00** job principal: coleta → roteiro → **GateDurance → Loop → autocorrect**
  → TTS → gates finais → deploy → recibo.
- **05:00** deploy do site (no_agent).
- **06:00–21:00 (a cada 2h)** job de recuperação: se ainda não publicado, regenera
  e re-tenta o ciclo.
- **A cada 2h** **watchdog**: observa, autocorrige quando possível, sinaliza o que
  precisa LLM. Silencioso quando o episódio do dia já foi publicado.

## 6. Verificação / testes conhecidos

| Cenário | Resultado esperado |
|---------|--------------------|
| Roteiro bom (05/08) | GateDurance exit 0, Loop exit 0 (aprova direto) |
| Roteiro com `(hum...)` | GateDurance bloqueia; autocorrect remove |
| Roteiro com `1 (um)` | GateDurance bloqueia; autocorrect → `1` |
| Roteiro em inglês | GateDurance bloqueia (não-traduzido); autocorrect não resolve → LLM |
| Roteiro <850 palavras | GateDurance bloqueia; autocorrect não inventa → LLM |
| Falta seção essencial | GateDurance bloqueia (estrutura) |
| Já publicado | Watchdog silencioso (exit 0) |

## 7. Arquivos

- `scripts/d5n-gatedurance-script-gate.py` — validador
- `scripts/d5n-gatedurance-autocorrect.py` — auto-correção determinística
- `scripts/d5n-gatedurance-loop.sh` — orquestrador
- `scripts/d5n-gatedurance-watchdog.sh` — observador
- `/root/.hermes/scripts/d5n-gatedurance-watchdog.sh` — wrapper no_agent (cron)
- `/root/.hermes/profiles/d5n/cron/jobs.json` — regras no CONTRATO dos jobs D5N
- `podcast-scripts/<data>.json` — snapshots dos roteiros aprovados/publicados
