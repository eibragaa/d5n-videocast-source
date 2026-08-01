#!/usr/bin/env python3
"""Babysitter silenciosa da MANHÃ CONECTADA."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

REPO = Path("/root/repositorio/d5n-videocast-source")
FEED = REPO / "manha-conectada.xml"
PUBLIC_FEED = "https://d5n-daily.netlify.app/manha-conectada.xml"
TZ = ZoneInfo("America/Sao_Paulo")
now = datetime.now(TZ)
day = now.date()

if day.weekday() >= 5:
    raise SystemExit(0)
try:
    data = json.loads(urllib.request.urlopen(f"https://brasilapi.com.br/api/feriados/v1/{day.year}", timeout=12).read())
    if any(x.get("date") == day.isoformat() for x in data):
        raise SystemExit(0)
except SystemExit:
    raise
except Exception:
    pass

manifest = REPO / "manifests" / "manha-conectada" / f"{day.isoformat()}.json"
issues: list[str] = []
try:
    m = json.loads(manifest.read_text())
    audio = Path(m["output"])
    if not audio.exists() or audio.stat().st_size < 500_000:
        issues.append("MP3 ausente")
    if m.get("date") != day.isoformat():
        issues.append("data editorial divergente")
    if m.get("voice") != "pt-BR-AntonioNeural":
        issues.append("voz divergente")
    metrics = m.get("audio", {})
    duration = float(metrics.get("duration", 0))
    lufs = float(metrics.get("lufs", 99))
    peak = float(metrics.get("true_peak_dbtp", 99))
    if not 225 <= duration <= 390:
        issues.append("duração fora da faixa")
    if not -17.5 <= lufs <= -14.5:
        issues.append("loudness fora da faixa")
    if peak > -1.0:
        issues.append("true peak inseguro")
    if audio.exists():
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)], capture_output=True, text=True)
        if probe.returncode != 0:
            issues.append("MP3 ilegível")
except Exception:
    issues.append("manifesto ausente ou inválido")

def feed_contains(feed_data: bytes) -> bool:
    root = ET.fromstring(feed_data)
    expected_guid = f"manha-conectada-{day.isoformat()}"
    expected_audio = f"manha-conectada-{day.isoformat()}.mp3"
    for item in root.findall("./channel/item"):
        enclosure = item.find("enclosure")
        if (item.findtext("guid") or "").strip() != expected_guid or enclosure is None:
            continue
        audio_name = Path(unquote(urlparse(enclosure.get("url", "")).path)).name
        return audio_name == expected_audio and enclosure.get("type") == "audio/mpeg"
    return False

try:
    if not feed_contains(FEED.read_bytes()):
        issues.append("RSS local sem a edição do dia")
except (OSError, ET.ParseError):
    issues.append("RSS local ausente ou inválido")

try:
    request = urllib.request.Request(PUBLIC_FEED, headers={"User-Agent": "D5N-Manha-Babysitter/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200 or not feed_contains(response.read()):
            issues.append("RSS público sem a edição do dia")
except (OSError, ET.ParseError):
    issues.append("RSS público indisponível ou inválido")

if issues:
    print("⚠️ MANHÃ CONECTADA — " + "; ".join(issues))
    raise SystemExit(1)
raise SystemExit(0)
