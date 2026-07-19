#!/usr/bin/env python3
"""Mixer da MANHÃ CONECTADA — identidade sonora própria e recursos versionados."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from pydub import AudioSegment

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets" / "audio" / "manha-conectada"
INTRO = ASSETS / "intro-jingle.mp3"
BED = ASSETS / "bg-music.mp3"
STING = ASSETS / "transition-sting.mp3"
MIN_SECONDS = 225
MAX_SECONDS = 390


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Mixer da MANHÃ CONECTADA")
    parser.add_argument("--voz", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    voice_path, output = Path(args.voz), Path(args.output)
    for path in (voice_path, INTRO, BED, STING):
        require(path)

    voice = AudioSegment.from_file(voice_path).set_channels(1).set_frame_rate(44100)
    duration = len(voice) / 1000
    if not MIN_SECONDS <= duration <= MAX_SECONDS:
        raise ValueError(f"voz fora da faixa {MIN_SECONDS}-{MAX_SECONDS}s: {duration:.1f}s")

    intro = AudioSegment.from_file(INTRO).set_channels(1).set_frame_rate(44100)[:6000].fade_in(300).fade_out(900) - 13
    bed = AudioSegment.from_file(BED).set_channels(1).set_frame_rate(44100)
    sting = AudioSegment.from_file(STING).set_channels(1).set_frame_rate(44100)[:1800].fade_out(500) - 17

    # Abertura de 1,2s antes da voz; cama discreta e marca de transição no terço final.
    lead = intro[:1200]
    voice_canvas = AudioSegment.silent(duration=1200, frame_rate=44100) + voice
    music = loop_to(bed - 30, len(voice_canvas)).fade_in(900).fade_out(2200)
    music = music.overlay(intro, position=0)
    transition_at = max(20_000, int(len(voice_canvas) * 0.72))
    music = music.overlay(sting, position=transition_at)
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
