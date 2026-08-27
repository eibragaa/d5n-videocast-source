#!/usr/bin/env python3
"""
Pre-flight validation for D5N podcast feeds.
Prevents publishing feeds with broken enclosures or missing metadata.

Usage:
    python3 scripts/validate_feeds.py              # all feeds
    python3 scripts/validate_feeds.py --feed D5N   # single feed
    python3 scripts/validate_feeds.py --strict     # fail on warnings too

Exit codes:
    0 = all OK
    1 = one or more failures
    2 = invalid arguments
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import NamedTuple


class Result(NamedTuple):
    feed: str
    status: str  # PASS | FAIL | WARN
    episodes: int
    errors: int
    warnings: int
    details: list[str]


REPO = Path(__file__).parent.parent
BASE_URL = "https://d5n-daily.netlify.app"

FEEDS = {
    "D5N": {
        "file": REPO / "podcast.xml",
        "live": f"{BASE_URL}/podcast.xml",
        "mp3_base": f"{BASE_URL}/audio/",
    },
    "MC": {
        "file": REPO / "manha-conectada.xml",
        "live": f"{BASE_URL}/manha-conectada.xml",
        "mp3_base": f"{BASE_URL}/manha-conectada/audio/",
    },
    "FM": {
        "file": REPO / "fechamento.xml",
        "live": f"{BASE_URL}/fechamento.xml",
        "mp3_base": f"{BASE_URL}/fechamento/audio/",
    },
}

TIMEOUT = 5  # seconds per request


def check_mp3(url: str) -> tuple[bool, str]:
    """Returns (ok, message)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.getcode()
            if status == 200:
                return True, f"HTTP 200 ({resp.headers.get('Content-Length', '?')} bytes)"
            return False, f"HTTP {status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"ERR: {type(e).__name__}"


def validate_feed(key: str, config: dict, strict: bool = False) -> Result:
    """Validate a single feed XML file."""
    path = config["file"]
    errors: list[str] = []
    warnings: list[str] = []

    # ── Read XML ──────────────────────────────────────────────
    if not path.exists():
        return Result(key, "FAIL", 0, 1, 0, [f"File not found: {path}"])

    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        return Result(key, "FAIL", 0, 1, 0, [f"XML parse error: {e}"])

    ns: dict[str, str] = {}
    for prefix, uri in root.attrib.items():
        if prefix.startswith("xmlns"):
            ns[prefix.split("}", 1)[-1] if "}" in prefix else prefix] = uri

    # ── Channel-level checks ─────────────────────────────────
    channel = root.find("channel")
    if channel is None:
        return Result(key, "FAIL", 0, 1, 0, ["No <channel> element"])

    # ttl
    ttl_el = channel.find("ttl")
    if ttl_el is not None and ttl_el.text:
        warnings.append(f"ttl={ttl_el.text.strip()} (recommend 60)")
    else:
        if strict:
            warnings.append("Missing <ttl> — aggregators may cache indefinitely")

    # itunes:image (channel) — search all namespaces
    img = None
    for ns_prefix, ns_uri in ns.items():
        if "itunes" in ns_prefix or "itunes" in ns_uri:
            img = channel.find(f"{{{ns_uri}}}image")
            if img is not None:
                break
    if img is None and strict:
        warnings.append("Missing channel-level itunes:image")

    # ── Episode checks ────────────────────────────────────────
    items = channel.findall("item")
    if not items:
        warnings.append("No episodes found")

    SAMPLE = 5
    mp3_ok = 0
    mp3_bad = 0

    for item in items[:SAMPLE]:
        title_el = item.find("title")
        title = title_el.text[:50] if title_el is not None and title_el.text else "NO TITLE"

        enc = item.find("enclosure")
        if enc is None:
            errors.append(f"[{title}] MISSING enclosure")
            continue

        url = enc.get("url", "")
        if not url or not url.endswith(".mp3"):
            continue

        ok, msg = check_mp3(url)
        if ok:
            mp3_ok += 1
        else:
            mp3_bad += 1
            errors.append(f"[{title}] MP3 404: {url.split('/')[-1]}")

    if len(items) > SAMPLE:
        warnings.append(f"Sample: {SAMPLE}/{len(items)} episodes checked")

    # ── Count chapters (sample) ──────────────────────────────
    chapters = 0
    for item in items[:SAMPLE]:
        for ns_val in ns.values():
            if item.find(f"{{{ns_val}}}chapter") is not None:
                chapters += 1
                break

    # ── Determine status ─────────────────────────────────────
    status = "PASS"
    if mp3_bad > 0:
        status = "FAIL"
    elif errors:
        status = "WARN"

    details = []
    if mp3_ok:
        details.append(f"{mp3_ok} MP3s OK")
    if mp3_bad:
        details.append(f"{mp3_bad} MP3s FAIL")
    if chapters:
        details.append(f"{chapters}+ episodes with chapters")
    else:
        details.append("no chapter markers (sample)")

    return Result(key, status, len(items), mp3_bad, len(warnings), errors + details)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate D5N podcast feeds")
    parser.add_argument("--feed", choices=["D5N", "MC", "FM"], help="Validate only this feed")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--live", action="store_true", help="Validate live Netlify URLs instead of local files")
    args = parser.parse_args()

    targets = {args.feed: FEEDS[args.feed]} if args.feed else FEEDS

    all_pass = True
    results: list[Result] = []

    for name, config in targets.items():
        if args.live:
            # Replace file path with downloaded content
            import tempfile
            try:
                with urllib.request.urlopen(config["live"], timeout=TIMEOUT) as resp:
                    content = resp.read().decode()
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
                    tmp.write(content)
                    config = dict(config)
                    config["file"] = Path(tmp.name)
            except Exception as e:
                print(f"❌ {name}: LIVE FETCH FAILED — {e}")
                all_pass = False
                continue

        result = validate_feed(name, config, strict=args.strict)
        results.append(result)

    # ── Print summary ────────────────────────────────────────
    max_name = max(len(r.feed) for r in results)
    max_detail = max(len(", ".join(r.details)) for r in results)

    print("=" * 70)
    print(f"{'FEED':<{max_name}}  {'STATUS':<6}  {'EPISODES':>8}  {'MP3_OK':>6}  {'MP3_ERR':>7}  DETAILS")
    print("-" * 70)

    for r in results:
        icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[r.status]
        ok = r.episodes - r.errors
        print(
            f"{r.feed:<{max_name}}  {icon}{r.status:<4}  "
            f"{r.episodes:>8}  {ok:>6}  {r.errors:>7}  {', '.join(r.details[:2])}"
        )
        if r.errors > 0:
            for err in r.details[:5]:
                print(f"           ↳ {err}")

    print("=" * 70)

    if all(r.status == "PASS" for r in results):
        print(f"✅ ALL {len(results)}/{len(results)} feeds PASS")
        return 0
    elif any(r.status == "FAIL" for r in results):
        print(f"❌ {sum(1 for r in results if r.status=='FAIL')} feed(s) FAIL — DO NOT PUSH")
        return 1
    else:
        print(f"⚠️  {sum(1 for r in results if r.status=='WARN')} feed(s) WARN — review recommended")
        return 0


if __name__ == "__main__":
    sys.exit(main())
