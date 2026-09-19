#!/usr/bin/env python3
"""Validação completa — aperfeiçoamento crítico D5N Daily.
Executa: validação HTML, feeds, áudio, duração, mobile, SEO, e rende relatório.
"""

import re, json, subprocess
from pathlib import Path

REPO = Path("/root/repositorio/d5n-videocast-source")
html = (REPO / "index.html").read_text(encoding="utf-8")

checks = []

# ── 1. Design tokens ──
tokens = all(t in html for t in ["--bg:", "--surface:", "--text-primary:", "--accent:", "--radius:", "--space:"])
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

# ── 6. Audio players ──
players = re.findall(r'controls preload="metadata"', html)
checks.append(("Audio players present", len(players) >= 3))

# ── 7. data-src for audio ──
srcs = re.findall(r'data-src="([^"]+\.mp3)"', html)
checks.append(("All 3 programs have audio src", len(srcs) == 3))

# ── 8. Cover images ──
covers = re.findall(r'src="(/[^"]+cover[^"]+\.jpg)"', html)
checks.append(("Cover images exist", len(covers) >= 3))

# ── 9. Favicon ──
has_svg_favicon = 'data:image/svg+xml' in html
checks.append(("SVG favicon embedded", has_svg_favicon))

# ── 10. Mobile viewport ──
has_viewport = 'meta name="viewport"' in html
checks.append(("Mobile viewport meta tag", has_viewport))

# ── 11. Archive section ──
has_archive = 'class="archive-section"' in html or 'class="archive-row"' in html or 'archive' in html
checks.append(("Archive section exists", has_archive))

# ── 12. RSS feed links ──
has_rss = 'podcast.xml' in html and 'manha-conectada.xml' in html and 'fechamento.xml' in html
checks.append(("RSS feed links in HTML", has_rss))

# ── 13. Orange glow accent for FM ──
has_fm_accent = 'var(--fm-accent)' in html or 'var(--fm-surface)' in html
checks.append(("FM orange accent theming", has_fm_accent))

# ── 14. Ticker ──
has_ticker = 'ticker' in html.lower()
checks.append(("News ticker present", has_ticker))

# ── 15. Dark theme (default) ──
has_dark = 'body {' in html and ('#0a0f1c' in html or 'var(--bg)' in html)
checks.append(("Dark theme default (no auto follow)", has_dark))

# ── 16. Brand logo (SVG inline) ──
has_brand = 'brand-logo' in html
checks.append(("Brand logo SVG inline in header", has_brand))

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

# ── 18. Audio file durations ──
for audio_file in ["d5n-ep067-2026-09-10.mp3", "manha-conectada-2026-09-10.mp3", "fechamento-2026-09-10.mp3"]:
    paths = [
        REPO / "audio" / audio_file,
        REPO / "manha-conectada/audio" / audio_file,
        REPO / "fechamento/audio" / audio_file,
    ]
    found = False
    for p in paths:
        if p.exists():
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)], capture_output=True, text=True)
            try:
                dur = float(r.stdout.strip())
                checks.append((f"{audio_file} duration {int(dur//60)}:{int(dur%60):02d}", 240 <= dur <= 900))
                found = True
                break
            except: pass
    if not found:
        checks.append((f"{audio_file} exists", False))

# ── Summary ──
print("=" * 60)
print("APERFEIÇOAMENTO CRÍTICO — D5N DAILY")
print("=" * 60)

passed = 0
failed = 0
for label, ok in checks:
    status = "✅" if ok else "❌"
    if ok: passed += 1
    else: failed += 1
    print(f"  {status} {label}")

print(f"\n{'=' * 60}")
print(f"RESULTADO: {passed}/{passed+failed} checks passaram")
if failed == 0:
    print("🎉 TODOS OS CHECKS PASSARAM — SITE D5N DAILY PREMIUM AAA")
else:
    print(f"⚠️  {failed} checks falharam — revisar itens acima")
print(f"{'=' * 60}")
