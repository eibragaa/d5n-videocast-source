#!/usr/bin/env python3
"""Gate bloqueante editorial + técnico do MP3 final do Drop Five News."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import datetime
from pathlib import Path

AUDIO_DIR = Path(os.environ.get("D5N_AUDIO_DIR", "/tmp/d5n_audio"))
MIXED = Path(os.environ.get("D5N_MIXED_FILE", "/tmp/d5n_mixado_v9.mp3"))
MANIFEST = AUDIO_DIR / "manifest.json"
EXPECTED = {
    "programa": "Drop Five News",
    "tts_provider": "edge-tts-local",
    "header_voice": "pt-BR-AntonioNeural",
    "loudness_target_lufs": -16,
    "true_peak_target_dbtp": -1.5,
}
FRANCISCA = "pt-BR-FranciscaNeural"
FORBIDDEN = ("cinto", "DropFiveNews", "Drop News")
ENGLISH_DATE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"January|February|March|April|May|June|July|August|September|October|November|December)\b",
    re.I,
)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
GOODBYE = re.compile(r"\b(?:tchau|até amanhã|até mais|valeu|falou)\b", re.I)
URL_OR_MARKDOWN = re.compile(r"https?://|\[[^]]+\]\([^)]+\)|[*_`#]{2,}")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def probe_audio(errors: list[str]) -> dict:
    if not MIXED.exists() or MIXED.stat().st_size < 100_000:
        fail(errors, f"MP3 final ausente ou pequeno: {MIXED}")
        return {}
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,bit_rate:stream=codec_name,sample_rate,channels",
        "-of", "json", str(MIXED),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode:
        fail(errors, f"ffprobe falhou: {p.stderr.strip()}")
        return {}
    data = json.loads(p.stdout)
    fmt = data.get("format", {})
    stream = (data.get("streams") or [{}])[0]
    duration = float(fmt.get("duration", 0))
    bitrate = int(fmt.get("bit_rate", 0))
    if not 120 <= duration <= 1200:
        fail(errors, f"duração fora de 2–20 min: {duration:.2f}s")
    if bitrate < 128_000:
        fail(errors, f"bitrate abaixo de 128 kbps: {bitrate}")
    if stream.get("codec_name") != "mp3":
        fail(errors, f"codec inesperado: {stream.get('codec_name')}")
    if int(stream.get("sample_rate", 0)) != 44_100:
        fail(errors, f"sample rate diferente de 44,1 kHz: {stream.get('sample_rate')}")
    if int(stream.get("channels", 0)) != 1:
        fail(errors, f"áudio deve ser mono: {stream.get('channels')} canais")
    return {"duration": duration, "bitrate": bitrate}


def measure_loudness(errors: list[str]) -> dict:
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(MIXED),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    match = re.search(r"\{\s*\"input_i\".*?\}", p.stderr, re.S)
    if not match:
        fail(errors, "não foi possível medir loudness com ffmpeg")
        return {}
    stats = json.loads(match.group(0))
    lufs = float(stats["input_i"])
    peak = float(stats["input_tp"])
    if not -17.0 <= lufs <= -15.0:
        fail(errors, f"loudness fora de -16±1 LUFS: {lufs:.2f}")
    if peak > -1.0:
        fail(errors, f"true peak acima de -1 dBTP: {peak:.2f}")
    return {"lufs": lufs, "true_peak": peak, "lra": float(stats["input_lra"])}


def validate_manifest(errors: list[str]) -> dict:
    if not MANIFEST.exists():
        fail(errors, f"manifesto de vozes ausente: {MANIFEST}")
        return {}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(errors, f"manifesto inválido: {exc}")
        return {}
    for key, expected in EXPECTED.items():
        if data.get(key) != expected:
            fail(errors, f"manifesto {key}: esperado {expected!r}, recebido {data.get(key)!r}")
    sections = data.get("sections")
    if not isinstance(sections, list) or not {"intro", "outro"}.issubset(sections):
        fail(errors, "manifesto sem intro/outro na ordem de seções")
        return data

    try:
        editorial_date = datetime.date.fromisoformat(data["editorial_date"])
    except (KeyError, TypeError, ValueError):
        fail(errors, "manifesto sem editorial_date ISO válida")
        return data

    weekday = editorial_date.weekday()
    voices = data.get("content_voices")
    voice_map = data.get("section_voice_map")
    mode = data.get("presentation_mode")
    if not isinstance(voice_map, dict) or set(voice_map) != set(sections):
        fail(errors, "section_voice_map não corresponde às seções mixadas")
        return data

    if weekday == 6:
        fail(errors, "manifesto representa episódio de domingo")
    else:
        expected_voice = FRANCISCA
        expected_mode = "solo-francisca-ptbr"
        if voices != [expected_voice] or mode != expected_mode:
            fail(errors, f"conteúdo exige voz estritamente pt-BR: {voices!r}, {mode!r}")
        if any(voice != expected_voice for voice in voice_map.values()):
            fail(errors, "section_voice_map contém voz não aprovada para pt-BR")
    return data


def validate_spoken_text(errors: list[str]) -> None:
    txts = sorted(AUDIO_DIR.glob("*.txt"))
    if not txts:
        fail(errors, "nenhum segmento .txt encontrado")
        return
    official_name_seen = False
    for path in txts:
        text = path.read_text(encoding="utf-8", errors="replace")
        folded = text.casefold()
        if "drop five news" in folded:
            official_name_seen = True
        for forbidden in FORBIDDEN:
            if forbidden.casefold() in folded:
                fail(errors, f"{path.name}: expressão proibida {forbidden!r}")
        if ENGLISH_DATE.search(text):
            fail(errors, f"{path.name}: dia ou mês em inglês")
        if EMOJI.search(text):
            fail(errors, f"{path.name}: emoji no texto falado")
        if URL_OR_MARKDOWN.search(text):
            fail(errors, f"{path.name}: URL ou markdown no texto falado")
        is_header = path.stem.endswith("_header")
        if path.stem not in {"intro", "outro"} and not is_header and GOODBYE.search(text):
            fail(errors, f"{path.name}: despedida intermediária")
        if path.stem != "outro" and re.search(r"instagram|siga|segue a gente|me segue", text, re.I):
            fail(errors, f"{path.name}: CTA fora do encerramento")
    if not official_name_seen:
        fail(errors, "nome oficial 'Drop Five News' ausente dos segmentos")


def main() -> int:
    errors: list[str] = []
    validate_spoken_text(errors)
    manifest = validate_manifest(errors)
    audio = probe_audio(errors)
    loudness = measure_loudness(errors) if MIXED.exists() else {}
    if errors:
        print("BLOQUEADO: gate do podcast falhou")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OK: podcast alinhado ao novo padrão")
    print(json.dumps({"audio": audio, "loudness": loudness, "manifest": manifest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
