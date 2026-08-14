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
MIN_SECONDS = 480
MAX_SECONDS = 720
PAUSE_MS = 300
PAUSE_EXTRA_MS = 650
HIGH_LUF = -16
TRUE_PEAK = -1.5
BITS = 192
LEAD_MS = 2_000
HEADER_BREATH_MS = 350
GLOBAL_FADE_IN_MS = 800
GLOBAL_FADE_OUT_MS = 2_000
LIGHT_TRACK_GAIN_DB = -20.0
HOT_TRACK_GAIN_DB = -26.0
VOICE_TARGET_DBFS = -19.0
SIGNATURE_GAIN_DB = -8.0
SIGNATURE_GAP_MS = 150
HEADER_VOICE = "pt-BR-AntonioNeural"
HEADER_LABELS = {
    "mundo": "Mundo",
    "brasil": "Brasil",
    "tecnologia": "Tecnologia",
    "economia": "Economia",
    "interacao": "Sua vez",
    "ofertas": "Ofertas do dia",
    "frase": "Mensagem do dia",
    "recomendacoes": "Recomendações",
    "historia": "História do dia",
}


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
    # Ganhos distintos mantêm a cama bem abaixo da voz já nivelada.
    gain = LIGHT_TRACK_GAIN_DB if filename in LIGHT_TRACKS else HOT_TRACK_GAIN_DB
    return path, gain


def valid_header(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1_000:
        return False
    try:
        return len(AudioSegment.from_file(path)) > 100
    except Exception:
        return False


def synthesize_header(audio_dir: Path, name: str) -> Path | None:
    label = HEADER_LABELS.get(name)
    if label is None:
        return None
    target = audio_dir / f"{name}_header.mp3"
    if valid_header(target):
        return target

    temp = target.with_suffix(".tmp.mp3")
    try:
        import asyncio
        import edge_tts

        temp.unlink(missing_ok=True)
        asyncio.run(edge_tts.Communicate(label, HEADER_VOICE).save(str(temp)))
        if not valid_header(temp):
            raise RuntimeError("arquivo sintetizado inválido")
        temp.replace(target)
        return target
    except Exception as exc:
        temp.unlink(missing_ok=True)
        print(f"AVISO: header {name!r} não foi sintetizado: {exc}", file=sys.stderr)
        return None


def mix_section(
    name: str, voice: AudioSegment, header: AudioSegment | None = None
) -> tuple[AudioSegment, str, float]:
    if voice.dBFS != float("-inf"):
        voice = voice + (VOICE_TARGET_DBFS - voice.dBFS)
    content = voice
    voice_offset = 0
    if header is not None:
        header = header.set_channels(1).set_frame_rate(44100)
        content = header + AudioSegment.silent(HEADER_BREATH_MS, frame_rate=44100) + voice
        voice_offset = len(header) + HEADER_BREATH_MS
    if name == "coldopen":
        content = AudioSegment.silent(LEAD_MS, frame_rate=44100) + voice
        voice_offset = LEAD_MS

    path, gain = track_for(name, len(voice))
    bed = loop_to(AudioSegment.from_file(path).set_channels(1).set_frame_rate(44100), len(content)) + gain
    fade_out = min(4_500 if name == "outro" else 900, max(1, len(bed)))
    bed = bed.fade_in(min(500, len(bed))).fade_out(fade_out)
    spoken = content if voice_offset == 0 else AudioSegment.silent(
        voice_offset, frame_rate=44100
    ) + voice.fade_in(12)
    if header is not None:
        spoken = header + AudioSegment.silent(HEADER_BREATH_MS, frame_rate=44100) + voice.fade_in(12)
    section = bed.overlay(spoken)
    if name == "coldopen":
        # A assinatura entra somente depois das manchetes, antes da intro, sem voz concorrente.
        signature_path = ASSET_DIR / "Vinheta.wav"
        require(signature_path)
        signature = AudioSegment.from_file(signature_path).set_channels(1).set_frame_rate(44100)
        signature = (signature + SIGNATURE_GAIN_DB).fade_in(80).fade_out(min(700, len(signature)))
        section += AudioSegment.silent(SIGNATURE_GAP_MS, frame_rate=44100) + signature
    return section, path.name, gain


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
    section_headers: dict[str, str] = {}
    cursor_ms = 0
    for index, (name, _text, mp3_path) in enumerate(segments):
        voice = extend_pauses(AudioSegment.from_file(mp3_path).set_channels(1).set_frame_rate(44100))
        header_path = synthesize_header(audio_dir, name)
        header = AudioSegment.from_file(header_path) if header_path is not None else None
        if header_path is not None:
            section_headers[name] = header_path.name
        section, track_name, gain = mix_section(name, voice, header)
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
        mixed.fade_in(GLOBAL_FADE_IN_MS).fade_out(GLOBAL_FADE_OUT_MS).export(tmp_path, format="wav")
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
        "header_voice": HEADER_VOICE, "editorial_date": editorial_date.isoformat(),
        "sections": sections, "content_voices": voices,
        "section_headers": section_headers,
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
