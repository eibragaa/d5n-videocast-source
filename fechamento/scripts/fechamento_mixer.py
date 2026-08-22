#!/usr/bin/env python3
"""Mixer da FECHAMENTO DO MERCADO — identidade sonora própria e recursos versionados."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from pydub import AudioSegment, silence

FC_ROOT = Path(__file__).resolve().parents[1]
ASSETS = FC_ROOT / "assets" / "audio"
MC_ASSETS = FC_ROOT.parent / "manha-conectada" / "assets" / "audio"  # fallback
INTRO = ASSETS / "intro-mc-nova.mp3"
BED = ASSETS / "bg-music-mc.wav"
STING = ASSETS / "transition-sting.mp3"
MIN_SECONDS = 480
MAX_SECONDS = 600
LEAD_MS = 1800
THEME_PAUSE_EXTRA_MS = 700


def loop_to(audio: AudioSegment, length: int) -> AudioSegment:
    if not audio:
        raise ValueError("trilha vazia")
    result = AudioSegment.empty()
    while len(result) < length:
        result += audio
    return result[:length]


def require(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 5_000:
        # fallback para assets da Manhã Conectada
        alt = MC_ASSETS / path.name
        if alt.exists() and alt.stat().st_size >= 5_000:
            return
        raise FileNotFoundError(f"recurso de áudio ausente: {path}")


def extend_theme_pauses(voice: AudioSegment, max_extra_ms: int) -> tuple[AudioSegment, list[int]]:
    """Abre quatro respiros naturais; nunca corta a locução por tempo fixo."""
    detected = silence.detect_silence(
        voice,
        min_silence_len=700,
        silence_thresh=int(voice.dBFS - 20),
        seek_step=10,
    )
    targets = (60_000, 120_000, 180_000, 240_000)
    available = [(start, end) for start, end in detected if 10_000 < start < len(voice) - 10_000]
    selected: list[tuple[int, int]] = []
    pause_limit = max(0, max_extra_ms // THEME_PAUSE_EXTRA_MS)
    for target in targets[:pause_limit]:
        candidates = [span for span in available if all(abs(span[0] - used[0]) > 20_000 for used in selected)]
        if candidates:
            selected.append(min(candidates, key=lambda span: abs(((span[0] + span[1]) // 2) - target)))

    result = voice
    transition_positions: list[int] = []
    offset = 0
    for start, end in sorted(selected):
        insert_at = ((start + end) // 2) + offset
        result = result[:insert_at] + AudioSegment.silent(duration=THEME_PAUSE_EXTRA_MS, frame_rate=44100) + result[insert_at:]
        transition_positions.append(LEAD_MS + insert_at + THEME_PAUSE_EXTRA_MS // 2)
        offset += THEME_PAUSE_EXTRA_MS
    return result, transition_positions


def main() -> int:
    parser = argparse.ArgumentParser(description="Mixer da FECHAMENTO DO MERCADO")
    parser.add_argument("--voz", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    voice_path, output = Path(args.voz), Path(args.output)
    for path in (voice_path, INTRO, BED, STING):
        require(path)

    voice = AudioSegment.from_file(voice_path).set_channels(1).set_frame_rate(44100)
    # Apply a 10ms fade-in to the voice to avoid clicks at the start
    voice = voice.fade_in(10)
    duration = len(voice) / 1000
    if not MIN_SECONDS <= duration <= MAX_SECONDS:
        raise ValueError(f"voz fora da faixa {MIN_SECONDS}-{MAX_SECONDS}s: {duration:.1f}s")

    available_pause_ms = MAX_SECONDS * 1000 - LEAD_MS - len(voice)
    if available_pause_ms < 0:
        raise ValueError(
            f"voz longa demais para a abertura de {LEAD_MS / 1000:.1f}s: {duration:.1f}s"
        )
    voice, transition_positions = extend_theme_pauses(voice, available_pause_ms)
    intro = AudioSegment.from_file(INTRO).set_channels(1).set_frame_rate(44100)[:7500]
    bed = AudioSegment.from_file(BED).set_channels(1).set_frame_rate(44100)
    sting = AudioSegment.from_file(STING).set_channels(1).set_frame_rate(44100)[:1800].fade_out(500) - 17

    # Abertura instrumental audível; cama sobe levemente e respira entre temas.
    voice_canvas = AudioSegment.silent(duration=LEAD_MS, frame_rate=44100) + voice
    music = loop_to(bed - 25, len(voice_canvas)).fade_in(500).fade_out(2200)
    music = music.overlay(intro, position=0)
    # Assinatura em transições alternadas; as demais deixam só a trilha exposta.
    for index, position in enumerate(transition_positions):
        if index % 2 == 1:
            music = music.overlay(sting, position=max(0, position - len(sting) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix="-music.wav", delete=False) as music_tmp:
        music_path = Path(music_tmp.name)
    with tempfile.NamedTemporaryFile(suffix="-voice.wav", delete=False) as voice_tmp:
        voice_canvas_path = Path(voice_tmp.name)
    try:
        music.export(music_path, format="wav")
        voice_canvas.export(voice_canvas_path, format="wav")
        fade_start = max(0.0, len(voice_canvas) / 1000 - 1.8)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(music_path), "-i", str(voice_canvas_path),
            "-filter_complex",
            (
                "[1:a]highpass=f=65,asplit=2[voice][key];"
                "[0:a][key]sidechaincompress="
                "threshold=0.018:ratio=8:attack=15:release=320[ducked];"
                f"[ducked][voice]amix=inputs=2:normalize=0,"
                f"afade=t=out:st={fade_start:.3f}:d=1.8,"
                "loudnorm=I=-16:TP=-1.5:LRA=11[out]"
            ),
            "-map", "[out]",
            "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "192k", str(output),
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-500:])
    finally:
        music_path.unlink(missing_ok=True)
        voice_canvas_path.unlink(missing_ok=True)

    if not output.exists() or output.stat().st_size < 500_000:
        raise RuntimeError("MP3 final ausente ou pequeno demais")
    print(f"OK {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
