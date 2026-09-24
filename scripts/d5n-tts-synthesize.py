#!/usr/bin/env python3
"""
d5n-tts-synthesize.py — Sintetiza os arquivos .mp3 a partir dos .txt usando edge_tts.

Para cada .txt em audio_dir, gera um .mp3 correspondente usando a voz
designada pelo mapa de vozes do mixer v10.

Uso: python3 d5n-tts-synthesize.py --audio-dir /tmp/d5n_audio --editorial-date 2026-09-23
"""

import asyncio
import argparse
import os
import sys
from datetime import date
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("ERRO: edge_tts não instalado. Instale com: pip install edge-tts")
    sys.exit(1)

REPO = Path(os.environ.get("D5N_REPO", "/root/repositorio/d5n-videocast-source")).resolve()

# Vozes usadas pelo mixer v10
THALITA = "pt-BR-ThalitaMultilingualNeural"
FRANCISCA = "pt-BR-FranciscaNeural"

SECCOES = [
    ("coldopen", "coldopen.txt"),
    ("intro", "intro.txt"),
    ("mundo", "mundo.txt"),
    ("brasil", "brasil.txt"),
    ("tecnologia", "tecnologia.txt"),
    ("economia", "economia.txt"),
    ("interacao", "interacao.txt"),
    ("ofertas", "ofertas.txt"),
    ("frase", "frase.txt"),
    ("recomendacoes", "recomendacoes.txt"),
    ("historia", "historia.txt"),
    ("outro", "outro.txt"),
]


def get_voice_map(audio_dir: Path, editorial_date: date) -> dict[str, str]:
    """Replica a lógica de _read_voice_map do mixer v10."""
    wd = editorial_date.weekday()
    presentes = []
    for name, txt_name in SECCOES:
        txt = audio_dir / txt_name
        if txt.is_file() and txt.stat().st_size > 0:
            presentes.append(name)

    if wd in {0, 2, 5}:  # seg, qua, sáb → Thalita
        return {nome: THALITA for nome in presentes}
    elif wd in {1, 3}:  # ter, qui → Francisca
        return {nome: FRANCISCA for nome in presentes}
    else:  # sexta → alterna Thalita(ímpar)/Francisca(par) na ordem
        return {
            nome: THALITA if idx % 2 == 0 else FRANCISCA
            for idx, nome in enumerate(presentes)
        }


async def synthesize_one(name: str, text: str, voice: str, output: Path) -> bool:
    """Sintetiza um texto em áudio usando edge_tts."""
    print(f"  Sintetizando {name} ({voice})...", end=" ", flush=True)
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output))
        if output.stat().st_size > 5000:
            print(f"✓ ({output.stat().st_size / 1024:.1f} KB)")
            return True
        else:
            print(f"✗ arquivo muito pequeno ({output.stat().st_size} bytes)")
            output.unlink(missing_ok=True)
            return False
    except Exception as e:
        print(f"✗ {e}")
        output.unlink(missing_ok=True)
        return False


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-dir", default="/tmp/d5n_audio")
    ap.add_argument("--editorial-date", default=date.today().isoformat())
    args = ap.parse_args()

    audio_dir = Path(args.audio_dir)
    editorial_date = date.fromisoformat(args.editorial_date)

    if editorial_date.weekday() == 6:
        print("ERRO: domingo não tem episódio (manutenção de pipeline)")
        return 1

    audio_dir.mkdir(parents=True, exist_ok=True)

    voice_map = get_voice_map(audio_dir, editorial_date)
    if not voice_map:
        print("ERRO: nenhum .txt encontrado em audio_dir")
        return 1

    print(f"D5N TTS SYNTHESIS — {editorial_date}")
    print(f"Vozes: {len(voice_map)} seções, {len(set(voice_map.values()))} vozes diferentes")
    print()

    successes = 0
    failures = 0
    tasks = []

    for name, txt_name in SECCOES:
        txt_path = audio_dir / txt_name
        if not txt_path.is_file() or txt_path.stat().st_size == 0:
            continue
        mp3_path = audio_dir / f"{name}.mp3"
        if mp3_path.exists() and mp3_path.stat().st_size > 5000:
            print(f"  {name}: já existe, pulando...")
            successes += 1
            continue

        text = txt_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        voice = voice_map.get(name, THALITA)
        tasks.append((name, text, voice, mp3_path))

    if not tasks:
        print("Nada para sintetizar.")
        return 0

    for name, text, voice, mp3_path in tasks:
        ok = await synthesize_one(name, text, voice, mp3_path)
        if ok:
            successes += 1
        else:
            failures += 1

    print(f"\nConcluído: {successes} OK, {failures} falhou(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
