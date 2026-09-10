#!/usr/bin/env python3
"""Update RSS feeds and index.html after a new D5N episode is generated."""

from pathlib import Path
import subprocess
import sys

REPO = Path("/root/repositorio/d5n-videocast-source")

def run_script(script_path: Path, description: str):
    if not script_path.exists():
        print(f"  X {description}: script not found")
        return False
    print(f">>  {description}...")
    result = subprocess.run(["python3", "-B", str(script_path)], capture_output=True, text=True, cwd=REPO, timeout=120)
    if result.returncode != 0:
        print(f"   Error: {result.stderr[-500:]}")
        return False
    print(f"   OK {result.stdout.strip()}")
    return True

def main():
    print("=" * 50)
    print("POS-EPISODIO: Feeds + Index")
    print("=" * 50)
    steps = [
        (REPO / "scripts" / "generate_all_feeds.py", "Gerar todos os feeds RSS"),
        (REPO / "scripts" / "gerar_pagina_d5n.py", "Atualizar index.html"),
    ]
    results = []
    for script, desc in steps:
        ok = run_script(script, desc)
        results.append((desc, ok))
    all_ok = all(ok for _, ok in results)
    print("\nRESUMO:", "OK" if all_ok else "FALHOU")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
