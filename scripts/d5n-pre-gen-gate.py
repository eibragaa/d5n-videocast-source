#!/usr/bin/env python3
"""Gate pré-geração do D5N — valida o diretório de roteiro antes do TTS."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

AUDIO_DIR = Path(os.environ.get("D5N_AUDIO_DIR", "/tmp/d5n_audio"))
REQUIRED = {"intro", "mundo", "brasil", "tecnologia", "economia", "ofertas", "outro"}
MIN_SECTIONS = 9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR))
    args = ap.parse_args()
    audio_dir = Path(args.audio_dir)

    errors = []
    if not audio_dir.is_dir():
        errors.append(f"diretorio de roteiro ausente: {audio_dir}")
        print("BLOQUEADO: " + " | ".join(errors))
        return 1

    presentes = {
        p.stem for p in audio_dir.glob("*.txt")
        if p.stat().st_size and p.stem not in {"cta", "outro", "intro"}
    }
    presentes |= {p.stem for p in audio_dir.glob("*.txt") if p.stat().st_size}

    if len(presentes) < MIN_SECTIONS:
        errors.append(f"secoes ausentes ou vazias: apenas {len(presentes)} de {MIN_SECTIONS}+")
    missing = sorted(REQUIRED - presentes)
    if missing:
        errors.append("secoes obrigatorias ausentes: " + ", ".join(missing))

    # O CTA e o outro devem existir e não estar vazios.
    for nome in ("cta", "outro"):
        f = audio_dir / f"{nome}.txt"
        if not f.is_file() or f.stat().st_size < 10:
            errors.append(f"secao obrigatoria ausente ou vazia: {nome}")

    if errors:
        print("BLOQUEADO: " + " | ".join(errors))
        return 1
    print(f"OK: pre-gen gate aprovado ({len(presentes)} seções)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
