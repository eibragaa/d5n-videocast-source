#!/usr/bin/env python3
"""Mixer da MANHÃ CONECTADA — identidade sonora própria e recursos versionados."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from pydub import AudioSegment, silence

MC_ROOT = Path(__file__).resolve().parents[1]
ASSETS = MC_ROOT / "assets" / "audio"
INTRO = ASSETS / "intro-jingle.mp3"
BED = ASSETS / "bg-music-tech.wav"
STING = ASSETS / "transition-sting.mp3"
MIN_SECONDS = 225
MAX_SECONDS = 390
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
        raise FileNotFoundError(f"recurso de áudio ausente: {path}")


def extend_theme_pauses(voice: AudioSegment) -> tuple[AudioSegment, list[int]]:
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
    for target in targets:
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
    parser = argparse.ArgumentParser(description="Mixer da MANHÃ CONECTADA")
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

    voice, transition_positions = extend_theme_pauses(voice)
    intro = AudioSegment.from_file(INTRO).set_channels(1).set_frame_rate(44100)[:6000].fade_in(250).fade_out(900) - 10
    bed = AudioSegment.from_file(BED).set_channels(1).set_frame_rate(44100)
    sting = AudioSegment.from_file(STING).set_channels(1).set_frame_rate(44100)[:1800].fade_out(500) - 17

    # Abertura instrumental audível; cama sobe levemente e respira entre temas.
    voice_canvas = AudioSegment.silent(duration=LEAD_MS, frame_rate=44100) + voice
    music = loop_to(bed - 27, len(voice_canvas)).fade_in(500).fade_out(2200)
    music = music.overlay(intro, position=0)
    # Assinatura em transições alternadas; as demais deixam só a trilha exposta.
    for index, position in enumerate(transition_positions):
        if index % 2 == 1:
            music = music.overlay(sting, position=max(0, position - len(sting) // 2))
    mixed = music.overlay(voice_canvas).fade_out(1800)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        mixed.export(tmp_path, format="wav")
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(tmp_path),
            "-af", "highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "192k", str(output),
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-500:])
    finally:
        tmp_path.unlink(missing_ok=True)

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
