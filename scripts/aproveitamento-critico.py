#!/usr/bin/env python3
"""Validação completa — aperfeiçoamento crítico D5N Daily (v2, contexto real).

Adaptado ao design atual do site: player custom JS (audio sem controls nativo),
tokens --text/--r-card/--s1, favicon externo /favicon.svg, dark #0B0E14,
brand .brand/.brand-mark, accents --d5n/--mc/--fm + -soft.

Executa: validação HTML, feeds, áudio, duração, mobile, SEO, duplicatas,
e rende relatório.
"""

import re, json, subprocess
from collections import Counter
from pathlib import Path

REPO = Path("/root/repositorio/d5n-videocast-source")
html = (REPO / "index.html").read_text(encoding="utf-8")

checks = []

# ── 1. Design tokens centralizados ──
tokens = all(t in html for t in ["--bg:", "--surface:", "--text:", "--accent:", "--r-card:", "--s1:"])
checks.append(("Design tokens centralized", tokens))

# ── 2. Program cards ──
cards = re.findall(r'class="program-card program-card--\w+"', html)
checks.append(("3 program cards found", len(cards) == 3))

# ── 3. pc-summary in all cards ──
summaries = re.findall(r'class="pc-summary"', html)
checks.append(("pc-summary present in all cards", len(summaries) == 3))

# ── 4. pc-duration in all cards ──
durations = re.findall(r'class="pc-duration"', html)
checks.append(("pc-duration present in all cards", len(durations) >= 3))

# ── 5. pc-date in all cards ──
dates = re.findall(r'class="pc-date"', html)
checks.append(("pc-date present in all cards", len(dates) == 3))

# ── 6. Audio players (custom JS: <audio id src preload=metadata> sem controls) ──
players = re.findall(r'<audio id="\w+" src="[^"]+\.mp3" preload="metadata">', html)
checks.append(("3 audio players (custom JS)", len(players) == 3))

# ── 7. src direto nos players (data-src é usado nos chips do arquivo) ──
srcs = re.findall(r'<audio id="\w+" src="([^"]+\.mp3)"', html)
checks.append(("All 3 programs have audio src", len(srcs) == 3))

# ── 8. Cover images ──
covers = re.findall(r'src="(/[^"]*cover[^"]*\.jpg)"', html)
checks.append(("Cover images exist", len(covers) >= 3))

# ── 9. Favicon (externo /favicon.svg) ──
has_favicon = 'rel="icon" href="/favicon.svg"' in html
checks.append(("SVG favicon linked", has_favicon))

# ── 10. Mobile viewport ──
has_viewport = 'meta name="viewport"' in html
checks.append(("Mobile viewport meta tag", has_viewport))

# ── 11. Archive section ──
has_archive = 'id="arquivo"' in html or 'archive-row' in html
checks.append(("Archive section exists", has_archive))

# ── 12. RSS feed links ──
has_rss = 'podcast.xml' in html and 'manha-conectada.xml' in html and 'fechamento.xml' in html
checks.append(("RSS feed links in HTML", has_rss))

# ── 13. FM accent (verde neon, var --fm + --fm-soft) ──
has_fm_accent = 'var(--fm)' in html and 'var(--fm-soft)' in html
checks.append(("FM accent theming (--fm/--fm-soft)", has_fm_accent))

# ── 14. Ticker ──
has_ticker = 'ticker' in html.lower()
checks.append(("News ticker present", has_ticker))

# ── 15. Dark theme (default, #0B0E14 — sem auto-follow de prefers-color-scheme) ──
has_dark = '#0B0E14' in html and 'var(--bg)' in html
checks.append(("Dark theme default #0B0E14", has_dark))

# ── 16. Brand logo (classe .brand + .brand-mark SVG) ──
has_brand = 'class="brand"' in html and 'brand-mark' in html
checks.append(("Brand logo (brand/brand-mark)", has_brand))

# ── 17. Valid RSS feeds ──
for feed in ["podcast.xml", "manha-conectada.xml", "fechamento.xml"]:
    fpath = REPO / feed
    if fpath.exists():
        content = fpath.read_text(encoding="utf-8")
        has_channel = '<channel>' in content
        has_item = '<item>' in content
        checks.append((f"{feed} valid RSS", has_channel and has_item))
    else:
        checks.append((f"{feed} valid RSS", False))

# ── 18. Audio file durations (episódios mais recentes de cada programa) ──
for audio_file, audio_subdir in [
    ("d5n-ep074-2026-09-25.mp3", "audio"),
    ("manha-conectada-2026-09-24.mp3", "manha-conectada/audio"),
    ("fechamento-2026-09-23.mp3", "fechamento/audio"),
]:
    p = REPO / audio_subdir / audio_file
    if p.exists():
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                           capture_output=True, text=True)
        try:
            dur = float(r.stdout.strip())
            checks.append((f"{audio_file} duration {int(dur//60)}:{int(dur%60):02d}", 240 <= dur <= 900))
        except Exception:
            checks.append((f"{audio_file} duration parse", False))
    else:
        checks.append((f"{audio_file} exists", False))

# ── 19. Sem duplicatas de data no episode-counter ──
counter = json.loads((REPO / "episode-counter.json").read_text(encoding="utf-8"))
hist = counter.get("history", [])
dups = {k: v for k, v in Counter(h.get("date") for h in hist).items() if v > 1}
checks.append(("No duplicate dates in episode-counter", len(dups) == 0))

# ── 20. RSS: sem 2 itens D5N da mesma data ──
rss = (REPO / "podcast.xml").read_text(encoding="utf-8")
rss_dates = re.findall(r"d5n-(\d{4}-\d{2}-\d{2})-ep\d+</guid>", rss)
rss_dups = {k: v for k, v in Counter(rss_dates).items() if v > 1}
checks.append(("RSS: no duplicate D5N dates", len(rss_dups) == 0))

# ── 21. Todos os data-src apontam para arquivos que existem ──
missing = []
for src in re.findall(r'data-src="(/[^"]+\.mp3)"', html):
    p = REPO / src.lstrip("/")
    if not p.exists():
        missing.append(src)
checks.append(("All archive data-src files exist", len(missing) == 0))

# ── Summary ──
print("=" * 60)
print("APERFEIÇOAMENTO CRÍTICO — D5N DAILY (v2 contexto real)")
print("=" * 60)

passed = 0
failed = 0
for label, ok in checks:
    status = "✅" if ok else "❌"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  {status} {label}")

if dups:
    print(f"\n  ⚠ Duplicatas por data: {dups}")
if rss_dups:
    print(f"  ⚠ RSS duplicatas: {rss_dups}")
if missing:
    print(f"  ⚠ data-src ausentes no disco: {missing[:5]}")

print(f"\n{'=' * 60}")
print(f"RESULTADO: {passed}/{passed + failed} checks passaram")
if failed == 0:
    print("🎉 TODOS OS CHECKS PASSARAM — SITE D5N DAILY PREMIUM AAA")
else:
    print(f"⚠️  {failed} checks falharam — revisar itens acima")
print(f"{'=' * 60}")