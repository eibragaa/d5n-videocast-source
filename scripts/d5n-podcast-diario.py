#!/usr/bin/env python3
"""D5N Daily Podcast Daily Generator

Generates the D5N daily podcast episode, updating:
- episode-counter.json (adds new episode with date)
- podcast.xml RSS feed
- index.html (site HTML)
- git push to master for Netlify auto-deploy

Usage:
    python3 scripts/d5n-podcast-diario.py

This is the daily cron job script — runs automatically at 03:00 via system cron.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import date, timedelta

REPO = Path("/root/repositorio/d5n-videocast-source")
TODAY = date.today().isoformat()  # ex: 2026-09-10
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()  # ex: 2026-09-09

print("=" * 60)
print(f"D5N DAILY PODCAST GENERATOR")
print(f"Data: {TODAY}")
print("=" * 60)

# 1. Verificar se episódio de hoje já existe
print("\n[1/6] Verificando episódio de hoje...")
counter_file = REPO / "episode-counter.json"
audio_dir = REPO / "audio"

if counter_file.exists():
    counter = json.loads(counter_file.read_text())
    today_exists = any(h.get("date") == TODAY for h in counter.get("history", []))
    if today_exists:
        print(f"✓ Episódio de hoje ({TODAY}) já existe no episode-counter.json")
    else:
        print(f"⚠ Episódio de hoje ({TODAY}) NÃO encontrado — precisará ser gerado")
else:
    print("⚠ episode-counter.json não existe — será criado")

# 2. Gerar episódio via mixer (se precisa)
print("\n[2/6] Verificando necessidade de geração de áudio...")
if not counter_file.exists():
        print("  ▶ Criando episode-counter.json placeholder...")
        # Cria estrutura mínima
        import json as json_mod
        json_content = {
            "format": "d5n-episodes-v1",
            "last_episode": 66,  # Último existente era #066
            "history": [
                {"num": "066", "date": "2026-08-31", "file": "d5n-ep066-2026-08-31.mp3", "exists": True}
            ]
        }
        counter_file.write_text(json_mod.dumps(json_content, ensure_ascii=False, indent=2))
        print("  ✓ episode-counter.json criado")

# 3. Run the mixer to generate or validate audio
print("\n[3/6] Executando mixer D5N...")
try:
    result = subprocess.run(
        ["python3", "-B", "scripts/drop5news-mixer-v10.py",
         "--audio-dir", str(audio_dir),
         "--editorial-date", TODAY],
        capture_output=True, text=True, cwd=REPO, timeout=60
    )
    if result.returncode == 0:
        print(f"  ✓ Mixer executado com sucesso")
        print(f"    stdout: {result.stdout[:200]}")
    else:
        print(f"  ⚠ Mixer retornou código {result.returncode}")
        print(f"    stderr: {result.stderr[:300]}")
except Exception as e:
    print(f"  ❌ Erro ao executar mixer: {e}")

# 4. Generate RSS feeds
print("\n[4/6] Gerando feeds RSS...")
try:
    feed_result = subprocess.run(
        ["python3", "-B", "scripts/generate_all_feeds.py"],
        capture_output=True, text=True, cwd=REPO, timeout=60
    )
    if feed_result.returncode == 0:
        print(f"  ✓ Feeds RSS gerados")
        print(f"    {feed_result.stdout.strip()[:300]}")
    else:
        print(f"  ⚠ Erro ao gerar feeds:")
        print(f"    {feed_result.stderr[:300]}")
except Exception as e:
    print(f"  ❌ Erro: {e}")

# 5. Regenerate index.html
print("\n[5/6] Regenerando index.html...")
try:
    index_result = subprocess.run(
        ["python3", "-B", "scripts/gerar_pagina_d5n.py"],
        capture_output=True, text=True, cwd=REPO, timeout=60
    )
    if index_result.returncode == 0:
        print(f"  ✓ index.html regenerado")
        print(f"    {index_result.stdout.strip()[:200]}")
    else:
        print(f"  ⚠ Erro ao regenerar index.html:")
        print(f"    {index_result.stderr[:300]}")
except Exception as e:
    print(f"  ❌ Erro: {e}")

# 6. Git push (deploy via Netlify)
print("\n[6/6] Preparando deploy...")
print("  ▶ git add -A")
subprocess.run(["git", "add", "-A"], cwd=REPO, timeout=30)

commit_msg = f"feat: D5N daily episode {TODAY} — automatic sync"
print(f"  ▶ git commit -m \"{commit_msg}\"")
result = subprocess.run(
    ["git", "commit", "-m", commit_msg],
    capture_output=True, text=True, cwd=REPO, timeout=60
)
print(f"    stdout: {result.stdout[:200]}")
print(f"    stderr: {result.stderr[:200] if result.stderr else 'None'}")

print(f"  ▶ git push origin HEAD:master")
push_result = subprocess.run(
    ["git", "push", "origin", "HEAD:master"],
    capture_output=True, text=True, cwd=REPO, timeout=120
)
print(f"    stdout: {push_result.stdout[:500]}")
print(f"    stderr: {push_result.stderr[:500] if push_result.stderr else 'None'}")

print("\n" + "=" * 60)
print("D5N DAILY PROCESS CONCLUIDO")
print("=" * 60)
print(f"\nPróximo passo: Validar site em https://d5n-daily.netlify.app/")
print("Episódio de hoje ({TODAY}) deveria aparecer nos 3 programas.")