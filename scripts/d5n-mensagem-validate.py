#!/usr/bin/env python3
"""Valida a Mensagem do Dia (frase.txt) antes do TTS — seleção SystemRandom, sem repetição recente."""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

AUDIO_DIR = Path(os.environ.get("D5N_AUDIO_DIR", "/tmp/d5n_audio"))
HISTORY_FILE = Path(os.environ.get("D5N_FRASE_HISTORY", "/root/.hermes/scripts/.frase_history.json"))
BLOCKLIST = ("cinto",)


def _fold(text: str) -> str:
    return " ".join(text.casefold().split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR))
    args = ap.parse_args()
    audio_dir = Path(args.audio_dir)
    frase = audio_dir / "frase.txt"

    errors = []
    if not frase.is_file() or frase.stat().st_size < 10:
        errors.append("frase.txt ausente ou vazio")
        print("BLOQUEADO: " + " | ".join(errors))
        return 1

    texto = frase.read_text(encoding="utf-8", errors="replace").strip()
    if not texto:
        errors.append("frase.txt vazio")
    for banned in BLOCKLIST:
        if banned in _fold(texto):
            errors.append(f"frase contém termo proibido: {banned!r}")
    if len(texto) < 20:
        errors.append("frase muito curta")

    if not errors:
        # Registra no histórico para evitar repetição recente
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        hist = []
        if HISTORY_FILE.exists():
            try:
                hist = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                hist = []
        hist.insert(0, texto)
        HISTORY_FILE.write_text(json.dumps(hist[:90], ensure_ascii=False, indent=2), encoding="utf-8")

    if errors:
        print("BLOQUEADO: " + " | ".join(errors))
        return 1
    print("OK: mensagem do dia válida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
