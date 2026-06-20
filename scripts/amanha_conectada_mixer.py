#!/usr/bin/env python3
"""
amanha_conectada_mixer.py — Mixer simplificado para o flash "Amanhã Conectada".

Diferente do drop5news-mixer-v9 (que faz 8 seções temáticas), este é OTIMIZADO
para o formato flash de 3-5min:
  - HOOK (15s) com trilha enérgica
  - 3-5 BLOCOS curtos (2-3 frases cada) com trilha mid-forward
  - CTA (15s) com trilha cinematic

Usa as 6 trilhas extraídas dos vídeos do Jean (D5N) em /root/d5n-trilhas/audios_extraidos/
Tambem aceita override via TRILHAS_DIR env var.

Uso:
  python3 amanha_conectada_mixer.py --voz /tmp/voz.mp3 --output /tmp/amanha.mp3
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

from pydub import AudioSegment

# Diretórios
TRILHAS_DIR = os.environ.get(
    "TRILHAS_DIR", "/root/d5n-trilhas/audios_extraidos"
)
# Trilhas mapeadas (do MIXMAP)
TRILHA_HOOK = "trilha-03-53s.mp3"      # energia/eletrônica
TRILHA_CHUNK = "trilha-04-96s.mp3"     # mid-forward
TRILHA_CTA = "trilha-01-147s.mp3"      # cinematic grave

# Volumes (em dB) - ducking forte pra deixar voz passar
BG_CHUNK_DB = -22      # trilha mid-forward por baixo da voz
BG_HOOK_DB = -16       # hook mais alto (sem voz por cima)
BG_CTA_DB = -20        # CTA

FADE_HOOK_MS = 800
FADE_CTA_MS = 1500
FADE_CHUNK_IN_MS = 600
FADE_CHUNK_OUT_MS = 600

# Validação
MIN_DUR_S = 180  # 3 min
MAX_DUR_S = 300  # 5 min


def get_duration_seconds(audio_path: str) -> float:
    """Retorna duração do áudio em segundos."""
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000.0


def load_trilha(name: str) -> AudioSegment:
    """Carrega trilha do diretório TRILHAS_DIR."""
    path = Path(TRILHAS_DIR) / name
    if not path.exists():
        raise FileNotFoundError(f"Trilha não encontrada: {path}")
    return AudioSegment.from_file(str(path))


def duck_under_voice(
    trilha: AudioSegment,
    voice: AudioSegment,
    bg_db: float,
    fade_in_ms: int,
    fade_out_ms: int,
) -> AudioSegment:
    """Faz a trilha tocar por baixo da voz (com fade in/out)."""
    # Ajusta volume
    trilha = trilha + bg_db

    # Loop se for menor que a voz
    if len(trilha) < len(voice):
        loops = (len(voice) // len(trilha)) + 1
        trilha = trilha * loops

    # Corta no tamanho da voz
    trilha = trilha[: len(voice)]

    # Fade in/out
    if fade_in_ms > 0:
        trilha = trilha.fade_in(fade_in_ms)
    if fade_out_ms > 0:
        trilha = trilha.fade_out(fade_out_ms)

    return trilha


def mix_hook_section(voice: AudioSegment, hook_trilha: AudioSegment) -> AudioSegment:
    """Mix do HOOK: trilha de energia + voz por cima (hook mais alto)."""
    hook_trilha = hook_trilha + BG_HOOK_DB
    # Hook dura no máx 15s
    hook_trilha = hook_trilha[: min(len(voice), 15_000)]
    hook_trilha = hook_trilha.fade_in(FADE_HOOK_MS).fade_out(FADE_HOOK_MS)

    # Trilha + voz (trilha mais alta no hook)
    mix = hook_trilha.overlay(voice[: len(hook_trilha)])
    return mix


def mix_chunk_section(voice: AudioSegment, chunk_trilha: AudioSegment) -> AudioSegment:
    """Mix do CHUNK: voz em cima + trilha mid-forward em loop com ducking."""
    trilha = duck_under_voice(
        chunk_trilha, voice, BG_CHUNK_DB, FADE_CHUNK_IN_MS, FADE_CHUNK_OUT_MS
    )
    # Trilha + voz
    mix = trilha.overlay(voice)
    return mix


def mix_cta_section(voice_tail: AudioSegment, cta_trilha: AudioSegment) -> AudioSegment:
    """Mix do CTA: trilha cinematic + voz do CTA."""
    cta_trilha = cta_trilha + BG_CTA_DB
    cta_trilha = cta_trilha[: len(voice_tail)]
    cta_trilha = cta_trilha.fade_in(FADE_CTA_MS).fade_out(FADE_CTA_MS)

    mix = cta_trilha.overlay(voice_tail)
    return mix


def main():
    parser = argparse.ArgumentParser(description="Amanhã Conectada — Mixer")
    parser.add_argument("--voz", required=True, help="Caminho do MP3 de voz (gerado pelo TTS)")
    parser.add_argument("--output", required=True, help="Caminho do MP3 de saída")
    parser.add_argument("--hook-seconds", type=float, default=15.0, help="Duração do HOOK em segundos")
    parser.add_argument("--cta-seconds", type=float, default=18.0, help="Duração do CTA em segundos")
    parser.add_argument("--skip-validation", action="store_true", help="Pula validação de duração")
    args = parser.parse_args()

    # Valida entrada
    if not Path(args.voz).exists():
        print(f"❌ Voz não encontrada: {args.voz}")
        sys.exit(1)

    # Carrega voz
    print(f"🎙️ Carregando voz: {args.voz}")
    voice = AudioSegment.from_file(args.voz)
    voice_dur = len(voice) / 1000.0
    print(f"   Duração: {voice_dur:.1f}s")

    # Validação
    if not args.skip_validation:
        if voice_dur < MIN_DUR_S:
            print(f"⚠️  ATENÇÃO: Áudio com {voice_dur:.0f}s (mínimo {MIN_DUR_S}s)")
            print(f"    O TTS/LLM precisa expandir o texto!")
        elif voice_dur > MAX_DUR_S:
            print(f"⚠️  ATENÇÃO: Áudio com {voice_dur:.0f}s (máximo {MAX_DUR_S}s)")
            print(f"    O TTS/LLM precisa condensar o texto!")
        else:
            print(f"✅ Duração dentro do range ({MIN_DUR_S}-{MAX_DUR_S}s)")

    # Carrega trilhas
    print(f"🎵 Carregando trilhas de {TRILHAS_DIR}")
    hook_trilha = load_trilha(TRILHA_HOOK)
    chunk_trilha = load_trilha(TRILHA_CHUNK)
    cta_trilha = load_trilha(TRILHA_CTA)

    # Define cortes (em ms)
    hook_ms = int(args.hook_seconds * 1000)
    cta_ms = int(args.cta_seconds * 1000)
    chunk_start_ms = hook_ms
    chunk_end_ms = max(hook_ms, len(voice) - cta_ms)
    cta_start_ms = chunk_end_ms

    # Validação: chunk precisa ter pelo menos 30s
    if (chunk_end_ms - chunk_start_ms) < 30_000:
        print(f"❌ CHUNK muito curto ({chunk_end_ms - chunk_start_ms}ms). Áudio total: {len(voice)}ms")
        sys.exit(1)

    print(f"   HOOK: 0 → {hook_ms}ms ({args.hook_seconds}s)")
    print(f"   CHUNK: {chunk_start_ms} → {chunk_end_ms}ms ({(chunk_end_ms - chunk_start_ms) / 1000:.1f}s)")
    print(f"   CTA: {cta_start_ms} → {len(voice)}ms ({(len(voice) - cta_start_ms) / 1000:.1f}s)")

    # Mix cada seção
    print("🎚️ Mixando HOOK...")
    voice_hook = voice[:chunk_start_ms]
    out_hook = mix_hook_section(voice_hook, hook_trilha)

    print("🎚️ Mixando CHUNK...")
    voice_chunk = voice[chunk_start_ms:chunk_end_ms]
    out_chunk = mix_chunk_section(voice_chunk, chunk_trilha)

    print("🎚️ Mixando CTA...")
    voice_cta = voice[cta_start_ms:]
    out_cta = mix_cta_section(voice_cta, cta_trilha)

    # Concatena
    print("🔗 Concatenando seções...")
    final = out_hook + out_chunk + out_cta

    # Fade in/out geral (2s)
    final = final.fade_in(1000).fade_out(2000)

    # Normaliza (peak a -1dB)
    print("📏 Normalizando...")
    final = final.apply_gain(-1.0 - final.max_dBFS)

    # Exporta
    print(f"💾 Salvando em {args.output}")
    final.export(args.output, format="mp3", bitrate="192k")

    # Relatório
    final_dur = len(final) / 1000.0
    final_size_mb = Path(args.output).stat().st_size / (1024 * 1024)
    print("")
    print("=" * 50)
    print(f"✅ MIX CONCLUÍDO")
    print(f"   Duração final: {final_dur:.1f}s")
    print(f"   Tamanho: {final_size_mb:.1f}MB")
    print(f"   Peak: {final.max_dBFS:.1f}dB")
    print(f"   Arquivo: {args.output}")
    print("=" * 50)

    if not args.skip_validation:
        if final_dur < MIN_DUR_S or final_dur > MAX_DUR_S:
            print(f"⚠️  Duração {final_dur:.0f}s fora do range {MIN_DUR_S}-{MAX_DUR_S}s")
            print(f"    O roteiro precisa ser expandido/condensado")
            # Não falha — só avisa (cron retry pode pegar)

    return 0


if __name__ == "__main__":
    main()
