#!/usr/bin/env python3
"""
d5n-trends-diario.py — Coleta RSS diária de notícias para o Drop Five News.

Gera um arquivo drop5news-trends-YYYY-MM-DD.txt com as manchetes coletadas
das fontes configuradas. Roda via cron Hermes ou sistema.

Fontes padrão (RSS):
- G1: https://g1.globo.com/dynamo/feed/tecnologia/
- Poder360
- BBC Brasil
- etc

Uso: python3 d5n-trends-diario.py [--output DIR]
"""

import sys
import json
import feedparser
import socket
import requests
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

OUTPUT_DIR = Path("/root/.hermes/cron/output")
TODAY = date.today().isoformat()


def default_sources():
    return [
        {
            "name": "G1 Tecnologia",
            "url": "https://g1.globo.com/rss/g1/tecnologia/",
        },
        {
            "name": "G1 Brasil",
            "url": "https://g1.globo.com/rss/g1/politica/",
        },
        {
            "name": "G1 Mundo",
            "url": "https://g1.globo.com/rss/g1/",
        },
        {
            "name": "G1 Economia",
            "url": "https://g1.globo.com/rss/g1/economia/",
        },
        {
            "name": "Poder360",
            "url": "https://www.poder360.com.br/feed/",
        },
        {
            "name": "InfoMoney",
            "url": "https://www.infomoney.com.br/feed/",
        },
    ]


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; D5N-Bot/1.0)"}


def fetch_feed(source):
    try:
        socket.setdefaulttimeout(15)
        resp = requests.get(source["url"], timeout=15, headers=HEADERS)
        if resp.status_code != 200:
            return [{"error": f"{source['name']}: HTTP {resp.status_code}"}]
        # Pre-process to fix HTML entities that break feedparser's XML parser
        content = resp.content
        feed = feedparser.parse(content)
        entries = []
        for entry in feed.entries[:8]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            published = getattr(entry, "published", "") or ""
            entries.append({
                "title": title,
                "url": link,
                "published": published[:16],
                "source": source["name"],
            })
        return entries
    except Exception as e:
        return [{"error": f"{source['name']}: {e}"}]


def main():
    sources = default_sources()
    print(f"D5N TRENDS — Coleta RSS diária {TODAY}")
    print(f"Fontes: {len(sources)}")
    
    output = []
    output.append(f"# TRENDS D5N — {TODAY}")
    output.append(f"# Atualizado via RSS em {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')} UTC")
    output.append(f"# Fuso editorial: America/Sao_Paulo")
    output.append("")
    output.append("=== TRENDS COLETADAS ===")
    output.append("")
    
    for source in sources:
        print(f"  Coletando {source['name']}...")
        entries = fetch_feed(source)
        output.append(f"### {source['name']}")
        output.append("")
        for e in entries:
            if "error" in e:
                output.append(f"⚠ {e['error']}")
            else:
                output.append(f"**{e['title']}**")
                output.append(f"Fonte: {e['source']} — {e['url']}")
                output.append("")
    
    out_file = OUTPUT_DIR / f"drop5news-trends-{TODAY}.txt"
    out_file.write_text("\n".join(output), encoding="utf-8")
    print(f"\nSalvo: {out_file}")


if __name__ == "__main__":
    main()
