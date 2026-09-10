#!/usr/bin/env python3
"""Validate all feeds and index.html for daily consistency.

Run after any feed generation to ensure MC, FM, D5N episodes are current.
"""
import subprocess
import re
from pathlib import Path

REPO = Path(__file__).parent.parent
TODAY = "2026-09-10"

def check_feeds():
    feeds = {
        "D5N": "podcast.xml",
        "MC": "manha-conectada.xml",
        "FM": "fechamento.xml",
    }
    for name, fname in feeds.items():
        f = REPO / fname
        if f.exists():
            content = f.read_text()
            items = len(re.findall(r'<item>', content))
            latest_match = re.search(r'<pubDate>([^<]+)</pubDate>', content)
            latest = latest_match.group(1)[:25] if latest_match else "unknown"
            print(f"  {name}: {items} eps, latest: {latest}")
        else:
            print(f"  {name}: NOT FOUND")

def check_index():
    idx = REPO / "index.html"
    if not idx.exists():
        print("  index.html: NOT FOUND")
        return
    content = idx.read_text()
    for prog, pattern in [("MC", "manha-conectada-2026-09-10"), ("FM", "fechamento-2026-09-10")]:
        if pattern in content:
            dur_match = re.search(f'{pattern}[^>]*data-duration="(\\d+)"', content)
            dur = f"{int(dur_match.group(1))//60}:{int(dur_match.group(1))%60:02d}" if dur_match else "?"
            print(f"  {prog}: hoje ({TODAY}) - {dur}")
        else:
            print(f"  {prog}: SEM EPISODIO DE HOJE ({TODAY})")

def check_audio():
    for prog, path, prefix in [
        ("D5N", "audio", "d5n-ep"),
        ("MC", "manha-conectada/audio", "manha-conectada-"),
        ("FM", "fechamento/audio", "fechamento-"),
    ]:
        d = REPO / path
        if d.exists():
            files = list(d.glob(f"{prefix}*.mp3"))
            today_files = [f for f in files if TODAY in f.name]
            if today_files:
                print(f"  {prog}: MP3 de hoje existe ({today_files[0].name})")
            else:
                print(f"  {prog}: SEM MP3 DE HOJE ({TODAY})")
        else:
            print(f"  {prog}: DIR NOT FOUND")

if __name__ == "__main__":
    print("=== FEEDS VALIDATION ===")
    check_feeds()
    print("\n=== INDEX.HTML VALIDATION ===")
    check_index()
    print("\n=== AUDIO FILES VALIDATION ===")
    check_audio()
