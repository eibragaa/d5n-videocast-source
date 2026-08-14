#!/usr/bin/env python3
"""Valida e publica o manifesto canônico de capítulos do D5N."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

SECTION_ORDER = [
    "intro", "mundo", "brasil", "tecnologia", "economia", "interacao",
    "ofertas", "frase", "recomendacoes", "historia", "outro",
]
REQUIRED_IDS = {"intro", "mundo", "brasil", "tecnologia", "economia", "outro"}
MIN_CHAPTERS = 7  # coldopen é pré-roll e não aparece na navegação do player


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def validate_manifest(payload: dict, editorial_date: str, duration: float) -> dict:
    if int(payload.get("schema", 0)) < 2:
        raise ValueError("manifesto de capítulos exige schema >= 2")
    if payload.get("editorial_date") != editorial_date:
        raise ValueError(
            f"data do manifesto {payload.get('editorial_date')!r} != {editorial_date!r}"
        )

    chapters = payload.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("campo chapters ausente")
    ids = [chapter.get("id") for chapter in chapters]
    expected = [section_id for section_id in SECTION_ORDER if section_id in ids]
    if len(ids) < MIN_CHAPTERS or not REQUIRED_IDS.issubset(ids) or ids != expected:
        raise ValueError(f"ordem de capítulos inválida: {ids}")

    starts = []
    for chapter in chapters:
        start = float(chapter.get("start", -1))
        end = float(chapter.get("end", -1))
        if start < 0 or end <= start:
            raise ValueError(f"limite inválido em {chapter.get('id')}: {start}–{end}")
        starts.append(start)
    if abs(starts[0]) > 0.05:
        raise ValueError("primeiro capítulo deve iniciar em 0s")
    if any(right <= left for left, right in zip(starts, starts[1:])):
        raise ValueError("inícios dos capítulos não são estritamente crescentes")
    if abs(float(chapters[-1]["end"]) - duration) > 2.0:
        raise ValueError(
            f"fim dos capítulos ({chapters[-1]['end']}s) difere do MP3 ({duration:.3f}s)"
        )

    canonical = {
        "schema": 2,
        "editorial_date": editorial_date,
        "audio_duration": round(duration, 3),
        "chapters": chapters,
    }
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--date", required=True)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not args.manifest.is_file():
        raise SystemExit(f"BLOQUEADO: manifesto ausente: {args.manifest}")
    if not args.audio.is_file():
        raise SystemExit(f"BLOQUEADO: áudio ausente: {args.audio}")

    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        canonical = validate_manifest(payload, args.date, audio_duration(args.audio))
    except (ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"BLOQUEADO: capítulos inválidos: {exc}") from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(
        json.dumps(canonical, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(args.output)
    print(f"CHAPTERS_OK: {len(canonical['chapters'])} capítulos → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
