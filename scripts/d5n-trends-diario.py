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

TODAY = date.today().isoformat()

# O --output e anunciado no help mas nunca lido: OUTPUT_DIR ficava preso ao
# path do host antigo (/root/.hermes/...), dando Permission denied em qualquer
# install fora de root.
if "--output" in sys.argv:
    _i = sys.argv.index("--output")
    OUTPUT_DIR = Path(sys.argv[_i + 1] if _i + 1 < len(sys.argv) else ".")
OUT_FILE = OUTPUT_DIR / f"drop5news-trends-{TODAY}.txt"


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
        # Volume: com os 7 feeds acima o roteiro do dia ficava em ~6.0k chars,
        # abaixo do minimo de 7.6k (480s) do mixer. Estes 3 entram para
        # garantir materia em mundo e economia, as categorias mais fracas.
        #
        # Testei 12 candidatos em 07/10/2026 e so estes 3 devolvem itens:
        #   CNN Brasil .............. 60 itens  (ok)
        #   Folha de S.Paulo/mundo .. 100 itens  (ok)
        #   MoneyTimes ..............  10 itens  (ok)
        #   Agencia Brasil ..........  10 itens  (ok)
        # Nao respondem (0 itens): valor.globo.com/rss/, economia.estadao.com.br/rss,
        # economia.uol.com.br/feed, terra.com.br/rss/*, g1.globo.com/rss/g1/mundo,
        # g1.globo.com/rss/g1/mercado, congressonacional.leg.br, 12.senado.leg.br.
        # Nao voltar a testar os mortos sem curl -sL -A "Mozilla/5.0" | grep -c item.
        {
            "name": "CNN Brasil",
            "url": "https://www.cnnbrasil.com.br/feed/",
        },
        {
            "name": "Folha Mundo",
            "url": "https://feeds.folha.uol.com.br/mundo/rss091.xml",
        },
        {
            "name": "MoneyTimes",
            "url": "https://www.moneytimes.com.br/feed/",
        },
        {
            "name": "Agencia Brasil",
            "url": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
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
    
    out_file = OUT_FILE
    out_file.write_text("\n".join(output), encoding="utf-8")
    print(f"\nSalvo: {out_file}")


if __name__ == "__main__":
    main()
