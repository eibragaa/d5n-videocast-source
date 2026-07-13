# Plano de Correção — Pipeline D5N (Drop Five News)

**Data:** 2026-07-12 (Domingo)
**Objetivo:** Documentar e formalizar as correções aplicadas no pipeline D5N que causavam data errada ("sábado" em vez de "domingo") e voz errada ("Marina" inexistente) nos áudios gerados.

---

## Sprint 1 — SKILL.md: Remover referências a "Marina"

**Status:** ✅ Concluído
**Arquivos alterados:**
- `/root/.hermes/skills/media/trends-podcast/SKILL.md`
- `/root/.hermes/profiles/d5n/skills/media/trends-podcast/SKILL.md`

**Correções:**
1. Session date: "Talita + Marina (dual)" → "Thalita + Francisca (dual)"
2. Modelos de abertura (linhas 86-88): "Marina" → "Thalita", "Talita" → "Francisca"
3. Tabela de vozes (linhas 447-456): 10 referências a "Marina" → "Thalita/Francisca (por dia)"
4. `get_voices()` descrição (linha 555): "Marina notícias, Talita intro" → "Thalita notícias, Francisca intro"
5. Referências a "intro/CTA/mensagem/outro" → "intro/CTA/ofertas/outro"

**Total:** 16 correções em 2 arquivos SKILL.md

---

## Sprint 2 — split_roteiro.py: Código morto removido

**Status:** ✅ Concluído
**Arquivo movido:**
- `/root/.hermes/scripts/split_roteiro.py` → `/root/.hermes/scripts/_deprecated/split_roteiro.py`

**Justificativa:** Zero referências em pipelines ativos. `gerar_pagina_d5n.py` usa "###" e "---" como separadores, não "════".

---

## Sprint 3 — Alinhar gerar-secoes-v2.py com mixer v9

**Status:** ✅ Concluído
**Arquivos alterados:**
- Mixer v9 (scripts + template, default + d5n profile)
- SKILL.md (d5n profile): tabela de seções atualizada

**Correções:**
1. Adicionado "frase" e "historia" no array SECOES (11 → 13 blocos)
2. Adicionado na lista de regeração TTS e dual_sections
3. Atualizada tabela no SKILL.md (13 blocos)

---

## Sprint 4 — Amanhã Conectada: Hook com dia errado

**Status:** ✅ Concluído
**Arquivos alterados:**
- `scripts/amanha-conectada-pipeline.sh`
- `source-amanha-2026-07-11.md`

**Correções:**
1. Pipeline calcula WEEKDAY_PT via Python e injeta no prompt
2. Hook corrigido: "Sábado começou quente" → "Sexta começou quente"

---

## Sprint 5 — Teste End-to-End

**Status:** ✅ Concluído

- 24/24 checks ad-hoc passaram
- Mixer v9 rodou completo: 13 blocos, voz FranciscaNeural, 6.4 min
- intro.txt: "Aqui é Francisca... Hoje é domingo, 12 de julho de 2026"
- Output: /tmp/d5n_mixado_v9.mp3 (9047 KB)

---

## Tabela de Bugs Corrigidos

| # | Bug | Severidade | Root Cause |
|:-:|-----|:----------:|------------|
| 1 | d5n-inject-date.py: path inexistente | CRÍTICO | os.popen() retornava vazio, json.loads("") falhava |
| 2 | source.md stale em /tmp/d5n_audio/ | CRÍTICO | Mixer lê .txt do disco; se .txt tem "sábado", áudio sai errado |
| 3 | pipeline_selecao.py: KeyError GLOBAL | CRÍTICO | Dict só tinha MUNDO; append para GLOBAL quebrava |
| 4 | Mixer v9: nomes marina/talita | ALTO | Variáveis apontavam para vozes erradas |
| 5 | Mixer v9: mensagem vs ofertas | CRÍTICO | dual_sections e regenação TTS usavam mensagem, SECOES tem ofertas |
| 6 | Validador inject-date: falso positivo | MÉDIO | Substring search por sábado em qualquer .txt pegava notícias |
| 7 | intro.txt: Aqui é Marina | ALTO | Nome Marina não existe no persona system |
| 8 | SKILL.md: 16 refs a Marina/Talita | MÉDIO | Documentação desatualizada |
| 9 | split_roteiro.py: código morto | BAIXO | Script não referenciado |
| 10 | gerar-secoes-v2.py: frase/historia ignorados | MÉDIO | Gerador criava arquivos não processados |
| 11 | Amanhã Conectada: hook dia errado | MÉDIO | LLM não recebia dia da semana |