#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validar_design.py — Guardrail de integridade do design system D5N.

Roda em <1s, stdlib puro. Bloqueia commit/deploy se:
  1. CSS com comentarios /* nao fechados (causa real: [truncated] matou 144/157 regras)
  2. Livros "injetados" de edicao/compressao ([truncated], HERMES-CONTEXT-COMPRESSION,
     [SKILL_PRUNED], [REDACTED], marcadores de truncamento) em CSS/codigo HTML
  3. Chaves {} desbalanceadas no CSS
  4. Tokens do design system ausentes (cores, fontes, espacos)
  5. Contraste de texto abaixo de WCAG AA (muted < 4.5:1)
  6. Anatomia minima do index.html ausente (hero, grid, ticker, cards, archive, footer, JSON-LD)
  7. index.html gerado sem marcadores do gerador atual (detecta bot/processo externo
     sobrescrevendo com layout antigo)

Uso:
  python3 -B scripts/validar_design.py          # valida gerador + index.html (exit 0/1)
  python3 -B scripts/validar_design.py --quiet  # sem saida quando OK (uso em hook)

Registrar como pre-commit:
  ln -sf ../../scripts/validar_design.py .git/hooks/pre-commit
  (o script auto-detecta --hook e roda quieto, bloqueando commit se falhar)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "gerar_pagina_d5n.py"
INDEX = REPO / "index.html"

# literais de truncamento/injecao que nunca devem existir em CSS ou HTML gerado
LIXO = [
    "[truncated]",  # comentario CSS real que quebrou o site
    "[TRUNCATED]",
    "HERMES-CONTEXT-COMPRESSION",
    "[SKILL_PRUNED]",
    "[REDACTED]",
    "context compressor",
]

# tokens obrigatorios do design system
TOKENS = [
    "--bg", "--surface", "--surface-2", "--border", "--border-soft",
    "--text", "--text-2", "--muted",
    "--d5n", "--mc", "--fm", "--d5n-soft", "--mc-soft", "--fm-soft",
    "--font-display", "--font-body", "--font-mono",
    "--r-card", "--r-inner", "--r-btn",
    "--s1", "--s4", "--s6",
    "--t-fast", "--t-med", "--ease",
]

# marcadores que so o gerador atual emite (layout v2/polish)
MARCAS_GERADOR = [
    "scroll-padding-top:76px",
    'grid-template-areas:"featured side-a"',
    "linear-gradient(180deg,var(--surface-2)",
    "background-clip:text",
]

ANATOMIA = [
    ("hero", 'class="hero"'),
    ("grid", 'class="programs-grid"'),
    ("ticker", 'class="ticker-track"'),
    ("card d5n", 'program-card--d5n'),
    ("card mc", 'program-card--mc'),
    ("card fm", 'program-card--fm'),
    ("archive", 'class="archive-row'),
    ("footer", 'class="site-footer"'),
    ("json-ld", 'application/ld+json'),
    ("player", 'class="pc-player"'),
    ("menu", 'id="menuBtn"'),
]


def contraste(fg: str, bg: str) -> float:
    def lum(c: int) -> float:
        c = c / 255
        c = c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return c
    r, g, b = (int(fg[i + 1:i + 3], 16) for i in (0, 2, 4))
    r2, g2, b2 = (int(bg[i + 1:i + 3], 16) for i in (0, 2, 4))
    l1 = 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b)
    l2 = 0.2126 * lum(r2) + 0.7152 * lum(g2) + 0.0722 * lum(b2)
    lo, hi = sorted([l1, l2])
    return (hi + 0.05) / (lo + 0.05)


def extrair_css(texto: str) -> str:
    blocos = re.findall(r"<style[^>]*>(.*?)</style>", texto, re.S)
    return "\n".join(blocos)


def checar(texto: str, rotulo: str) -> list[str]:
    falhas: list[str] = []
    css = extrair_css(texto)

    # 1. comentarios balanceados (no CSS e no resto do arquivo)
    for alvo, nome in ((css, f"{rotulo} CSS"), (texto, rotulo)):
        a = len(re.findall(r"/\*", alvo))
        f = len(re.findall(r"\*/", alvo))
        if a != f:
            falhas.append(f"{nome}: {a} comentarios abertos vs {f} fechados — CSS sera descartado pelo browser")

    if css:
        # 3. chaves balanceadas no CSS
        prof: int = 0
        for ch in css:
            if ch == "{":
                prof += 1
            elif ch == "}":
                prof -= 1
                if prof < 0:
                    falhas.append(f"{rotulo}: '}}' sem '{'{'}' correspondente no CSS")
                    break
        if prof > 0:
            falhas.append(f"{rotulo}: {prof} chaves abertas sem fechar no CSS")

    # 2. lixo injetado
    for lixo in LIXO:
        for alvo, nome in ((css, f"{rotulo} CSS"),):
            if lixo in alvo:
                falhas.append(f"{rotulo}: literal injetado '{lixo}' encontrado no CSS")

    return falhas


def checar_tokens(css: str) -> list[str]:
    falhas = []
    for tok in TOKENS:
        if tok not in css:
            falhas.append(f"token do design system ausente: {tok}")
    return falhas


def checar_contraste(css: str) -> list[str]:
    falhas = []
    m = re.search(r":root\s*\{([^}]*)\}", css, re.S)
    if not m:
        return ["nao achei :root no CSS"]
    root = m.group(1)
    vars_ = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", root))
    bg = vars_.get("--bg")
    for tok in ("--muted", "--text-2", "--text"):
        cor = vars_.get(tok)
        if bg and cor:
            r = contraste(cor, bg)
            minimo = 7.0 if tok == "--text" else 4.5
            if r < minimo:
                falhas.append(f"contraste {tok} {cor} = {r:.2f}:1 (min {minimo}:1) — falha WCAG AA")
    return falhas


def main() -> int:
    quiet = "--quiet" in sys.argv or "--hook" in sys.argv
    falhas: list[str] = []

    if GEN.exists():
        src = GEN.read_text(encoding="utf-8")
        falhas += checar(src, "gerar_pagina_d5n.py")
        # gerador: CSS dentro da f-string triple — checar lixo tambem no .py inteiro
        for lixo in LIXO:
            if lixo in src:
                falhas.append(f"gerar_pagina_d5n.py: literal injetado '{lixo}'")
    else:
        falhas.append("gerar_pagina_d5n.py nao encontrado")

    if INDEX.exists():
        html = INDEX.read_text(encoding="utf-8")
        falhas += checar(html, "index.html")
        for nome, marcador in ANATOMIA:
            if marcador not in html:
                falhas.append(f"index.html: anatomia ausente ({nome})")
        for marcador in MARCAS_GERADOR:
            if marcador not in html:
                falhas.append(f"index.html: marcador do gerador atual ausente — layout antigo/bot concorrente? '{marcador}'")
        css = extrair_css(html)
        if css:
            falhas += checar_tokens(css)
            falhas += checar_contraste(css)
    else:
        falhas.append("index.html nao encontrado — rode gerar_pagina_d5n.py primeiro")

    if falhas and not quiet:
        print("FALHAS DE INTEGRIDADE DO DESIGN:")
        for f in falhas:
            print(f"  - {f}")
        print(f"\n{len(falhas)} falha(s). Corrija antes de commit/deploy.")
    if not falhas and not quiet:
        print("OK — design system integro (tokens, contraste AA, CSS parseavel, sem lixo injetado)")

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())