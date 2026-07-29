#!/usr/bin/env python3
"""Gera podcast.xml — feed RSS de áudio para players externos (Apple Podcasts, Spotify, etc.)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(os.environ.get("D5N_BASE", Path(__file__).resolve().parent.parent))
BASE_URL = "https://d5n-daily.netlify.app"
IMAGE_URL = f"{BASE_URL}/podcast-cover.png"
COUNTER = REPO / "episode-counter.json"
OUTPUT = REPO / "podcast.xml"
MANIFEST_FILE = REPO / "episode-manifest.json"

CHANNEL_DESC = (
    "Curadoria diária de notícias em áudio. O D5N entrega todos os dias um "
    "resumo sonoro com as notícias mais relevantes do Brasil e do mundo — "
    "direto, sem enrolação."
)

ITUNES_CATEGORIES = """\
<itunes:category text="News">
  <itunes:category text="Daily News"/>
</itunes:category>
<itunes:category text="Technology"/>"""

PODCAST_LOCKED = """\
<podcast:locked owner="eibragaa@gmail.com">yes</podcast:locked>
<podcast:guid>d5n-daily.netlify.app</podcast:guid>
<podcast:funding url="https://github.com/sponsors/eibragaa">Support D5N</podcast:funding>"""


def load_episode_manifest() -> dict:
    """Load episode manifest if available, for richer descriptions."""
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def get_duration(mp3: Path) -> tuple[str, int, int] | None:
    """Return (itunes_duration, size_bytes, duration_sec) or None."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
         "-of", "json", str(mp3)],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return None
    data = json.loads(r.stdout)
    dur_sec = float(data["format"]["duration"])
    size = int(data["format"]["size"])
    h, rem = divmod(int(dur_sec), 3600)
    m, s = divmod(rem, 60)
    itunes_dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    return itunes_dur, size, int(dur_sec)


def main() -> None:
    if not COUNTER.exists():
        print("❌ episode-counter.json não encontrado", file=sys.stderr)
        sys.exit(1)

    counter = json.loads(COUNTER.read_text())
    manifests = load_episode_manifest()
    episodes = []

    for ep in reversed(counter["history"]):  # newest first
        mp3 = REPO / "audio" / ep["file"]
        if not mp3.exists():
            continue
        info = get_duration(mp3)
        if info is None:
            continue
        itunes_dur, size, dur_sec = info
        dt = datetime.strptime(ep["date"], "%Y-%m-%d")
        pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S -0400")
        ep_url = f"{BASE_URL}/audio/{ep['file']}"

        # Stable GUID using date-based UUID
        guid = f"d5n-{ep['date']}-ep{ep['num']}"

        # Build description with headline count and source URL
        desc = (
            f"Drop Five News — Episódio #{ep['num']} • {ep['date']}. "
            f"Ouça o resumo de notícias do dia com curadoria inteligente. "
            f"🎧 {dur_sec // 60}:{dur_sec % 60:02d} min."
        )
        desc_escaped = escape(desc)

        # content:encoded with HTML for richer display in some players
        content_html = (
            f"<p><strong>D5N • Episódio #{ep['num']}</strong></p>"
            f"<p>📅 {ep['date']}</p>"
            f"<p>🎧 {dur_sec // 60}:{dur_sec % 60:02d} minutos de curadoria diária</p>"
            f"<p>{escape(desc)}</p>"
            f"<p>👉 <a href=\"{BASE_URL}/\">Ouça no site</a></p>"
        )

        episodes.append(f"""    <item>
      <title>D5N • Episódio #{ep['num']} — {ep['date']}</title>
      <itunes:title>D5N • Episódio #{ep['num']} — {ep['date']}</itunes:title>
      <itunes:episode>{int(ep['num'])}</itunes:episode>
      <itunes:season>1</itunes:season>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:duration>{itunes_dur}</itunes:duration>
      <itunes:image href="{IMAGE_URL}"/>
      <guid isPermaLink="false">{guid}</guid>
      <link>{BASE_URL}/</link>
      <enclosure url="{ep_url}" length="{size}" type="audio/mpeg"/>
      <pubDate>{pub_date}</pubDate>
      <description>{desc_escaped}</description>
      <itunes:summary>{desc_escaped}</itunes:summary>
      <content:encoded><![CDATA[{content_html}]]></content:encoded>
    </item>""")

    if not episodes:
        print("❌ Nenhum episódio com áudio encontrado", file=sys.stderr)
        sys.exit(1)

    last_build = datetime.now().strftime("%a, %d %b %Y %H:%M:%S -0400")
    year = datetime.now().year
    items_xml = "\n".join(episodes)
    channel_desc = escape(CHANNEL_DESC)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:googleplay="http://www.google.com/schemas/play-podcasts/1.0"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>Drop Five News</title>
    <link>{BASE_URL}/</link>
    <language>pt-br</language>
    <description>{channel_desc}</description>
    <itunes:subtitle>Curadoria diária de notícias em áudio</itunes:subtitle>
    <itunes:summary>{channel_desc}</itunes:summary>
    <itunes:author>Jean Braga</itunes:author>
    <itunes:owner>
      <itunes:name>Jean Braga</itunes:name>
      <itunes:email>eibragaa@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:image href="{IMAGE_URL}"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:keywords>notícias,brasil,mundo,política,economia,tecnologia,podcast,diário,resumo</itunes:keywords>
    <itunes:type>episodic</itunes:type>
    <itunes:complete>No</itunes:complete>
    {ITUNES_CATEGORIES}
    {PODCAST_LOCKED}
    <atom:link href="{BASE_URL}/podcast.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{last_build}</lastBuildDate>
    <image>
      <url>{IMAGE_URL}</url>
      <title>Drop Five News</title>
      <link>{BASE_URL}/</link>
      <width>3000</width>
      <height>3000</height>
    </image>
    <copyright>© {year} Drop Five News</copyright>
    <webMaster>eibragaa@gmail.com (Jean Braga)</webMaster>
    <generator>D5N Pipeline v2</generator>
{items_xml}
  </channel>
</rss>"""

    OUTPUT.write_text(rss)
    print(f"✅ podcast.xml — {len(rss):,} bytes, {len(episodes)} episódios")
    print(f"📡 {BASE_URL}/podcast.xml")


if __name__ == "__main__":
    main()
