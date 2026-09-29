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

**9. A apresentadora anunciava dia e mês em inglês.** O intro usava `strftime('%A, %d de %B de %Y')`, que segue o locale do processo. No cron o locale é `C`, então a saída era "Thursday, 28 de May of 2026" em um podcast inteiro em português. Pior, `date.today()` roda no fuso do sistema (`America/Manaus`), que perto da meia-noite pode cair no dia errado para o conteúdo editorial.

**10. Cadastro nos diretórios externos nunca foi feito por código.** Apple e Spotify exigem submissão/claim inicial. A documentação do Spotify diz que episódios novos costumam aparecer em algumas horas, podendo levar até 24; a Apple costuma refletir mudanças em algumas horas.

**11. `podcast:chapters` apontava para o `.mp3`, que não tem capítulos embutidos.** O padrão Podcasting 2.0 só resolve chapters quando o áudio traz os atoms ID3 `CHAP`/`ctoc`. Nenhum dos três mixers os escreve — verificado nos MP3 de D5N e FM: `CHAP`, `ctoc` e `cmark` ausentes. O `src` apontava para o enclosure, que não resolve em nenhum player.

**12. `podcast:chapters` com filhos derrubava o feed inteiro.** O elemento é vazio por definição quando o `src` é um documento externo; filhos só existem quando o `src` é o próprio áudio com atoms ID3. O gerador emitia `psrc:chapter` (D5N) e `psc:chapters` aninhado (MC e FM) — mistura de namespaces que leitor estrito rejeita, e o sintoma é o **feed inteiro parando de carregar**, não apenas os capítulos sumindo. Confirmado no leitor do usuário.

**13. `psc:chapter` sem `start` não navega.** O Podlove Simple Chapters exige `start`; `title` sozinho não é definição válida. O D5N emitia 104 tags só com rótulo, porque o `coldopen.txt` não tem tempos e o gerador usava `has_timing=False`. Os tempos existiam em `chapters/<data>.json` (11 blocos medidos do MP3, com `start`/`end` exatos) mas sem os rótulos, que vêm da derivação sobre o coldopen.

**14. Manhã Conectada nunca teve capítulos em nenhum commit do histórico.** `_shared_chapters.py` já tinha `MC_CHAPTER_LABELS` prontos e sem uso; `gerar_manha_conectada_feed.py` nunca implementou. Além disso faltava declarar `xmlns:psc` no canal — sem ele o feed fica inválido.

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

## Capítulos nos três programas

Corrigido em 29/09/2026, depois de o usuário reportar que o podcast parou de carregar no leitor.

- `_shared_chapters.py`: `chapters_from_manifest()` casa os timings reais do manifesto do mixer (só `id`, `start`, `end`) com os rótulos da derivação sobre o coldopen. Casa por posição quando as quantidades batem; quando não batem, mantém a derivação em vez de inventar capítulo.
- `podcast:chapters` passou a ser elemento vazio com `src` apontando para o JSON de capítulos (`chapters/<data>.json`, `manha-conectada/chapters/`, `fechamento/chapters/`), nunca para o `.mp3`.
- `psc:chapters` (Podlove) carrega os capítulos inline, todos com `start` e `title`. O D5N deixou de usar `has_timing=False`.
- MC ganhou chapters: `_calc_mc_chapters()` com os 8 blocos editoriais fixos. A contagem de fontes não entra — antes truncava em 5 capítulos e perdia "Sinal 11" e "Encerramento".
- FM passou a gravar `fechamento/chapters/<data>.json` (13 arquivos).
- `xmlns:psc` declarado no canal do MC, que não tinha.

Resultado medido no ar: D5N 104 capítulos, MC 248, FM 78, todos com `start`, nenhum `podcast:chapters` com filho.

### Contratos de capítulo no portão

`tests/test_chapters_rss_contracts.py` (novo, 4 testes) reprova: `podcast:chapters` com filho, `psc:chapter` sem `start` ou sem `title`, capítulos fora de ordem dentro do item, e `src` em `.mp3` ou fora de JSON. Verificado que pegam a regressão: reintroduzidos os dois defeitos, os testes falham.

A lição que motivou o teste: parse XML e presença da tag não são contrato de podcast. Os defeitos 12 e 13 passaram pela validação anterior porque ela só checava se o feed parseava e se a tag existia — e ambos reprovam no leitor. O sintoma era o feed inteiro parando de carregar, não os capítulos sumindo.

## Portão de qualidade no pipeline

- Passo 10 de `d5n-podcast-daily-full.sh`: roda `scripts/validar_design.py` e a suíte de testes entre gerar o index e commitar. Reprovar aborta com `exit 1` e **zero commits** — fail-closed.
- Verificado nos dois sentidos: gerador emitindo CSS inválido reprova e cancela a publicação; gerador íntegro publica e o feed público responde OK.
- Armadilha registrada: sabotar o `index.html` em disco não prova nada, porque o passo 9 regenera o index antes do passo 10 e o CSS quebrado some. O que reprova de verdade é o gerador emitir CSS inválido.
- `.github/quality.yml` foi descartado. Seria uma segunda cópia do mesmo portão em outra máquina, exigindo token com escopo `workflow` que o token OAuth não tem.

## Mixagem: divergência entre os três programas

**Ainda não corrigido — é o maior item em aberto.** Medido com `ffmpeg loudnorm` nos últimos episódios:

| | D5N | MC | FM |
|---|---|---|---|
| Loudness integrado | -16,3 LUFS | -17,4 | -17,9 |
| True peak | -1,7 dB | -1,7 | -1,7 |
| LRA | 2,1–2,4 | 1,8–2,1 | 2,9–3,0 |

Causa: três mixers independentes. `drop5news-mixer-v10.py` usa `HIGH_LUF = -16` e cadeia própria (fade por seção, `VOICE_TARGET_DBFS`, gain por trilha). `amanha_conectada_mixer.py` e `fechamento_mixer.py` são quase o mesmo script, com `loudnorm=I=-17` hardcoded. O FM ainda resolve `INTRO` e `BED` pelo diretório de assets do MC, como fallback — está pegando áudio do outro programa.

Variação de ~1,6 LU entre programas, audível fora de player que normalize. O caminho é um módulo único de loudness e cabeçalho, consumido pelos três mixers, com teste de contrato que reprova se divergir mais que 0,3 LU.

## Datas em português e fuso editorial

- `scripts/d5n_data_ptbr.py` (novo): tabelas de dia da semana e mês em PT-BR, sem depender do locale do sistema. Expõe `data_extenso`, `data_extenso_curta`, `data_curta`, `sigla_mes` e `hoje_editorial` (fuso `America/Sao_Paulo`).
- `scripts/gerar_roteiro_d5n.py` usa o helper no intro e passa a derivar a data do fuso editorial em vez de `date.today()`.
- `gerar_cards_pipeline.py` e `gerar_cards_instagram_d5n.py` tinham fallback em inglês quando não achavam a data no conteúdo; agora usam o mesmo helper.
- `tests/test_d5n_data_ptbr.py` (novo): 8 testes cobrindo PT-BR, independência de locale, os sete dias da semana, fuso, e uma guarda anti-regressão que falha se `%A`/`%B` voltarem ao roteiro.

Verificado: o intro gerado agora diz "terça-feira, 29 de setembro de 2026" e o TTS de `pt-BR-FranciscaNeural` sintetiza o trecho sem nomes em inglês.

## Publicação

Commits `fd6a13b`, `57c65eb` e `87ecb27` no `master` e no `origin/master`. Após o push, o verificador público rodou contra o episódio #075 e passou em todas as checagens, confirmando que o deploy do Netlify propagou.

## Pendente: depende de acesso às contas

- Confirmar em Apple Podcasts Connect e Spotify for Creators qual URL RSS está cadastrada para Hoje no Drop Five News. O canônico é `https://d5n-daily.netlify.app/podcast.xml`. Se algum cadastro apontar para `d5n-feed.xml` (feed de notícias, sem áudio) ou para uma URL antiga, corrigir.
- Se houve migração de feed, aplicar o procedimento oficial de redirecionamento/aviso de feed novo.
- Fazer a submissão/claim inicial onde o programa ainda não estiver cadastrado.
- Registrar plataforma, URL do programa, URL RSS cadastrada, estado de aprovação e data da última atualização. Não armazenar credenciais no repositório.

## Em aberto (não depende de conta)

**1. Mixagem desigual entre os três programas.** Detalhado acima. É o maior item: enquanto não for corrigido, os três não têm a mesma edição. Requisito do usuário: mixagem similar, variação só de trilha de fundo.

**2. 59 dos 64 capítulos antigos do D5N continuam com 1 capítulo.** O conserto vale a partir do #075. Para trás exigiria reprocessar todos os MP3, porque os tempos só existem no manifesto do dia.

**3. Roteiros do D5N não são gerados desde 31/08.** O cron das 04h falhava por falta de manifest; o wrapper ganhou a etapa de roteiro no dia 29/09. O próximo ciclo precisa ser observado para confirmar que sustenta.

**4. `HTTP 401` da auditoria semanal.** Não investigado.

**5. Git LFS.** O repositório tem 1,7 GB de MP3 versionados como arquivo comum.

**6. Três programas num repositório só.** Separação em repos próprios é discutível e não foi feita.

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
