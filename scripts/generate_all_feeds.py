#!/usr/bin/env python3
"""Generate all podcast feeds (RSS/XML) for D5N, MC, FM.

This script is a wrapper that calls each feed generator in the correct order.
It reads from the episode-counter.json and generates fresh feeds.

Usage:
    python3 generate_all_feeds.py

The feeds are written to the repo root (for Netlify) and also to each program's
subdirectory (for archival purposes).
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent

def run_script(script_path: Path, description: str):
    """Run a Python script and report its result."""
    if not script_path.exists():
        print(f"❌ {description}: script not found at {script_path}")
        return False
    
    print(f"▶️  {description}...")
    result = subprocess.run(
        ["python3", "-B", str(script_path)],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120
    )
    
    if result.returncode != 0:
        print(f"   Error: {result.stderr[-500:]}")
        return False
    
    print(f"   ✓ {result.stdout.strip()}")
    return True

def main():
    """Generate all feeds in the correct order."""
    print("=" * 50)
    print("GENERATING ALL PODCAST FEEDS")
    print("=" * 50)
    
    # Order matters: generate episode data first, then feeds
    steps = [
        (REPO / "scripts" / "gerar_podcast_feed.py", "D5N main podcast feed"),
        (REPO / "manha-conectada" / "scripts" / "gerar_manha_conectada_feed.py", "Manhã Conectada feed"),
        (REPO / "fechamento" / "scripts" / "gerar_fechamento_feed.py", "Fechamento do Mercado feed"),
    ]
    
    results = []
    for script, desc in steps:
        ok = run_script(script, desc)
        results.append((desc, ok))
        print()
    
    print("=" * 50)
    print("SUMMARY:")
    for desc, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {desc}")
    
    all_ok = all(ok for _, ok in results)
    if all_ok:
        print("\n✓ All feeds generated successfully!")
        print("\nFeeds available at:")
        print("  - https://d5n-daily.netlify.app/podcast.xml (D5N)")
        print("  - https://d5n-daily.netlify.app/manha-conectada.xml (MC)")
        print("  - https://d5n-daily.netlify.app/fechamento.xml (FM)")
    else:
        print("\n❌ Some feeds failed to generate. Check errors above.")
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())