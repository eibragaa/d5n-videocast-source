#!/usr/bin/env python3
"""Escreve um manifest D5N e REJEITA o texto se estiver corrompido.

Motivo:Several vezes o texto saiu com palavras de outro idioma coladas
("governments", "班级sheet", "Candidates") ou CJK infiltrado. Tudo isso passa
pelo TTS e vai ao ar. Este helper falha ANTES de gravar.

Uso:
    python3 escrever-manifest.py <secao> <data-editorial>
    (texto vem do stdin)

Ou como modulo:
    from escrever_manifest import write_section
"""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

REPO = Path("/home/mxqpro/repo/d5n")
OK_NON_ASCII = set("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇºª—–…“”‘’•")

BAD_RANGES = [(0x2E80, 0x9FFF), (0xAC00, 0xD7AF), (0x0400, 0x04FF),
              (0x0370, 0x03FF), (0x0600, 0x06FF), (0x0590, 0x05FF),
              (0x0900, 0x097F), (0xFF01, 0xFFEF)]

DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")

# Palavras que NUNCA devem aparecer num roteiro PT-BR falado. A lista veio de
# erros reais commits deste pipeline.
BANNED = re.compile(
    r"\b("
    r"governments?|republicans?|republicano|president[s]?|senator[s]?|"
    r"congress|house|whitehouse|governor|mayor|"
    r"candidates?|candidate|team|people|start|started|about|their|"
    r"the|and|for|with|from|this|that|what|when|here|there|"
    r"students?|teachers?|school[s]?|voters?|voting|"
    r"reuters|bloomberg|cnn|bbc|"
    r"adjust\w*|taught|looking|looking|watching|making|getting|"
    r"\w+ing\b"
    r")\b", re.I)


def validate(text: str, editorial: date) -> list[str]:
    errs: list[str] = []
    n = len(text.strip())

    bad = []
    for ch in text:
        cp = ord(ch)
        if ch in OK_NON_ASCII or ch.isascii():
            continue
        if any(lo <= cp <= hi for lo, hi in BAD_RANGES):
            try:
                nm = unicodedata.name(ch)
            except ValueError:
                nm = f"U+{cp:04X}"
            bad.append(f"{ch!r} ({nm})")
    if bad:
        errs.append(f"caracteres de outro alfabeto: {sorted(set(bad))[:6]}")

    hits = sorted(set(m.group(0) for m in BANNED.finditer(text)))
    if hits:
        errs.append(f"palavras proibidas (ruido PT-BR): {hits[:12]}")

    low = text.lower()
    real = DIAS[editorial.weekday()]
    for d in DIAS:
        if d in low and d != real:
            errs.append(f"'{d}' mas o editorial e {real}")
    for m in MESES:
        if m in low and m != MESES[editorial.month - 1] and re.search(
            rf"(hoje|ontem|amanh[ãa]\s*,?\s*\d{{1,2}}\s+de|nesta?n?\s+\w+\s*,\s*\d{{1,2}}\s+de)\s+{m}\b", low
        ):
            errs.append(f"afirma que HOJE e '{m}', mas e {MESES[editorial.month - 1]}")

    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", text):
        errs.append("data ISO crua no texto falado")
    if not text.strip().endswith((".", "!", "?", '"', "”")):
        errs.append("nao termina com pontuacao")
    if n < 100:
        errs.append(f"curto demais: {n} chars")
    return errs


def write_section(section: str, editorial: date, text: str, quiet: bool = False) -> Path:
    errs = validate(text, editorial)
    if errs:
        raise SystemExit(
            f"REJEITADO {section} ({editorial}):\n  - " + "\n  - ".join(errs)
        )
    dest = REPO / "manifests" / "d5n" / editorial.isoformat() / f"{section}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text.strip() + "\n", encoding="utf-8")
    if not quiet:
        print(f"ok {section}.txt  ({len(text.strip())} chars)")
    return dest


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    section, iso = sys.argv[1], sys.argv[2]
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        editorial = date(y, m, d)
    except (ValueError, TypeError):
        print(f"data invalida: {iso}")
        return 1
    write_section(section, editorial, sys.stdin.read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())