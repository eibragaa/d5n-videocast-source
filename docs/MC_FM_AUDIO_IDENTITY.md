# MC & FM — Identidade Sonora

Vigência: 27 de agosto de 2026.

---

## Critérios de aprovação (loop crítico-executor)

Antes de colocar em produção, toda demo deve passar por:

1. **Intro**: dura 3-5s e não compete com a narração
2. **BG audível**: -12dB (não usar -25dB, BG morre embaixo da voz)
3. **Narração começa**: 2-3s APÓS o início do BG/intro
4. **Pausas**: 1.5-2s entre blocos temáticos (não encadear sem pausa)
5. **Fade**: 0.8-1s de fade-in/out no BG e narração
6. **Sem loudnorm**: auto-nivelamento muda o timbre — proibido
7. **BG completo**: usa `loop_to()` para BG ser >= narração (nunca acabar antes)
8. **Volume narração**: 1.0-1.15x (não 0.9, precisa compensar o sidechain)

---

## Arquivos de áudio

### BGs (background loops de 60s)

| Programa | Arquivo | Origem | Timbre |
|---|---|---|---|
| MC | `bg-mc-03.mp3` | cand-03 | Grave/entulhado, íntimo |
| MC | `bg-mc-04.mp3` | cand-04 | Grave/entulhado, quente |
| MC | `bg-mc-06.mp3` | cand-06 | Equilibrado, suave |
| FM | `bg-fm-01.mp3` | cand-01 | Grave/intimidador |
| FM | `bg-fm-07.mp3` | cand-07 | Grave/ambiente |

### Intros (primeiros 5s de cada BG)

`intro-mc-03.mp3`, `intro-mc-04.mp3`, `intro-mc-06.mp3`
`intro-fm-01.mp3`, `intro-fm-07.mp3`

### Candidatos completos

Pasta: `assets/audio/intros-candidatos/`
- `cand-01.mp3` — FM primary
- `cand-03.mp3` — MC rotativo
- `cand-04.mp3` — MC rotativo
- `cand-06.mp3` — MC rotativo
- `cand-07.mp3` — FM rotativo

---

## Rotação automática

Mixers escolhem deterministicamente por data (mesmo ep. = mesmo BG):
- **Hoje** = seed da data → escolha aleatória com seed fixa
- Não é aleatório puro: garante reprodutibilidade

MC: 3 BGs (03, 04, 06)
FM: 2 BGs (01, 07)

---

## Parâmetros do mixer

### MC (Manhã Conectada)

| Parâmetro | Valor | Nota |
|---|---|---|
| LEAD_MS | 2000 | narração começa 2s depois |
| BG volume | -12dB | audível, não morre |
| Fade in BG | 800ms | entrada suave |
| Fade out BG | 1000ms | saída suave |
| Fade out final | 1000ms | 1s antes do fim |
| Sting volume | -17dB | assinatura em transições alternadas |
| Sidechain | ratio=8, threshold=0.018 | BG reduz quando fala |

### FM (Fechamento do Mercado)

| Parâmetro | Valor | Nota |
|---|---|---|
| LEAD_MS | 2000 | narração começa 2s depois |
| BG volume | -12dB | audível |
| Fade in BG | 800ms | entrada suave |
| Fade out BG | 1000ms | saída suave |
| Fade out final | 1000ms | 1s antes do fim |

---

## Vozes

| Programa | Voz | Provider | Nota |
|---|---|---|---|
| MC | `pt-BR-FranciscaNeural` | Edge TTS | Tom matinal |
| FM | `pt-BR-AntonioNeural` | Edge TTS | Tom de fechamento |

Taxa recomendada: `-2%` | Tom: `-2Hz`

---

## Como gerar uma demo

```bash
# 1. Gerar TTS por bloco (Edge TTS CLI)
edge-tts --voice pt-BR-FranciscaNeural --text "Bloco 1." --write-media s1.mp3
edge-tts --voice pt-BR-FranciscaNeural --text "Bloco 2." --write-media s2.mp3
edge-tts --voice pt-BR-FranciscaNeural --text "Bloco 3." --write-media s3.mp3

# 2. Converter para WAV
for f in s1.mp3 s2.mp3 s3.mp3; do
    ffmpeg -y -i "$f" -ac 1 -ar 44100 "${f%.mp3}.wav"
done

# 3. Concatenar com pausas (Python)
python3 -c "
import wave
def concat_wav(files, pauses, out):
    with wave.open(files[0]) as w:
        r,sw,ch=w.getframerate(),w.getsampwidth(),w.getnchannels()
        f=w.readframes(w.getnframes())
    for i,f in enumerate(files[1:]):
        with wave.open(f) as w2: f+=w2.readframes(w2.getnframes())
        f+=b'\x00\x00'*int(r*pauses[i])*ch
    with wave.open(out,'wb') as w3:
        w3.setnchannels(ch);w3.setsampwidth(sw);w3.setframerate(r)
        w3.writeframes(f)
concat_wav(['s1.wav','s2.wav','s3.wav'], [1.5,1.5], 'narration.wav')
"

# 4. Mix com ffmpeg
ffmpeg -y -i bg-mc-04.mp3 -i narration.wav -i intro-mc-04.mp3 \
  -filter_complex "
    [0:a]volume=-12dB,afade=t=in:st=0:d=0.8,afade=t=out:st=58:d=1[bg];
    [1:a]volume=1.15,adelay=2000|2000,afade=t=in:st=0:d=0.05,afade=t=out:st=60:d=1[voice];
    [2:a]volume=0.95,afade=t=in:st=0:d=0.3,afade=t=out:st=4:d=0.8[intro];
    [bg][voice]amix=inputs=2:duration=longest[bgv];
    [intro][bgv]amix=inputs=2:duration=longest[final]
  " -map "[final]" -codec:a libmp3lame -b:a 192k demo_mc.mp3
```

---

## Bugs conhecidos

- **BG acabar antes da narração**: usar `loop_to(bed, len(voice_canvas))` — BG deve ser >= canvas total
- **amix sem duration=longest**: ffmpeg para na faixa mais curta
- **Concatenar MP3 direto com concat:** não funciona — usar WAV intermediário
- **loudnorm**: muda timbre do BG musical, proibido

---

## Locais

- Repo: `/root/repositorio/d5n-videocast-source/`
- Mixers: `manha-conectada/scripts/` e `fechamento/scripts/`
- Demos beta: `/root/.hermes/homelab/d5n-audio-premium/demos-beta/`
- BGs backup: `/root/.hermes/homelab/d5n-audio-premium/`
