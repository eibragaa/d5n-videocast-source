#!/usr/bin/env python3
"""Publica um episodio D5N no site — com trava anti-feed-vazio.

Por que existe: `gerar_podcast_feed.py` so lista episodios cujo MP3 existe
LOCALMENTE (`if not mp3.exists(): continue`). Num checkout sparse — onde
audio/ tem ~770 MB que nao estao em disco — ele produz um podcast.xml com
1 item em vez de 61. Se esse arquivo for commitado, o feed publico perde 60
episodios de uma vez.

Medido em 07/10/2026: rodando o gerador isolado, saiu
"✅ podcast.xml — 4.946 bytes, 1 episodios". O arquivo original tem 94.746
bytes e 61 itens.

Este script compara o feed gerado com o que ja esta no git e ABORTA se o
numero de itens cair. Nao ha como publicar um feed truncado por engano.

Uso:
    python3 publicar-d5n.py                # usa o proximo episodio do contador
    python3 publicar-d5n.py --check        # so verifica, nao commita
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/mxqpro/repo/d5n")
FEED = REPO / "podcast.xml"
INDEX = REPO / "index.html"
COUNTER = REPO / "episode-counter.json"
MIN_ITEMS = 30          # o feed historico tem 61; qualquer coisa abaixo e truncamento
DROP_RATIO = 0.5        # abaixo de 50% do anterior tambem e travado

ITEM_RE = re.compile(r"<item>")


def count_items(path: Path) -> int:
    if not path.exists():
        return 0
    return len(ITEM_RE.findall(path.read_text(encoding="utf-8", errors="replace")))


def git_show(path: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{path.relative_to(REPO)}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verifica sem commitar")
    args = ap.parse_args()

    if not COUNTER.exists():
        print("X episode-counter.json ausente")
        return 1
    counter = json.loads(COUNTER.read_text())
    last = counter["history"][0]
    ep_file = f"audio/{last['file']}"
    mp3 = REPO / ep_file

    print(f"Episodio: #{last['num']} — {last['date']}")
    print(f"Audio:    {ep_file}")
    if not mp3.exists():
        print(f"X MP3 ausente localmente: {mp3}")
        return 1
    print(f"          {mp3.stat().st_size/1e6:.1f} MB")

    before = git_show(FEED)
    before_items = len(ITEM_RE.findall(before)) if before else 0
    print(f"\nFeed no git: {before_items} itens")

    print("\nGerando podcast.xml...")
    r = subprocess.run([sys.executable, "-B", str(REPO / "scripts" / "gerar_podcast_feed.py")],
                       cwd=REPO, capture_output=True, text=True, timeout=300)
    print("  " + r.stdout.strip().replace("\n", "\n  "))
    if r.returncode != 0:
        print("X gerador falhou:", r.stderr[-300:])
        return 1

    after_items = count_items(FEED)
    print(f"\nFeed gerado: {after_items} itens ({FEED.stat().st_size} bytes)")

    # ---- TRAVA ----
    if after_items < MIN_ITEMS:
        print(f"\nX BLOQUEADO: feed com {after_items} itens, minimo {MIN_ITENTS}.")
        print("  Causa quase certa: audio/ esta em checkout sparse e o gerador")
        print("  so enxerga MP3s locais. Nao commitar.")
        if before:
            FEED.write_text(before, encoding="utf-8")
            print(f"  podcast.xml restaurado do HEAD ({before_items} itens).")
        return 2
    if before_items and after_items < before_items * DROP_RATIO:
        print(f"\nX BLOQUEADO: feed caiu de {before_items} para {after_items} itens.")
        if before:
            FEED.write_text(before, encoding="utf-8")
            print(f"  podcast.xml restaurado do HEAD ({before_items} itens).")
        return 2

    print(f"\nOK trava anti-truncamento passou ({before_items} -> {after_items})")

    if args.check:
        print("\n--check: nada foi commitado.")
        return 0

    # Esta versao do gerador aceita --dry-run, nao --site-only (a skill
    # d5n-content-pipeline citava --site-only e o comando falhava).
    r2 = subprocess.run([sys.executable, "-B", str(REPO / "scripts" / "gerar_pagina_d5n.py")],
                         cwd=REPO, capture_output=True, text=True, timeout=300)
    if r2.returncode != 0:
        print("  X gerador de pagina falhou:", r2.stderr[-300:])
    else:
        print("  " + (r2.stdout.strip().splitlines() or ["(sem saida)"])[-1][:200])

    print("\nNada e publicado ainda. Para revisar o diff:")
    print(f"  cd {REPO} && git diff --stat podcast.xml index.html")
    print("\nPara commitar E publicar:")
    print(f"  cd {REPO} && git add podcast.xml index.html episode-counter.json {ep_file}")
    print(f'  git commit -m "feat: D5N #{last["num"]} {last["date"]}" && git push origin HEAD:master')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())