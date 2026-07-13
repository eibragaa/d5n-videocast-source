# Plano de Correção — Pipeline D5N (Drop Five News)

**Data:** 2026-07-12 (Domingo)
**Objetivo:** Corrigir bugs que causavam data errada ("sábado" em vez de "domingo") e voz errada ("Marina" inexistente) nos áudios gerados pelo pipeline D5N.

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

**Total:** 16 correções em 2 arquivos SKILL.md (default + d5n profile)

---

## Sprint 2 — split_roteiro.py: Código morto removido

**Status:** ✅ Concluído
**Arquivo movido:**
- `/root/.hermes/scripts/split_roteiro.py` → `/root/.hermes/scripts/_deprecated/split_roteiro.py`

**Justificativa:** Script dividia roteiros por "════" mas nenhum pipeline ativo o referencia. `gerar_pagina_d5n.py` usa "###" e "---" como separadores. Zero referências encontradas em scripts, skills, crontab ou scheduler.db.

---

## Sprint 3 — Alinhar gerar-secoes-v2.py com mixer v9

**Status:** ✅ Concluído
**Arquivos alterados:**
- `/root/.hermes/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py`
- `/root/.hermes/skills/media/trends-podcast/templates/drop5news-mixer-v9.py`
- `/root/.hermes/profiles/d5n/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py`
- `/root/.hermes/profiles/d5n/skills/media/trends-podcast/templates/drop5news-mixer-v9.py`
- `/root/.hermes/profiles/d5n/skills/media/trends-podcast/SKILL.md` (tabela de seções)

**Correções:**
1. Adicionado "frase" e "historia" no array SECOES (11 → 13 blocos)
2. Adicionado "frase" e "historia" na lista de regeneração TTS
3. Adicionado "frase" e "historia" no dual_sections
4. Atualizada tabela de seções no SKILL.md (13 blocos)
5. Atualizada nota: "frase e historia AGORA estão no SECOES"

**Antes:** `gerar-secoes-v2.py` gerava `frase.txt` e `historia.txt` mas o mixer ignorava.
**Depois:** Mixer processa 13 blocos incluindo frase e historia.

---

## Sprint 4 — Amanhã Conectada: Hook com dia errado

**Status:** ✅ Concluído
**Arquivos alterados:**
- `/root/repositorio/d5n-videocast-source/scripts/amanha-conectada-pipeline.sh`
- `/root/repositorio/d5n-videocast-source/source-amanha-2026-07-11.md`

**Correções:**
1. Pipeline agora calcula `WEEKDAY_PT` via Python e injeta no prompt do LLM
2. Hook do arquivo 2026-07-11 corrigido: "Sábado começou quente" → "Sexta começou quente"

**Antes:** LLM recebia `DATE=2026-07-11` mas não o dia da semana. Adivinhava "Sábado" para uma sexta-feira.
**Depois:** LLM recebe `WEEKDAY=Sexta-feira` explicitamente no prompt.

---

## Sprint 5 — Teste End-to-End

**Status:** ✅ Concluído

**Verificação ad-hoc (24 checks):**
- Compilação: 4 scripts Python + 1 template (py_compile) ✓
- Sintaxe bash: drop5news-mixer-exec.sh + amanha-conectada-pipeline.sh ✓
- d5n-date-context.py retorna "domingo" para 2026-07-12 ✓
- d5n-inject-date.py usa caminho relativo ✓
- inject-date corrige "sábado, 11" → "domingo, 12" ✓
- inject-date não gera falso positivo em "neste sábado" ✓
- pipeline_selecao.py roda sem KeyError ✓
- mixer v9 usa "ofertas" (não "mensagem") ✓
- mixer-exec.sh sincroniza source.md + inject-date ✓
- Perfis: default + d5n sincronizados ✓

**Teste E2E do mixer v9:**
- 13 blocos processados (incluindo frase e historia)
- Voz: FranciscaNeural (domingo = Francisca) ✓
- intro.txt: "Aqui é Francisca... Hoje é domingo, 12 de julho de 2026" ✓
- Duração: 385.9s (6.4 min) ✓
- Output: `/tmp/d5n_mixado_v9.mp3` (9047 KB) ✓

---

## Bugs Corrigidos (Resumo)

| # | Bug | Severidade | Root Cause |
|:-:|-----|:----------:|------------|
| 1 | d5n-inject-date.py chamava date-context em path inexistente | CRÍTICO | `os.popen()` retornava string vazia, `json.loads("")` falhava, data nunca injetada |
| 2 | source.md stale em /tmp/d5n_audio/ | CRÍTICO | Mixer regenera TTS lendo .txt do disco; se .txt tem "sábado", áudio sai "sábado" |
| 3 | pipeline_selecao.py KeyError em PILARES["GLOBAL"] | CRÍTICO | Dict só tinha "MUNDO"; append para "GLOBAL" quebrava |
| 4 | Mixer v9: nomes marina/talita | ALTO | Variáveis apontavam para vozes erradas (marina=Thalita, talita=Francisca) |
| 5 | Mixer v9: "mensagem" vs "ofertas" | CRÍTICO | dual_sections e regenação TTS usavam "mensagem" mas SECOES tem "ofertas" |
| 6 | Validador inject-date: falso positivo | MÉDIO | Substring search por "sábado" em qualquer .txt pegava notícias |
| 7 | intro.txt: "Aqui é Marina" | ALTO | Nome "Marina" não existe no persona system |
| 8 | SKILL.md: 16 refs a "Marina/Talita" | MÉDIO | Documentação desatualizada com nomes errados |
| 9 | split_roteiro.py: código morto | BAIXO | Script não referenciado em nenhum pipeline ativo |
| 10 | gerar-secoes-v2.py: frase/historia ignorados | MÉDIO | Gerador criava arquivos que o mixer não processava |
| 11 | Amanhã Conectada: hook com dia errado | MÉDIO | LLM não recebia dia da semana no prompt |

---

## Incongruências Não-Corrigidas (Baixa Prioridade)

1. **SKILL.md linha 467:** Ainda diz `Apresentador: "Aqui é Jean Braga..."` — mas o persona system usa Thalita/Francisca. Provavelmente um remanescente de versão anterior onde o apresentador era Jean.
2. **SKILL.md descrição frontmatter:** Referências a `references/mixer-v9-section-mismatch.md` e `references/mixer-v9-secoes-fix.md` ainda marcadas como desatualizadas — precisam ser atualizadas para refletir 13 seções.
3. **gerar_pagina_d5n.py** ainda referencia "Marina" na função `gerar_source_md` — precisa ser verificado se isso afeta a geração do source.md.