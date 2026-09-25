# PROPOSTA V4 — Roteiro D5N estilo Amanda Flaury (para avaliação)

Status: PROPOSTA — não aplicado. Backup do estado atual em:
- backups/d5n-podcast-cron-prompt.txt.v3.ATUAL.bak
- git tag: rollback-cron-prompt-v3-20260925-071433

Data: 2026-09-25. Autor: Jean + Hermes.

---

## Problemas diagnosticados no roteiro atual (2026-09-25)

1. INTRO com data em INGLÊS: "hoje é Friday, 25 de September de 2026"
   — strftime('%A, %d de %B') com locale C. Deve ser "sexta-feira, 25 de setembro".
2. INTRO hardcoda "Eu sou Francisca" — ignora a escala de vozes do mixer v10
   (seg/qua/sáb = Thalita; ter/qui = Francisca; sex = dual). A voz do áudio
   muda pelo mixer, mas o roteiro sempre diz Francisca.
3. TODAS as seções de notícia abrem com template fixo:
   - mundo: "No cenário global, as bolsas internacionais operam com cautela..."
   - brasil: "No Brasil, o foco da quinta-feira, ... reúne a agenda econômica..."
   - tecnologia: "Em tecnologia, os avanços em inteligência artificial generativa..."
   - economia: "Na economia, o mercado financeiro reflete o bom momento..."
   → mesmo episódio, mesma abertura, todo dia. É "leitura de portal".
4. Corpo = lista de "Título, segundo Fonte." sem gancho → contexto → efeito prático.
5. coldopen.txt começa com "2026-09-25." (data) em vez de manchetes-tiro no 1º segundo.
6. interacao.txt é CTA de Instagram/Telegram — o contrato manda ser pergunta
   espontânea ligada ao assunto do dia, sem anunciar seção.
7. outro.txt NÃO contém o CTA obrigatório do RSS Manhã Conectada ("manhã conectada",
   "rss próprio", "aplicativo de podcast", "site do drop five news") — contrato v3
   exige esses termos; o outro atual apenas menciona o programa sem o CTA.

## Mudanças propostas

### A. gerar_roteiro_d5n.py (gerador de manifests)

1. **Data em português**: usar array fixo de meses/dias em pt-BR
   ("sexta-feira, 25 de setembro de 2026"), nunca strftime %A/%B.
2. **Apresentadora pela escala do mixer**: dia da semana → nome certo
   (seg/qua/sáb Thalita, ter/qui Francisca, sex alterna pela primeira seção).
   intro.txt usa o nome REAL da voz daquele dia.
3. **Aberturas variadas por dia** (pool de aberturas rotativas, baseadas no dia da
   semana): substituir os templates fixos de mundo/brasil/tecnologia/economia por
   gancho → contexto → consequência para quem ouve, variando a frase de abertura.
4. **coldopen**: 3-4 manchetes-tiro curtas e fortes no primeiro segundo, SEM data
   no início (a manchete mais forte abre). Formato Amanda: consequência primeiro.
5. **interacao**: pergunta real ligada ao assunto mais forte do dia, sem CTA.
6. **outro**: CTA do RSS Manhã Conectada (4 termos obrigatórios) + lembrete +
   bordão de despedida, variado.
7. **frase.txt**: frase real com autoria (Pensador) — não texto genérico
   "Quem não evolui, é ultrapassado" sem atribuição.
8. **historia**: fato histórico VERIFICÁVEL da data (omitir se não houver).
9. **recomendacoes**: 1-2 filmes/séries reais com ano (verificar IMDB), não
   "recomendamos acompanhar as notícias do G1".

### B. config/d5n-podcast-cron-prompt.txt (contrato do roteiro)

- Reescrever a seção ARQUITETURA DO ROTEIRO com os 11 pontos Amanda Flaury
  (cold open manchetes-tiro, auto-apresentação com nome real, gancho → detalhe →
  efeito prático, transições vivas, engajamento no meio, frase com autoria,
  CTA + bordão variado no fechamento).
- Reforçar: datas sempre em português; nunca "No cenário global..." como abertura;
  variar abertura/transições/fechamento diariamente (comparar com snapshots).
- Manter contratos técnicos intactos: seções, durações, gates, deploy.

### C. Headers e alternância (já existentes no mixer v10 — NÃO mudar)

- Headers falados (voz Antonio): mundo/brasil/tecnologia/economia/ofertas/frase/
  recomendacoes/historia anunciam o bloco; interacao propositalmente sem header.
- Escala de vozes: seg/qua/sáb Thalita; ter/qui Francisca; sex dual; dom manutenção.
- O gerador de roteiro deve REFLETIR isso no texto (nome da apresentadora), não
  criar headers novos.

## Fora de escopo (não mexer)

- drop5news-mixer-v10.py, gates, deploy_d5n_site.sh, gerar_pagina_d5n.py,
  feeds, podcast.xml, index.html, contador de episódios.