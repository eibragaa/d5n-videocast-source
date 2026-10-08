#!/usr/bin/env python3
"""Valida manifests D5N antes de irem ao TTS.

Catches the failure mode that actually happens: texto em portugues com palavras
estranhas coladas no meio (outro idioma, CJK, resto de um racunio). Tudo isso
passa pelo TTS e vai ao ar.

Uso: python3 validar-manifests.py <dir> [<dir> ...]
Sai != 0 se qualquer secao falhar.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

MIN_CHARS = 120
MAX_CHARS = 2600
# O mixer exige 480-720s de NARRACAO. Taxa real medida no RK3229 com
# ThalitaMultilingualNeural: 7258 chars -> 478.7s = 15.2 chars/s.
# (o gerador assumia ~14 e produzia episodio curto demais, barrado pelo mixer)
IDEAL = (7200, 10000)

SECTIONS = ("coldopen", "intro", "mundo", "brasil", "tecnologia", "economia",
            "interacao", "ofertas", "frase", "recomendacoes", "historia", "outro")

# Palavras PT-BR legítimas que contém Sequências não-ASCII (não é erro).
OK_NON_ASCII = set("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇºª—–…“”‘’•")

# Detecta lixo: ideogramas, cirílico, grego, árabe, hebraico, coreano, etc.
BAD_RANGES = [
    (0x2E80, 0x9FFF),    # CJK + kana
    (0xAC00, 0xD7AF),    # hangul
    (0x0400, 0x04FF),    # cirílico
    (0x0370, 0x03FF),    # grego
    (0x0600, 0x06FF),    # árabe
    (0x0590, 0x05FF),    # hebraico
    (0x0900, 0x097F),    # devanagari
]

# Sequências UTF-8 mojibake: replacement char e latin-1 estendidotypical.
MOJIBAKE = re.compile(r"[�ÃÂ][\x80-\xbf\u0080-\u00ff]?")

# Palavras que quase sempre indicam texto corrompido ou não revisado.
SUSPECT = re.compile(
    r"\b(?:"                  # início de palavra
    r"trending|placeholder|lorem|ipsum|todo|xxx+|asdf|qwerty|"  # ruído
    r"government|governments|republicans|republicano|ingles|english|"
    r"watch|looking|people|team|make|made|about|their|start|"
    r"the|and|for|with|from|this|that|what|when|here|"
    r"\w+ed\b|\w+ing\b"
    r")\b", re.I)


def bad_chars(text: str) -> list[str]:
    out = []
    for ch in text:
        cp = ord(ch)
        if ch in OK_NON_ASCII or ch.isascii():
            continue
        if any(lo <= cp <= hi for lo, hi in BAD_RANGES):
            try:
                name = unicodedata.name(ch)
            except ValueError:
                name = f"U+{cp:04X}"
            out.append(f"{ch!r} ({name})")
    return out


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errs = []
    n = len(text.strip())

    if n < MIN_CHARS:
        errs.append(f"curto demais: {n} chars (min {MIN_CHARS})")
    if n > MAX_CHARS:
        errs.append(f"longo demais: {n} chars (max {MAX_CHARS})")

    bad = bad_chars(text)
    if bad:
        uniq = sorted(set(bad))
        errs.append(f"caracteres de outro alphabeto: {', '.join(uniq[:8])}")

    if MOJIBAKE.search(text):
        errs.append(f"mojibake: {MOJIBAKE.search(text).group(0)!r}")

    sus = SUSPECT.findall(text)
    if sus:
        errs.append(f"palavras suspectas (ruido/ingles/gerundio): {sorted(set(sus))[:10]}")

    if not text.strip().endswith((".", "!", "?", '"', "”")):
        errs.append("não termina com pontuação")

    errs.extend(check_dates(text, path))
    errs.extend(check_gate_rules(text, path))

    return errs


DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Regex do quality gate para CTA fora do encerramento. Falso positivo conhecido:
# a palavra "Instagram" numa NOTICIA (Meta limitando uso por menores) casa com
# o regex, e o gate nao distingue noticia de CTA. Ao escrever a secao, prefira
# "redes sociais" / "aplicativo de mensagens" para nao perder a manchete.
CTA_RE = re.compile(r"instagram|siga|segue a gente|me segue", re.I)
GOODBYE_RE = re.compile(r"\b(?:tchau|até amanhã|até mais|valeu|falou)\b", re.I)


def check_gate_rules(text: str, path: Path) -> list[str]:
    errs = []
    stem = path.stem
    if stem != "outro" and CTA_RE.search(text):
        m = CTA_RE.search(text)
        errs.append(f"CTA fora do encerramento ({m.group(0)!r}) — o quality gate barra")
    if stem not in {"intro", "outro"} and GOODBYE_RE.search(text):
        errs.append("despedida intermediaria — o quality gate barra")
    return errs


def check_dates(text: str, path: Path) -> list[str]:
    """O editorial usa a data da PASTA. Dia da semana e mes citados no texto
    precisam bater com ela — o gerador automatico erra os dois."""
    errs = []
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", path.parent.name)
    if not m:
        return errs
    y, mo, d = (int(x) for x in m.groups())
    try:
        editorial = date(y, mo, d)
    except ValueError:
        return [f"nome da pasta nao e uma data: {path.parent.name}"]

    # O editorial vai de 07/10/2026. Meses citados referem-se ao passado
    # ("caiu em setembro") e sao legítimos; so reclamamos quando o texto
    # AFFIRMA que o dia de hoje e aquele mes ("hoje e setembro", "nesta
    # quinta-feira", "amanha, 12 de setembro").
    hoje_mes = MESES[editorial.month - 1]
    low = text.lower()
    for w in MESES:
        if w in low and w != hoje_mes and re.search(
            rf"(hoje|ontem|amanh[ãa]\s*,?\s*\d{{1,2}}\s+de|nesta?n?\s+\w+\s*,\s*\d{{1,2}}\s+de)\s+{w}\b",
            low,
        ):
            errs.append(f"afirma que HOJE e '{w}', mas o editorial e {hoje_mes}")
    # Segunda=0 ... Domingo=6
    real_dia = DIAS[editorial.weekday()]
    for dia in DIAS:
        if dia in low and dia != real_dia:
            errs.append(f"citando '{dia}' mas o editorial e {real_dia}")
    # Data ISO crua no meio do texto lido em voz alta.
    if DATE_RE.search(text):
        errs.append(f"data ISO crua no texto falado: {DATE_RE.search(text).group(0)}")
    return errs


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv[1:]]
    if not dirs:
        dirs = [Path("/home/mxqpro/repo/d5n/manifests/d5n/2026-10-07")]

    total = 0
    failed = 0
    for d in dirs:
        if not d.is_dir():
            print(f"\n{d}: PASTA AUSENTE")
            failed += 1
            continue
        print(f"\n{'='*70}\n{d}\n{'='*70}")
        sizes = []
        for name in SECTIONS:
            p = d / f"{name}.txt"
            if not p.exists():
                print(f"  FALTA   {name}.txt")
                failed += 1
                continue
            sizes.append(len(p.read_text(encoding="utf-8").strip()))
            errs = check(p)
            if errs:
                failed += 1
                print(f"  REPROVADO  {name}.txt")
                for e in errs:
                    print(f"       - {e}")
            else:
                print(f"  ok       {name}.txt  ({len(p.read_text().strip())} chars)")
        total += sum(sizes)
        lo, hi = IDEAL
        verdict = "ok" if lo <= total <= hi else "FORA DA FAIXA IDEAL"
        print(f"\n  total roteiro: {total} chars (~{total/14:.0f}s falado) — {verdict}")

    print(f"\n{'='*70}")
    print("VALIDAÇÃO: OK" if not failed else f"VALIDAÇÃO: {failed} problema(s)")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))