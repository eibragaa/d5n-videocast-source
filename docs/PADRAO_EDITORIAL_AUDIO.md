# Padrão editorial e de áudio — Drop Five News

Vigência: 18 de julho de 2026.

## Publicação

- O podcast é produzido de **segunda a sábado**.
- **Domingo não tem episódio**: é reservado para manutenção de TTS, mixer e pipeline.
- O nome editorial e falado é sempre **Drop Five News**.
- A data editorial usa `America/Sao_Paulo` e deve ser narrada em português brasileiro.
- Reprocessamentos históricos devem definir `D5N_EDITORIAL_DATE=AAAA-MM-DD`.

## Roteiro

1. Todo texto falado deve estar em português brasileiro.
2. Não narrar emoji, markdown, URL, nome de arquivo ou instrução técnica.
3. CTA e despedida aparecem somente no encerramento geral.
4. Não usar Voz da Comunidade, comentário simulado, audiência inventada ou micro-momento sussurrado.
5. Não inventar fatos, fontes, organizações, números, percentuais ou curiosidades.
6. Killpoints editoriais são opcionais e exigem sustentação factual:
   - Conexão Brasil;
   - cenário “E se?” claramente identificado como hipótese;
   - Antes e Depois;
   - Aposta do Dia claramente identificada como leitura editorial;
   - curiosidade contextual;
   - contraponto responsável;
   - silêncio intencional em tema sensível;
   - assinatura sonora.
7. A substring `cinto`, sem diferenciar maiúsculas e minúsculas, é proibida em qualquer roteiro, template ou frase selecionada.

## Mensagem do Dia

- Origem preferencial: frase real coletada do Pensador.com.
- A seleção usa `SystemRandom` entre várias candidatas elegíveis.
- O histórico persistente guarda até 90 frases e bloqueia repetição recente.
- A blocklist é aplicada antes da escolha e após a gravação.
- Fallbacks editoriais também participam do histórico.
- O arquivo ativo é validado antes do TTS.

## Vozes e síntese

A produção usa exclusivamente **Edge TTS local**:

| Regra editorial | Voz |
|---|---|
| Segunda, quarta e sábado | Thalita — `pt-BR-ThalitaMultilingualNeural` |
| Terça e quinta | Francisca — `pt-BR-FranciscaNeural` |
| Sexta-feira especial | Francisca e Thalita, alternadas a cada bloco disponível |
| Headers de seção | Antonio — `pt-BR-AntonioNeural` |
| Domingo | Sem episódio; manutenção |

A escolha é calculada pela **data editorial** (`D5N_EDITORIAL_DATE`) em `America/Sao_Paulo`, nunca pelo dia em que um reprocessamento é executado. Na sexta-feira, o manifesto registra `presentation_mode: sexta-dual-dinamica`, as duas vozes e o mapa de voz por seção. Gemini TTS é legado e não deve ser usado.

## Mixer v9

Cópias sincronizadas:

- `~/.hermes/profiles/d5n/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py`
- `~/.hermes/profiles/d5n/skills/media/trends-podcast/templates/drop5news-mixer-v9.py`

Requisitos:

- preservar a ordem real das seções mesmo quando blocos opcionais estiverem ausentes;
- usar o nome carregado junto ao bloco, sem inferir por índice;
- trilha abaixo da narração, com fades e transições;
- saída mono, 44,1 kHz, MP3 192 kbps;
- normalização final com alvo de **−16 LUFS** e true peak de **−1,5 dBTP**;
- gravar `/tmp/d5n_audio/manifest.json` com provedor, vozes, seções e alvos de áudio.

## Gates bloqueantes

Antes do TTS:

```bash
D5N_EDITORIAL_DATE=AAAA-MM-DD python3 /root/.hermes/scripts/d5n-pre-gen-gate.py
python3 /root/.hermes/scripts/d5n-mensagem-validate.py
```

Após a mixagem:

```bash
cd /root/repositorio/d5n-videocast-source
python3 scripts/d5n-podcast-quality-gate.py
```

O gate final bloqueia publicação quando houver:

- texto falado fora do padrão editorial;
- nome incorreto do programa;
- substring proibida;
- data em inglês;
- emoji, markdown ou URL em segmento falado;
- CTA ou despedida intermediária;
- manifesto ausente ou vozes divergentes;
- MP3 ausente, corrompido, curto, longo ou com bitrate insuficiente;
- sample rate/canais divergentes;
- loudness fora de −16 ±1 LUFS;
- true peak acima de −1 dBTP.

## Babysitter

`babysitter.yaml` executa o gate final como verificação crítica. Qualquer falha editorial, de voz ou de mixagem impede a publicação. Problemas históricos de contador e arquivos ausentes continuam reportados separadamente e não devem ser confundidos com o gate do episódio ativo.

## Sequência operacional

1. Reunir notícias e fontes verificáveis.
2. Escrever o roteiro no padrão editorial.
3. Selecionar e registrar a Mensagem do Dia.
4. Dividir o roteiro em segmentos falados limpos.
5. Rodar gates pré-TTS.
6. Gerar o conteúdo conforme o plano de vozes da data editorial; na sexta, alternar Francisca e Thalita por bloco. Gerar headers com Antonio.
7. Rodar Mixer v9.
8. Rodar gate final e a babysitter.
9. Entregar o MP3 real como anexo.
