#!/usr/bin/env python3
"""GateDurance Snapshot Restore — restaura os .txt de roteiro a partir do snapshot
APROVADO e valida antes do TTS.

Por quê: os .txt em /tmp/d5n_audio podem ser sobrescritos por jobs concorrentes
com versões ruins (inglês, markdown). A fonte da verdade do que foi aprovado é o
snapshot podcast-scripts/<data>.json. Este script reconstroi os .txt a partir do
snapshot e garante que o texto que segue para o TTS é exatamente o aprovado.

Uso:
    python3 d5n-gatedurance-snapshot-restore.py --date YYYY-MM-DD \
        [--snapshot-dir podcast-scripts] [--audio-dir /tmp/d5n_audio]

Exit 0 = txts restaurados a partir do snapshot aprovado e GateDurance verde
        (pronto para TTS).
Exit 1 = snapshot não encontrado ou roteiro restaurado ainda reprovado.
Exit 2 = sem snapshot aprovado para a data (precisa gerar roteiro do zero).
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

# Seções que devem existir no snapshot (mesmo contrato do mixer).
REQUIRED = ["intro", "mundo", "brasil", "tecnologia", "economia",
            "ofertas", "frase", "cta", "outro"]


def load_snapshot(snapshot_dir, date):
    """Retorna dict de segments do snapshot aprovado, ou None."""
    path = Path(snapshot_dir) / f"{date}.json"
    if not path.exists():
        return None, f"sem snapshot aprovado para {date} em {path}"
    snap = json.loads(path.read_text(encoding="utf-8"))
    segs = snap.get("segments") or {}
    return segs, None


def restore(segs, audio_dir):
    """Escreve os txts a partir do snapshot aprovado."""
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in REQUIRED:
        text = (segs.get(name) or "").strip()
        if not text:
            continue
        (audio_dir / f"{name}.txt").write_text(text, encoding="utf-8")
        written.append(name)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--snapshot-dir", default="podcast-scripts")
    ap.add_argument("--audio-dir", default="/tmp/d5n_audio")
    args = ap.parse_args()

    segs, err = load_snapshot(args.snapshot_dir, args.date)
    if segs is None:
        print(f"RESTORE: {err}")
        return 2

    missing = [n for n in REQUIRED if not (segs.get(n) or "").strip()]
    if missing:
        print(f"RESTORE: snapshot de {args.date} incompleto, faltam: {', '.join(missing)}")
        return 2

    written = restore(segs, args.audio_dir)
    print(f"RESTORE: txts restaurados do snapshot aprovado {args.date} → "
          f"{args.audio_dir} ({len(written)} seções): {', '.join(written)}")

    # Validação final com o GateDurance (o mesmo usado no pipeline).
    here = Path(__file__).resolve().parent
    gate = here / "d5n-gatedurance-script-gate.py"
    r = subprocess.run(
        ["python3", str(gate), "--date", args.date, "--audio-dir", args.audio_dir],
        capture_output=True, text=True,
    )
    print(r.stdout.strip())
    if r.returncode != 0:
        print(f"RESTORE: roteiro restaurado ainda reprovado pelo GateDurance "
              f"(exit {r.returncode}). Rode o autocorrect/loop antes do TTS.")
        return 1
    print("RESTORE: OK — roteiro aprovado pronto para TTS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
