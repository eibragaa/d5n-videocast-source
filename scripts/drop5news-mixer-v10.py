#!/usr/bin/env python3
"""Mixer v10 do Drop Five News — identidade sonora premium D5N v3.

Mixa os segmentos TTS com trilhas próprias de ``assets/audio/d5n``, preserva
a ordem canônica das seções presentes e grava um manifesto schema 2.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from pydub import AudioSegment, silence

SECOES = [
    ("coldopen", "coldopen.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("intro", "intro.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("mundo", "mundo.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("brasil", "brasil.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("tecnologia", "tecnologia.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("economia", "economia.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("interacao", "interacao.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("ofertas", "ofertas.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("frase", "frase.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("recomendacoes", "recomendacoes.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("historia", "historia.txt", "pt-BR-ThalitaMultilingualNeural"),
    ("outro", "outro.txt", "pt-BR-ThalitaMultilingualNeural"),
]
REQUIRED_TXT = {"coldopen", "intro", "mundo", "brasil", "tecnologia", "economia", "outro"}
MIN_SECTIONS = 8

REPO = Path(os.environ.get("D5N_REPO", "/root/repositorio/d5n-videocast-source")).resolve()
ASSET_DIR = REPO / "assets" / "audio" / "d5n"
FALLBACK_TRACK = "Trilha_principal.wav"
TRACKS = {
    "coldopen": "Cenario-global.wav",
    "intro": "NEW-INTRO.wav",
    "mundo": "Cenario-global.wav",
    "brasil": "Politica.wav",
    "tecnologia": "Tech.wav",
    "economia": "Trilha_principal.wav",
    "interacao": "NEW-INTRO.wav",
    "ofertas": "Trilha_principal.wav",
    "frase": "NEW-INTRO.wav",
    "recomendacoes": "Cenario-global.wav",
    "historia": "file-9723d355.wav",
    "outro": "Vinheta2.wav",
}
LIGHT_TRACKS = {"NEW-INTRO.wav", "Cenario-global.wav", "Politica.wav", "Tech.wav", "TECNOLOGIA.wav"}
MIN_SECONDS = 300
MAX_SECONDS = 720
PAUSE_MS = 300
PAUSE_EXTRA_MS = 650
HIGH_LUF = -16
TRUE_PEAK = -1.5
BITS = 192


def require(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 5_000:
        raise FileNotFoundError(f"Trilha obrigatória ausente: {path}")


def _read_voice_map(section_names: list[str], editorial_date: date) -> dict[str, str]:
    thalita = "pt-BR-ThalitaMultilingualNeural"
    francisca = "pt-BR-FranciscaNeural"
    if editorial_date.weekday() in {0, 2, 5}:
        return dict.fromkeys(section_names, thalita)
    if editorial_date.weekday() in {1, 3}:
        return dict.fromkeys(section_names, francisca)
    return {name: thalita if index % 2 == 0 else francisca
            for index, name in enumerate(section_names)}


def load_segments(audio_dir: Path) -> list[tuple[str, str, Path]]:
    segments = []
    for name, txt_name, _voice in SECOES:
        txt = audio_dir / txt_name
        if not txt.is_file() or not txt.stat().st_size:
            continue
        text = txt.read_text(encoding="utf-8", errors="replace").strip()
        mp3 = audio_dir / f"{name}.mp3"
        if not mp3.is_file() or mp3.stat().st_size < 5_000:
            if name in REQUIRED_TXT:
                raise FileNotFoundError(f"Seção obrigatória sem áudio: {name} ({mp3})")
            continue
        segments.append((name, text, mp3))
    present = {name for name, *_ in segments}
    missing = REQUIRED_TXT - present
    if missing:
        raise FileNotFoundError("Seções obrigatórias sem roteiro: " + ", ".join(sorted(missing)))
    if len(segments) < MIN_SECTIONS:
        raise ValueError(f"roteiro precisa de pelo menos {MIN_SECTIONS} seções; encontradas {len(segments)}")
    return segments


def loop_to(audio: AudioSegment, length: int) -> AudioSegment:
    if not audio:
        raise ValueError("trilha vazia")
    repeats = max(1, (length + len(audio) - 1) // len(audio))
    return (audio * repeats)[:length]


def extend_pauses(voice: AudioSegment) -> AudioSegment:
    detected = silence.detect_silence(
        voice, min_silence_len=600, silence_thresh=int(voice.dBFS - 20), seek_step=10
    )
    targets = (60_000, 120_000, 180_000, 240_000)
    selected: list[tuple[int, int]] = []
    available = [(start, end) for start, end in detected if 10_000 < start < len(voice) - 10_000]
    for target in targets:
        candidates = [span for span in available if all(abs(span[0] - used[0]) > 20_000 for used in selected)]
        if candidates:
            selected.append(min(candidates, key=lambda span: abs(sum(span) // 2 - target)))
    result = voice
    offset = 0
    for start, end in sorted(selected):
        at = (start + end) // 2 + offset
        result = result[:at] + AudioSegment.silent(PAUSE_EXTRA_MS, frame_rate=44100) + result[at:]
        offset += PAUSE_EXTRA_MS
    return result


def track_for(name: str, voice_ms: int) -> tuple[Path, float]:
    filename = "TECNOLOGIA.wav" if name == "tecnologia" and voice_ms > 90_000 else TRACKS[name]
    path = ASSET_DIR / filename
    if not path.is_file() or path.stat().st_size < 5_000:
        path = ASSET_DIR / FALLBACK_TRACK
        filename = FALLBACK_TRACK
    require(path)
    # As camas leves medem cerca de -19 LUFS; as quentes, cerca de -12 LUFS.
    # Os ganhos abaixo colocam ambas na faixa aproximada de -28 a -29 LUFS.
    gain = -10.0 if filename in LIGHT_TRACKS else -16.0
    return path, gain


def mix_section(name: str, voice: AudioSegment) -> tuple[AudioSegment, str, float]:
    path, gain = track_for(name, len(voice))
    bed = loop_to(AudioSegment.from_file(path).set_channels(1).set_frame_rate(44100), len(voice)) + gain
    fade_out = min(4_500 if name == "outro" else 900, max(1, len(bed)))
    bed = bed.fade_in(min(500, len(bed))).fade_out(fade_out)
    if name == "coldopen":
        signature_path = ASSET_DIR / "Vinheta.wav"
        require(signature_path)
        signature = AudioSegment.from_file(signature_path).set_channels(1).set_frame_rate(44100) - 10
        bed = bed.overlay(signature[:len(bed)].fade_out(min(700, len(signature))))
    return bed.overlay(voice.fade_in(12)), path.name, gain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-dir", default="/tmp/d5n_audio")
    parser.add_argument("--output", default="/tmp/d5n_mixado_v10.mp3")
    parser.add_argument("--editorial-date", default=os.environ.get("D5N_EDITORIAL_DATE", date.today().isoformat()))
    args = parser.parse_args()
    audio_dir, output = Path(args.audio_dir), Path(args.output)
    editorial_date = date.fromisoformat(args.editorial_date)
    if editorial_date.weekday() == 6:
        raise RuntimeError("domingo não tem episódio (manutenção de pipeline)")

    require(ASSET_DIR / FALLBACK_TRACK)
    segments = load_segments(audio_dir)
    voice_map = _read_voice_map([name for name, *_ in segments], editorial_date)
    mixed = AudioSegment.empty()
    rendered: list[dict] = []
    cursor_ms = 0
    for index, (name, _text, mp3_path) in enumerate(segments):
        voice = extend_pauses(AudioSegment.from_file(mp3_path).set_channels(1).set_frame_rate(44100))
        section, track_name, gain = mix_section(name, voice)
        start_ms = cursor_ms
        mixed += section
        cursor_ms += len(section)
        rendered.append({"id": name, "start_ms": start_ms, "end_ms": cursor_ms,
                         "track": track_name, "track_gain_db": gain})
        if index < len(segments) - 1:
            mixed += AudioSegment.silent(PAUSE_MS, frame_rate=44100)
            cursor_ms += PAUSE_MS

    duration_s = len(mixed) / 1000
    if not MIN_SECONDS <= duration_s <= MAX_SECONDS:
        raise ValueError(f"narração fora da faixa {MIN_SECONDS}-{MAX_SECONDS}s: {duration_s:.1f}s")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        mixed.fade_out(1_800).export(tmp_path, format="wav")
        command = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(tmp_path),
            "-af", f"highpass=f=65,loudnorm=I={HIGH_LUF}:TP={TRUE_PEAK}:LRA=11",
            "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", f"{BITS}k", str(output),
        ]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if proc.returncode:
            raise RuntimeError(proc.stderr[-500:])
    finally:
        tmp_path.unlink(missing_ok=True)
    if not output.exists() or output.stat().st_size < 100_000:
        raise RuntimeError("MP3 final ausente ou pequeno demais")

    sections = [name for name, *_ in segments]
    thalita, francisca = "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"
    voices = [thalita, francisca] if editorial_date.weekday() == 4 else sorted(set(voice_map.values()))
    # Cold open é pré-roll editorial: capítulos navegáveis começam na intro em 0s.
    intro_offset = next(item["start_ms"] for item in rendered if item["id"] == "intro")
    chapter_starts = [
        (item["id"], round(max(0, item["start_ms"] - intro_offset) / 1000, 3))
        for item in rendered if item["id"] != "coldopen"
    ]
    chapters = [
        {"id": name, "start": start,
         "end": chapter_starts[index + 1][1] if index + 1 < len(chapter_starts) else round(duration_s, 3)}
        for index, (name, start) in enumerate(chapter_starts)
    ]
    manifest = {
        "schema": 2, "programa": "Drop Five News", "tts_provider": "edge-tts-local",
        "header_voice": "pt-BR-AntonioNeural", "editorial_date": editorial_date.isoformat(),
        "sections": sections, "content_voices": voices,
        "presentation_mode": ("sexta-dual-dinamica" if editorial_date.weekday() == 4 else
                              "solo-thalita" if voice_map["intro"] == thalita else "solo-francisca"),
        "section_voice_map": {name: voice_map[name] for name in sections},
        "loudness_target_lufs": HIGH_LUF, "true_peak_target_dbtp": TRUE_PEAK,
        "chapters": chapters,
        "audio_beds": {item["id"]: {"file": item["track"], "gain_db": item["track_gain_db"]}
                       for item in rendered},
        "output": str(output),
    }
    (audio_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {output} · {duration_s:.0f}s · {len(sections)} seções")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
