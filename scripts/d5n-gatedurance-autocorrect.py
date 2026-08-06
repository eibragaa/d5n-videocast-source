#!/usr/bin/env python3
"""GateDurance Autocorrect — auto-correção DETERMINÍSTICA do roteiro em texto.

Corrige automaticamente os artefatos mecânicos que o GateDurance rejeita, SEM
gastar tokens de LLM. Depois de corrigir, re-valida com o GateDurance.

O que este script NUNCA faz:
  - Não traduz inglês para português (isso exige LLM → deixa o erro visível).
  - Não inventa conteúdo (não aumenta palavra count para atingir o mínimo).
  - Não altera a data editorial nem inventa notícias.

O que este script SEMPRE faz (quando presente):
  1. Remove marcações de leitura entre parênteses: (hum...), (pausa), (pensando)...
  2. Remove numeração por extenso: "1 (um)" → "1".
  3. Remove emojis e símbolos do texto falado.
  4. Remove URLs e markdown ([Fonte original](URL), **negrito**, _itálico_).
  5. Colapsa reticências espaçadas ("olha . . ." → "olha...").
  6. Remove numeradores/marcadores de lista no início de linha ("1.", "-", "*").
  7. Garante que "Drop Five News" aparece em algum segmento (adiciona no outro).
  8. Garante que o outro.txt termina com "Bom dia!" (se faltar, anexa).

Uso: python3 d5n-gatedurance-autocorrect.py [--audio-dir /tmp/d5n_audio] [--date YYYY-MM-DD]
Saída: exit 0 = aprovado (GateDurance verde); exit 1 = ainda bloqueado (mostra o que exige LLM).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GATEDURANCE = SCRIPT_DIR / "d5n-gatedurance-script-gate.py"

# Marcadores de leitura entre parênteses que o TTS lê literalmente.
HESITATION = re.compile(
    r"\(\s*(?:hum{1,6}\.?\s*\.{0,4}|hmm{1,4}\.?\s*\.{0,4}|pausa\.?\.{0,3}|"
    r"pensando?\.?\.{0,3}|hesita(?:ndo)?\.?\.{0,3}|respir(?:a|ando)\.?\.{0,3}|"
    r"tosse\.?\.{0,3}|riso?s?\.?\.{0,3}|sil[eê]ncio\.?\.{0,3}|"
    r"murmur[ao]\.?\.{0,3}|barulho\.?\.{0,3}|\b[ae]h[m]?\b\.?\.{0,3})\s*\)",
    re.I,
)
# Numeração por extenso: "1 (um)", "2. (dois)".
NUMBER_BY_EXTENSION = re.compile(
    r"(\b\d{1,3}\s*[.)]?)\s*\(\s*(?:um|dois|tr[êe]s|quatro|cinco|seis|sete|oito|nove|"
    r"dez|onze|doze|treze|quatorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte)\s*\)",
    re.I,
)
EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D\u231A-\u23FA]"
)
# URL pura.
URL = re.compile(r"https?://\S+")
# Markdown: [texto](url) e negrito/itálico/código.
MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MARKDOWN_EMPH = re.compile(r"\*{1,3}|_{1,3}|`{1,3}")
# Numerador/marcador de lista no início de linha.
LIST_BULLET = re.compile(r"^\s*(?:\d{1,3}[.)]\s+|\*\s+|-+\s+)")
SPACED_ELLIPSIS = re.compile(r"\s*\.\s*\.\s*\.")
DROP_FIVE = re.compile(r"drop five news", re.I)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in normalized if not unicodedata.combining(c)).split())


def autocorrect(text: str) -> str:
    """Aplica as correções mecânicas num bloco de texto. Nunca inventa conteúdo."""
    if not text:
        return text
    text = HESITATION.sub("", text)
    text = NUMBER_BY_EXTENSION.sub(r"\1", text)
    text = EMOJI.sub("", text)
    text = URL.sub("", text)
    text = MARKDOWN_LINK.sub(r"\1", text)
    text = MARKDOWN_EMPH.sub("", text)
    text = SPACED_ELLIPSIS.sub("...", text)
    # Reticências normalizadas (o TTS lê bem).
    text = re.sub(r"\s*\.\.\.\s*", " ... ", text)
    lines = [re.sub(LIST_BULLET, "", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines).strip()


def run_gate(audio_dir: Path, editorial_date: date) -> tuple[int, list[str]]:
    proc = subprocess.run(
        ["python3", str(GATEDURANCE), "--date", editorial_date.isoformat(), "--audio-dir", str(audio_dir)],
        capture_output=True, text=True,
    )
    errors = []
    for line in proc.stdout.splitlines():
        if line.startswith("- "):
            errors.append(line[2:])
    return proc.returncode, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-dir", default="/tmp/d5n_audio")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir)
    editorial_date = date.fromisoformat(args.date)
    txts = sorted(audio_dir.glob("*.txt"))

    # Backup dos arquivos originais (nunca destrói o roteiro bruto).
    for path in txts:
        backup = audio_dir / (path.stem + ".raw.txt")
        if not backup.exists():
            backup.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

    applied: list[str] = []
    for path in txts:
        original = path.read_text(encoding="utf-8", errors="replace")
        fixed = autocorrect(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            applied.append(path.name)

    # Garantia 7: "Drop Five News" em algum segmento (adiciona no outro.txt).
    outro_path = audio_dir / "outro.txt"
    all_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in txts)
    if not DROP_FIVE.search(all_text) and outro_path.exists():
        outro = outro_path.read_text(encoding="utf-8", errors="replace").rstrip()
        outro = (outro + "\n" if outro else "") + "Este foi o Drop Five News de hoje."
        outro_path.write_text(outro + "\n", encoding="utf-8")
        applied.append("outro.txt (+nome oficial)")

    # Garantia 8: outro termina com "Bom dia!".
    if outro_path.exists():
        outro = outro_path.read_text(encoding="utf-8", errors="replace").rstrip()
        if not re.search(r"\bbom dia[!.]?\s*$", _fold(outro)):
            outro = re.sub(r"\s*$", "", outro)
            outro = outro + " Bom dia!"
            outro_path.write_text(outro + "\n", encoding="utf-8")
            applied.append("outro.txt (+Bom dia!)")

    rc, errors = run_gate(audio_dir, editorial_date)
    report = {
        "ok": rc == 0,
        "date": editorial_date.isoformat(),
        "corrections_applied": applied,
        "remaining_errors": errors,
    }
    if args.json:
        print(__import__("json").dumps(report, ensure_ascii=False, indent=2))
    elif rc == 0:
        print(f"OK (GateDurance autocorrect): {editorial_date.isoformat()} aprovado após auto-correção")
        if applied:
            print("  correções aplicadas: " + ", ".join(applied))
    else:
        print("AINDA BLOQUEADO (GateDurance autocorrect): restam erros que exigem regeneração LLM")
        for error in errors:
            print(f"- {error}")
        print("ACÃO: regenere o texto das seções apontadas (traduzir inglês, escrever mais conteúdo, "
              "corrigir data) e re-execute este autocorrect + GateDurance.")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
