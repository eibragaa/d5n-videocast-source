#!/usr/bin/env python3
"""Gera o RSS exclusivo da Manhã Conectada para players externos."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.sax.saxutils import escape, quoteattr
from zoneinfo import ZoneInfo

# shared chapters (MC/FM)
sys.path.insert(0, str(Path(__file__).parents[2]))
from _shared_chapters import load_program_chapters, build_chapters_rss, build_chapters_description, _fmt_dur

BASE_URL = "https://d5n-daily.netlify.app"
FEED_NAME = "manha-conectada.xml"
IMAGE_URL = f"{BASE_URL}/manha-conectada-cover.png"
TZ = ZoneInfo("America/Sao_Paulo")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CHANNEL_DESCRIPTION = (
    "Briefing de fim de manhã do Drop Five News. De segunda a sexta, Antonio "
    "resume as notícias que já definiram o dia e apresenta o Sinal 11: o que "
    "ainda pode mudar o cenário até o começo da tarde."
)


@dataclass(frozen=True)
class Episode:
    editorial_date: date
    audio_name: str
    duration: int
    size: int
    headlines: tuple[str, ...]
    chapters: list = None   # capítulos RSS (pode estar vazio)
    # type: ignore[assignment]

    def __post_init__(self):
        if self.chapters is None:
            object.__setattr__(self, 'chapters', [])

    @property
    def guid(self) -> str:
        return f"manha-conectada-{self.editorial_date.isoformat()}"

    @property
    def enclosure_url(self) -> str:
        return f"{BASE_URL}/audio/{self.audio_name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_episodes(repo: Path) -> list[Episode]:
    """Carrega somente manifestos canônicos e falha em inconsistência publicável."""
    manifest_dir = repo / "manifests"
    audio_dir = repo / "audio"
    episodes: list[Episode] = []

    for manifest_path in sorted(manifest_dir.glob("*.json")):
        if not DATE_RE.fullmatch(manifest_path.stem):
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"manifesto inválido: {manifest_path}") from exc

        if manifest.get("prototype") is not False:
            continue
        editorial_date = date.fromisoformat(manifest_path.stem)
        expected_name = f"manha-conectada-{editorial_date.isoformat()}.mp3"
        output_name = Path(str(manifest.get("output", ""))).name
        audio_path = audio_dir / expected_name
        if str(manifest.get("program", "")).strip().upper() != "MANHÃ CONECTADA":
            raise ValueError(f"programa divergente em {manifest_path}")
        if manifest.get("date") != editorial_date.isoformat():
            raise ValueError(f"data divergente em {manifest_path}")
        if output_name != expected_name:
            raise ValueError(f"saída não canônica em {manifest_path}")
        if not audio_path.is_file() or audio_path.stat().st_size < 500_000:
            raise ValueError(f"áudio ausente ou insuficiente: {audio_path}")
        expected_hash = str(manifest.get("sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError(f"sha256 ausente em {manifest_path}")
        if _sha256(audio_path) != expected_hash:
            raise ValueError(f"sha256 divergente: {audio_path}")

        duration = round(float(manifest.get("audio", {}).get("duration", 0)))
        if duration <= 0:
            raise ValueError(f"duração inválida em {manifest_path}")
        headlines = tuple(
            str(item.get("title", "")).strip()
            for item in manifest.get("sources", [])[:3]
            if str(item.get("title", "")).strip()
        )
        # Carrega capítulos derivados do roteiro
        chapters = load_program_chapters("manha-conectada", editorial_date.isoformat(), duration)

        episodes.append(
            Episode(
                editorial_date=editorial_date,
                audio_name=expected_name,
                duration=duration,
                size=audio_path.stat().st_size,
                headlines=headlines,
                chapters=chapters,
            )
        )

    if not episodes:
        raise ValueError("nenhum episódio canônico da Manhã Conectada")
    return episodes


def _duration(value: int) -> str:
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def build_feed(repo: Path) -> tuple[str, list[Episode]]:
    episodes = load_episodes(repo)
    numbered = {episode.editorial_date: number for number, episode in enumerate(episodes, 1)}
    latest = episodes[-1]
    last_build = datetime.combine(latest.editorial_date, time(11), tzinfo=TZ)
    items: list[str] = []

    for episode in reversed(episodes):
        episode_number = numbered[episode.editorial_date]
        published = datetime.combine(episode.editorial_date, time(11), tzinfo=TZ)
        date_br = episode.editorial_date.strftime("%d/%m/%Y")
        minutes, seconds = divmod(episode.duration, 60)
        description = (
            f"Manhã Conectada de {date_br}. Briefing das notícias que definiram "
            f"a manhã, com apresentação de Antonio. Duração: {minutes}:{seconds:02d}."
        )
        chapters_rss = build_chapters_rss(episode.chapters, episode.enclosure_url, episode.duration)
        chapters_desc = build_chapters_description(episode.chapters, episode.duration)
        desc_full = description + (f"\n\n📑 Capítulos:\n{chapters_desc}" if chapters_desc else "")
        headline_html = "".join(f"<li>{escape(title)}</li>" for title in episode.headlines)
        chapters_html = ""
        if episode.chapters:
            rows = "".join(
                f'<li><strong>{escape(ch["label"])}</strong> — {_fmt_dur(float(ch["start"]))}</li>'
                for ch in episode.chapters
            )
            chapters_html = f"<p>📑 <strong>Capítulos:</strong></p><ul>{rows}</ul>"
        content_html = (
            f"<p><strong>Manhã Conectada • {date_br}</strong></p>"
            f"<p>{escape(description)}</p>"
            + (f"<ul>{headline_html}</ul>" if headline_html else "")
            + chapters_html
            + f'<p><a href="{BASE_URL}/#manha-conectada">Ouça no site</a></p>'
        )
        items.append(
            f"""    <item>
      <title>Manhã Conectada — {date_br}</title>
      <itunes:title>Manhã Conectada — {date_br}</itunes:title>
      <itunes:episode>{episode_number}</itunes:episode>
      <itunes:season>1</itunes:season>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:duration>{_duration(episode.duration)}</itunes:duration>
      <itunes:image href={quoteattr(IMAGE_URL)}/>
      <guid isPermaLink="false">{episode.guid}</guid>
      <link>{BASE_URL}/#manha-conectada</link>
      <enclosure url={quoteattr(episode.enclosure_url)} length="{episode.size}" type="audio/mpeg"/>
      <pubDate>{format_datetime(published)}</pubDate>
      <description>{escape(description)}</description>
      <itunes:summary>{escape(desc_full)}</itunes:summary>
      <content:encoded><![CDATA[{content_html}]]></content:encoded>
{chapters_rss}
    </item>"""
        )

    description = escape(CHANNEL_DESCRIPTION)
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:podcast="https://podcastindex.org/namespace/1.0"
     xmlns:psrc="https://podcastindex.org/namespace/podcast/chapters"
     xmlns:psc="http://podlove.org/player's/models/chapters">
  <channel>
    <title>Manhã Conectada</title>
    <link>{BASE_URL}/#manha-conectada</link>
    <language>pt-br</language>
    <description>{description}</description>
    <itunes:subtitle>As notícias que definiram a manhã e o Sinal 11</itunes:subtitle>
    <itunes:summary>{description}</itunes:summary>
    <itunes:author>Drop Five News</itunes:author>
    <itunes:owner>
      <itunes:name>Jean Braga</itunes:name>
      <itunes:email>eibragaa@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:image href={quoteattr(IMAGE_URL)}/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:complete>no</itunes:complete>
    <itunes:category text="News">
      <itunes:category text="Daily News"/>
    </itunes:category>
    <itunes:category text="Business"/>
    <podcast:locked owner="eibragaa@gmail.com">no</podcast:locked>
    <podcast:guid>manha-conectada.d5n-daily.netlify.app</podcast:guid>
    <atom:link href="{BASE_URL}/{FEED_NAME}" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{format_datetime(last_build)}</lastBuildDate>
    <image>
      <url>{IMAGE_URL}</url>
      <title>Manhã Conectada</title>
      <link>{BASE_URL}/#manha-conectada</link>
    </image>
    <copyright>© {latest.editorial_date.year} Drop Five News</copyright>
    <generator>D5N Pipeline — Manhã Conectada</generator>
{os.linesep.join(items)}
  </channel>
</rss>"""
    return rss, episodes


def feed_has_episode(feed_data: bytes | str, editorial_date: str) -> bool:
    root = ET.fromstring(feed_data)
    expected_guid = f"manha-conectada-{editorial_date}"
    expected_audio = f"manha-conectada-{editorial_date}.mp3"
    for item in root.findall("./channel/item"):
        enclosure = item.find("enclosure")
        if (item.findtext("guid") or "").strip() != expected_guid or enclosure is None:
            continue
        audio_name = Path(unquote(urlparse(enclosure.get("url", "")).path)).name
        if audio_name == expected_audio and enclosure.get("type") == "audio/mpeg":
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(os.environ.get("MANHA_CONECTADA_ROOT", Path(__file__).parents[1])))
    parser.add_argument("--check-date")
    args = parser.parse_args()
    output = args.repo / "feeds" / FEED_NAME

    if args.check_date:
        if not DATE_RE.fullmatch(args.check_date):
            print("data inválida", file=sys.stderr)
            return 2
        try:
            valid = feed_has_episode(output.read_bytes(), args.check_date)
        except (OSError, ET.ParseError):
            valid = False
        print(json.dumps({"date": args.check_date, "feed": str(output), "published": valid}, ensure_ascii=False))
        return 0 if valid else 1

    try:
        rss, episodes = build_feed(args.repo)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rss, encoding="utf-8")
    print(f"✅ {FEED_NAME} — {len(episodes)} episódios; mais recente: {episodes[-1].editorial_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
