# D5N — Variação "Vídeo Telejornal" (news-style short)

Gera vídeos verticais 9:16 estilo **telejornal de notícias** a partir de uma narração:
quebra em frases, busca **stock video por frase no Pexels** (com keywords semânticas em inglês
via DeepSeek), aplica o **visual instagram-premium** (obsidiana escuro + menta) e empacota com
ffmpeg em MP4. Útil para o D5N distribuir as mesmas notícias em vídeo curto (Reels/Shorts).

> Status: **variação experimental** (14/08/2026). Roda 100% local no homelab; sem ASR.

## Arquitetura (pipelines e fluxo)

```
texto da notícia
   │  edge-tts (voz PT-BR, ex. Thalita) ──► áudio mp3 + SentenceBoundary (timing por frase)
   │
   ├─► por frase: DeepSeek ──► 3 keywords EN ──► Pexels API ──► stock video (portrait)
   │        (fallback: heurística de palavras)
   │
   └─► .ass (legendas) + ffmpeg ──► concat dos clips + obsidiana/premium ──► MP4 9:16
```

- **Sem ASR**: usa `SentenceBoundary` do Edge TTS (timing exato por frase). Não precisa de
  Whisper — `ctranslate2` dá SIGILL nesta CPU (sem AVX2).
- **Correspondência semântica**: cada frase vira 3 keywords em inglês via DeepSeek, então o
  vídeo do Pexels é relevante ao que está sendo dito.
- **Visual**: scrim obsidiana (`eq` escurece) + cabeçalho "NOTÍCIAS · IA" (menta) + legenda
  por frase + rodapé "@jeanbraga.ia · SIGA" — alinhado ao padrão instagram-premium.

## Uso

```bash
cd d5n-video-telejornal
# chaves precisam estar no ambiente (ou export):
export PEXELS_API_KEY=...     # obrigatório p/ stock video
export DEEPSEEK_API_KEY=...   # opcional (keywords semânticas; senão usa heurística)

/root/.venv-telejornal/bin/python telejornal.py \
  --text "$(cat noticia.txt)" --out saida.mp4
# opções: --voice pt-BR-ThalitaMultilingualNeural --rate +12% --music m.mp3
```

Modos:
- **Pexels** (com `PEXELS_API_KEY`): stock video por frase. (padrão)
- **Fallback** (sem chave): fundo = gradiente obsidiana animado (lavfi `gradients`).

## Dependências
- Python venv `/root/.venv-telejornal`: `edge-tts`, `faster-whisper` (não usado, ver pitfall).
- `ffmpeg` (7.x, com `libass`/`subtitles` para o `.ass`).
- Chaves: `PEXELS_API_KEY`, `DEEPSEEK_API_KEY` (no `/root/.hermes/.env`, imutável).

## Pitfalls (aprendidos)
- `ass=` filter: caminho SEM parênteses; escapar `: , [ ] \`.
- ffmpeg: todos os `-i` primeiro; `-vf`/`-filter_complex` como opção de saída (senão erro 234).
- filter_complex SEM `;;` duplo → `No such filter: ''`.
- Pexels via urllib dá 403 sem `User-Agent` (bloqueia `Python-urllib`).
- Whisper/faster-whisper (`ctranslate2`) → **SIGILL** nesta CPU sem AVX2. Usar Edge TTS timing.
- `.env` do Hermes é imutável (`chattr +i`): p/ salvar chave, `chattr -i`, editar, `chattr +i`.
- `p_src()`: backslash em f-string é proibido no Python 3.12+.

## Limitações de voz clonada
- **OpenVoice v2 não fala português** (base MeloTTS: EN/ES/FR/ZH/JA/KR).
- **PT-BR zero-shot local = Coqui XTTS v2**, mas exige AVX2/GPU — NÃO roda neste homelab.
  Clonar a voz numa máquina forte e trazer o áudio aqui.
