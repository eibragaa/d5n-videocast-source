# Trilhas D5N — Padrão Premium (decidido a partir dos assets fornecidos)

Assets originais fornecidos pelo Jean (pasta Google Drive "D5N - MANHÃ CONECTADA").
Baixados em 14/08/2026 e extraídos para `assets/audio/d5n/*.wav` (mono 44.1kHz, pcm_s16le).
Os arquivos eram vídeos; usamos apenas a trilha de áudio deles.

## Padrão de apresentação de referência

Hoje no Tecmundo — Amanda Flaury (https://youtu.be/69akKHThID4).
Estrutura premium desejada (adaptada ao boletim D5N, madrugada, 8–10 min, notícias do Jean):

1. **coldopen** — 3–4 manchetes-tiro, notícia no primeiro segundo
2. **intro** — auto-apresentação + pergunta de engajamento + vinheta
3. **noticias** (mundo, brasil, tecnologia, economia) — gancho → detalhe → efeito prático
4. **interacao** — check-in/pergunta no meio do programa
5. **ofertas** — bloco comercial rápido
6. **frase** — frase do dia
7. **recomendacoes** — livros/streaming
8. **historia** — fato histórico do dia
9. **outro** — CTA + lembrete + bordão de despedida

## Perfil técnico medido (ffmpeg loudnorm + RMS em janela 500ms)

| Arquivo | Dur (s) | I (LUFS) | LRA | TP (dBTP) | rms_med | %silêncio | pico/rms | Perfil |
|---|---|---|---|---|---|---|---|---|
| Vinheta.wav | 6.5 | -12.5 | 1.1 | +0.03 | 0.26 | 0% | 1.2 | **Vinheta curta de abertura** — curta, densa, sem variação |
| Vinheta2.wav | 173.9 | -13.1 | 7.6 | -0.16 | 0.32 | 0% | 1.2 | **Cama densa longa** — mais quente, serve de trilha contínua |
| Trilha_principal.wav | 146.2 | -13.0 | 6.1 | +0.07 | 0.29 | 0% | 1.3 | **Trilha principal** — bed densa e estável, boa p/ notícias |
| NEW-INTRO.wav | 85.6 | -19.3 | 2.8 | -2.95 | 0.13 | 1.2% | 1.5 | **Intro** — mais aberta, dinâmica média, própria p/ abertura falada |
| Cenario-global.wav | 84.3 | -19.3 | 9.3 | +0.07 | 0.12 | 3.0% | 3.6 | **Cenário global** — pico/rms alto (dinâmica), cama leve p/ mundo |
| Politica.wav | 60.3 | -19.8 | 5.5 | -0.76 | 0.13 | 0% | 1.4 | **Política** — cama leve e estável |
| Tech.wav | 76.2 | -19.4 | 8.8 | -1.41 | 0.12 | 0% | 2.0 | **Tech** — leve, dinâmica média |
| TECNOLOGIA.wav | 227.1 | -18.1 | 9.0 | +0.45 | 0.14 | 2.9% | 1.6 | **Tecnologia (longa)** — 227s, boa p/ bloco tech extenso |
| file-4c3b82e6.wav | 147.4 | -11.8 | 2.4 | +0.39 | 0.29 | 3.1% | 1.4 | bed quente estável |
| file-6a9bf54b.wav | 86.0 | -12.5 | 4.7 | +0.96 | 0.26 | 4.1% | 1.7 | bed quente |
| file-85e0bec2.wav | 52.9 | -12.7 | 3.0 | +0.57 | 0.24 | 4.8% | 1.6 | bed quente curta |
| file-9723d355.wav | 96.1 | -12.1 | 3.2 | +0.26 | 0.25 | 3.6% | 1.9 | bed quente |
| file-ab58d078.wav | 93.2 | -11.8 | 2.3 | +0.09 | 0.26 | 2.7% | 1.6 | bed quente |
| file-cad85d29.wav | 165.1 | -12.0 | 5.6 | +0.20 | 0.29 | 2.4% | 1.6 | bed quente longa |

### Leitura
- **Quentes (I ≈ -12, rms ≈ 0.26–0.32):** beds densas contínuas. Uso: trilha principal, Vinheta2, file-*. Servem de base sob a narração.
- **Leves (I ≈ -19, rms ≈ 0.12–0.14):** camas com mais espaço, dinâmicas. Uso: blocos temáticos falados (Cenario-global p/ mundo, Politica p/ política, Tech/TECNOLOGIA p/ tecnologia, NEW-INTRO p/ abertura).
- **Vinheta.wav (6.5s):** jingle de abertura.

## Decisão de mapeamento (a confirmar/refinar pelo Codex no mixer v10)
- **coldopen:** Vinheta.wav (6.5s) como assinatura + bed leve rápida
- **intro:** NEW-INTRO.wav
- **mundo:** Cenario-global.wav
- **brasil/política:** Politica.wav
- **tecnologia:** Tech.wav (ou TECNOLOGIA.wav p/ bloco longo)
- **economia/ofertas:** Trilha_principal.wav
- **cama contínua geral:** Trilha_principal.wav (padrão)
- **frase/história/recomendações:** bed leve (NEW-INTRO ou Cenario-global)
- **outro:** Vinheta2.wav (fade out)

O mixer deve aplicar: mono 44.1kHz, MP3 192kbps, −16 LUFS / −1.5 dBTP, fades e transições,
ducking da trilha sob a narração. Copiar asset em runtime NUNCA — sempre ler de
`assets/audio/d5n/`.
