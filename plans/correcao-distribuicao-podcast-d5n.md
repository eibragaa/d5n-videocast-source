# Plano de correção definitiva — distribuição do podcast D5N

**Implementado em:** 29/09/2026
**Escopo:** geração/publicação do RSS e ingestão por diretórios externos (Apple Podcasts, Spotify e outros).

## Diagnóstico verificado

### O feed público está atualizado

- `https://d5n-daily.netlify.app/podcast.xml` responde HTTP 200 com 61 episódios; o primeiro é o #075, de 29/09/2026.
- O enclosure do #075 responde HTTP 200 como `audio/mpeg`, com 11.579.602 bytes.
- `scripts/validate_feeds.py --feed D5N` passa: 61/61 enclosures válidos.

Isso descarta falha atual de geração/publicação do feed. Não prova que os diretórios externos estejam inscritos no feed correto.

### Causas raiz encontradas

**1. O cron não tinha as dependências do pipeline.** O agendador Hermes executa scripts `.py` com o interpretador do próprio gateway — hoje um runtime gerenciado do Hermes (Python 3.14.7) que não tem `pydub`, `edge_tts` nem `feedparser`. Não há como mudar isso na configuração do job. Resultado: o wrapper das 04h falhava todo dia em `ModuleNotFoundError`, e o coletor de trends falhava em `ModuleNotFoundError: feedparser`.

**2. Erros eram mascarados como sucesso.** Em `scripts/d5n-podcast-daily-full.sh`, falha de síntese, geração de feeds, página e `git push` viravam avisos, e o script podia terminar com código zero. Um `git add -A` sem staging seletivo subia arquivos de outros pipelines.

**3. Não havia idempotência por data.** A etapa que calcula o número do episódio fazia sempre `last_episode + 1`, criando um segundo episódio para a mesma data (o #076 para 29/09, quando o #075 já estava publicado).

**4. O coletor de trends nunca emitiu os quatro pilares.** `deploy_d5n_site.sh:76` exige `GLOBAL BRASIL TECH ECONOMIA` no arquivo do dia, mas `d5n-trends-diario.py` escrevia as manchetes agrupadas por fonte, sem esses marcadores. Nenhum arquivo já gerado passou nesse gate.

**5. Não havia confirmação de publicação.** Nada verificava, depois do push, se o feed e o áudio estavam de fato públicos. Um deploy verde no git pode deixar o feed público desatualizado — exatamente o descompasso que impede os diretórios externos de receber o episódio.

**6. Jobs duplicados e um inválido.** Três jobs disputavam a produção diária; um apontava para um script bloqueado por estar fora do diretório permitido.

**7. O guard de design apontava para o gerador errado.** `scripts/validar_design.py` validava `scripts/gerar_pagina_d5n.py` (layout v2, obsoleto desde ago/2026), enquanto o pipeline executa `gerar_pagina_d5n.py` na raiz. O guard exigia tokens e marcadores que o gerador real nunca emite, bloqueando todo commit com 34 falso-positivos. Pior: exigia um `grid-template-areas` cujo teste provou que o CSS do site estava sendo descartado.

**8. O gerador em uso tinha um bloco CSS órfão.** Uma edição corrompida duplicou o bloco `.filter-btn` e deixou uma declaração órfã, fazendo o browser descartar todas as regras seguintes. Além disso, `--brand-cyan` e `--chapter-weight` eram consumidos por `var()` sem nunca serem declarados, e `--muted` (#64748b) ficava em 3.98:1 sobre o fundo, abaixo de WCAG AA.

**9. Cadastro nos diretórios externos nunca foi feito por código.** Apple e Spotify exigem submissão/claim inicial. A documentação do Spotify diz que episódios novos costumam aparecer em algumas horas, podendo levar até 24; a Apple costuma refletir mudanças em algumas horas.

## Correções aplicadas

### Ambiente de execução
- `requirements-d5n.txt` (novo) fixa as dependências, com nota de que o cron deve usar o venv D5N.
- Instalei no venv `/root/venv-d5n-audio`: `pydub 0.25.1`, `edge-tts 7.2.7`, `feedparser 6.0.14`, `audioop-lts 0.2.2` (o `audioop` foi removido do Python 3.13 e o pydub depende dele), `PyYAML 6.0.3`.
- `d5n-trends-diario.py` passou a importar as dependências com fallback para o site-packages do venv, funcionando em qualquer interpretador.

### Pipeline fail-closed
- `d5n-podcast-daily-full.sh` fixa `D5N_PY=/root/venv-d5n-audio/bin/python3`, valida os três imports antes de gerar qualquer artefato, e usa esse interpretador em todas as etapas.
- Roteiro, TTS, mixer, feeds, index e push agora são bloqueantes; só o commit sem alterações staged é tolerado.
- `git add -A` substituído por staging seletivo dos arquivos da release.
- Idempotência por data: reutiliza o episódio existente da data em vez de incrementar o contador, e atualiza a entrada existente em vez de duplicar.

### Verificação de publicação
- `scripts/d5n_public_feed_check.py` (novo) busca o feed público e confere HTTP 200, XML, `atom:link rel="self"`, `lastBuildDate`, GUID exato `d5n-{data}-ep{NNN}` com `isPermaLink="false"`, `pubDate` RFC 822 e enclosure HTTPS `audio/mpeg` com tamanho coerente. Tenta novamente com backoff antes de falhar.
- `tests/test_d5n_public_feed_check.py` (novo) cobre feed íntegro, GUID ausente, data inválida, enclosure errado, retry em 404 e tamanho divergente. Sete testes, todos offline.

### Feed e gerador
- `gerar_pagina_d5n.py` passa a conferir o código de retorno do gerador do podcast e encerra com erro se ele falhar.
- `scripts/d5n-tts-synthesize.py` informa qual interpretador está em uso e o comando correto de instalação.

### Coletor de trends
- `d5n-trends-diario.py` agrupa as manchetes pelos quatro pilares que o gate exige, e falha se algum ficar sem notícias.

### Site e guard de design
- `gerar_pagina_d5n.py`: removido o bloco CSS órfão que descartava as regras seguintes; declarados `--brand-cyan` (#67e8f9) e `--chapter-weight`; `--muted` passou de #64748b (3.98:1) para #8a99ad (6.53:1), atendendo WCAG AA.
- `scripts/validar_design.py`: passou a validar o gerador da raiz (o que o pipeline usa), a ler todos os blocos `:root` em vez do primeiro, e a derivar os tokens esperados do próprio design system — mantendo o poder de detectar token que sumiu, sem lista fixa que envelhece a cada redesign. O arquivo legado `scripts/gerar_pagina_d5n.py` só é verificado quanto a lixo injetado.
- Verificado que o guard ainda detecta os três modos de falha reais: comentário CSS quebrado, token usado sem declaração e contraste abaixo de 4.5:1.

### Jobs
- `d5n-podcast-diario-fixed` pausado (script inválido, sempre bloqueado).
- `d5n-podcast-daily-wrapper` corrigido para o caminho relativo aceito pelo agendador.
- `d5n-trends-diario` mantém o script e agora executa com sucesso.

## Publicação

Commit `fd6a13b` no `master` e no `origin/master`. Após o push, o verificador público rodou contra o episódio #075 e passou em todas as checagens, confirmando que o deploy do Netlify propagou.

## Pendente: depende de acesso às contas

- Confirmar em Apple Podcasts Connect e Spotify for Creators qual URL RSS está cadastrada para Hoje no Drop Five News. O canônico é `https://d5n-daily.netlify.app/podcast.xml`. Se algum cadastro apontar para `d5n-feed.xml` (feed de notícias, sem áudio) ou para uma URL antiga, corrigir.
- Se houve migração de feed, aplicar o procedimento oficial de redirecionamento/aviso de feed novo.
- Fazer a submissão/claim inicial onde o programa ainda não estiver cadastrado.
- Registrar plataforma, URL do programa, URL RSS cadastrada, estado de aprovação e data da última atualização. Não armazenar credenciais no repositório.

## Critérios de aceite

- Existe um único caminho de produção, com dependências verificadas e sem depender de execução manual.
- Duas execuções para a mesma data não criam episódios duplicados nem pulam números.
- Falha antes ou depois do push deixa o job em estado de erro; não há sucesso com feed desatualizado.
- O pós-deploy comprova que o primeiro item público é o episódio esperado e que o enclosure responde com o tamanho correto.
- Os dois estados são reportados separadamente: **RSS publicado** (verificável pelo servidor) e **plataformas externas atualizadas** (depende do crawl de cada diretório).

## Referências oficiais

- Apple — [RSS feed refresh](https://podcasters.apple.com/support/838-refresh-a-podcast)
- Apple — [Submit a new show](https://podcasters.apple.com/support/897-submit-a-show)
- Spotify — [Distributing your show to other platforms](https://support.spotify.com/us/creators/article/distributing-your-show-to-other-platforms/)
