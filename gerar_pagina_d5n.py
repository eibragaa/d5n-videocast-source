#!/usr/bin/env python3
"""
gerar_pagina_d5n.py — Gera página Netlify + feed para NotebookLM.
Lê os dados do pipeline D5N e gera:
  - index.html     (página principal, últimas notícias)
  - 2026/MM-DD.md  (notícias do dia)
  - feed.json      (feed estruturado)
  - d5n-feed.xml   (RSS alternativo)

Uso:
  python3 gerar_pagina_d5n.py --data "2026-05-27" --titulo "Quarta, 27 de Maio"

  # Sem argumentos → usa data de hoje
  python3 gerar_pagina_d5n.py
"""
import os, sys, json, argparse
from datetime import datetime

BASE = "/root/repositorio/d5n-videocast-source"
DATE = datetime.now().strftime("%Y-%m-%d")

def slug(text):
    import re
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60]

def gerar_index_html(dias):
    """Gera index.html com as últimas N páginas diárias."""
    
    # Path da capa do D5N
    cover_rel = f"/{dias[0]['date']}.png" if dias else ""
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="DropFiveNews — Curadoria diária de notícias trending. Fonte para NotebookLM VideoCast.">
  <meta name="author" content="Jean Braga — @ojeanbraga.s">
  <title>DropFiveNews • Fonte de Dados</title>
  <link rel="alternate" type="application/rss+xml" title="D5N RSS" href="/d5n-feed.xml">
  <link rel="alternate" type="application/json" title="D5N Feed" href="/feed.json">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #1A1A2E; color: #E8E8E8; line-height: 1.6; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ color: #E94560; font-size: 2.5em; margin-bottom: 8px; }}
    h2 {{ color: #FFE66D; font-size: 1.6em; margin: 30px 0 15px; 
          border-bottom: 2px solid #E94560; padding-bottom: 8px; }}
    h3 {{ color: #4ECDC4; font-size: 1.2em; margin: 20px 0 10px; }}
    .subtitle {{ color: #888; font-size: 1.1em; margin-bottom: 30px; }}
    a {{ color: #4ECDC4; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .card {{ background: #16213E; border-radius: 12px; padding: 24px; margin: 16px 0;
             border-left: 4px solid #E94560; }}
    .card h3 {{ margin-top: 0; }}
    .card .meta {{ color: #888; font-size: 0.9em; margin-bottom: 8px; }}
    .card a {{ color: #FFE66D; }}
    .pillar {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
               font-size: 0.8em; font-weight: bold; margin: 0 4px 4px 0; }}
    .pillar-global {{ background: #28527A; color: #8AB4F8; }}
    .pillar-brasil {{ background: #1A5A3C; color: #81C784; }}
    .pillar-tech {{ background: #6A1B9A; color: #CE93D8; }}
    .pillar-econ {{ background: #7A4A1A; color: #FFD54F; }}
    .day-link {{ display: block; padding: 12px 20px; margin: 8px 0;
                 background: #16213E; border-radius: 8px;
                 border: 1px solid #333; }}
    footer {{ margin-top: 60px; padding-top: 20px; border-top: 1px solid #333;
              color: #666; font-size: 0.9em; text-align: center; }}
    ul {{ list-style: none; }}
    li {{ padding: 6px 0; border-bottom: 1px solid #2A2A4A; }}
    li:last-child {{ border-bottom: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📡 DropFiveNews</h1>
    <p class="subtitle">Curadoria diária de notícias trending • Fonte oficial para NotebookLM</p>
    
    <section>
      <h2>📰 Últimas Notícias</h2>
"""
    
    for dia in dias[:3]:
        html += f"""
    <div class="card">
      <div class="meta">{dia['data_br']}</div>
      <ul>"""
        for n in dia['noticias'][:8]:
            pclass = f"pillar-{n['pilar'].lower()}" if n.get('pilar') else ""
            html += f"""
        <li><span class="pillar {pclass}">{n.get('pilar','')}</span> {n['titulo']}</li>"""
        html += """
      </ul>
    </div>"""
    
    html += """
    </section>
    
    <section>
      <h2>📅 Arquivo Diário</h2>"""
    
    for dia in dias:
        html += f"""
      <a class="day-link" href="/{dia['date']}.html">
        <strong>{dia['data_br']}</strong>
        <span style="float:right;color:#888;">{len(dia['noticias'])} notícias →</span>
      </a>"""
    
    html += """
    </section>
    
    <section>
      <h2>📡 Fontes de Dados</h2>
      <p>Esta página serve como fonte estruturada para o NotebookLM.</p>
      <ul>
        <li><a href="/d5n-feed.xml">📻 RSS Feed</a></li>
        <li><a href="/feed.json">📊 JSON Feed</a></li>
      </ul>
      <p style="margin-top:12px;color:#888;">
        <strong>Como usar no NotebookLM:</strong><br>
        Copie a URL base deste site e adicione como fonte no NotebookLM.<br>
        Ele vai ler todas as páginas e gerar o VideoCast automaticamente.
      </p>
    </section>
    
    <footer>
      <p>DropFiveNews por <a href="https://instagram.com/ojeanbraga.s">@ojeanbraga.s</a></p>
      <p>Atualizado automaticamente • {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    </footer>
  </div>
</body>
</html>
"""
    return html


def gerar_dia_html(date, data_br, noticias):
    """Gera página HTML específica do dia."""
    articles = ""
    for i, n in enumerate(noticias, 1):
        pclass = f"pillar-{n['pilar'].lower()}" if n.get('pilar') else ""
        articles += f"""
      <article>
        <h3><span class="pillar {pclass}">{n.get('pilar','')}</span> {n['titulo']}</h3>
        <p>{n.get('descricao', '')}</p>
        <p style="font-size:0.9em;color:#888;">
          Fonte: {n.get('fonte', 'D5N Pipeline')}
        </p>
      </article>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="DropFiveNews • {data_br} — Notícias diárias">
  <title>D5N • {data_br}</title>
  <link rel="canonical" href="/{date}.html">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #1A1A2E; color: #E8E8E8; line-height: 1.6; }}
    .container {{ max-width: 700px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ color: #E94560; font-size: 2em; }}
    h2 {{ color: #FFE66D; font-size: 1.3em; margin: 30px 0 10px; }}
    article {{ margin: 20px 0; padding: 16px; background: #16213E; border-radius: 8px; }}
    .pillar {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
               font-size: 0.8em; font-weight: bold; margin: 0 4px 4px 0; }}
    .pillar-global {{ background: #28527A; color: #8AB4F8; }}
    .pillar-brasil {{ background: #1A5A3C; color: #81C784; }}
    .pillar-tech {{ background: #6A1B9A; color: #CE93D8; }}
    .pillar-econ {{ background: #7A4A1A; color: #FFD54F; }}
    footer {{ margin-top: 40px; color: #666; font-size: 0.9em; }}
    a {{ color: #4ECDC4; }}
    .back {{ display: block; margin-bottom: 20px; }}
  </style>
</head>
<body>
  <div class="container">
    <a class="back" href="/">← Voltar</a>
    <h1>📰 DropFiveNews</h1>
    <h2>{data_br}</h2>
    {articles}
    <footer>
      <p>Atualizado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    </footer>
  </div>
</body>
</html>"""
    return html


def gerar_feed_json(dias):
    """Gera feed.json para NotebookLM."""
    items = []
    for dia in dias[:7]:
        items.append({
            "id": dia['date'],
            "title": f"D5N • {dia['data_br']}",
            "url": f"https://d5n-videocast.netlify.app/{dia['date']}.html",
            "date_published": dia['date'],
            "summary": f"Curadoria de {len(dia['noticias'])} notícias trending",
            "tags": ["notícias", "D5N", "curadoria"],
            "content_text": "\n".join(f"[{n.get('pilar','')}] {n['titulo']}" for n in dia['noticias'])
        })
    return json.dumps({
        "version": "https://jsonfeed.org/version/1",
        "title": "DropFiveNews - Feed de Notícias",
        "home_page_url": "https://d5n-videocast.netlify.app",
        "feed_url": "https://d5n-videocast.netlify.app/feed.json",
        "description": "Curadoria diária de notícias trending para geração de VideoCast no NotebookLM",
        "author": {"name": "Jean Braga", "url": "https://instagram.com/ojeanbraga.s"},
        "items": items
    }, ensure_ascii=False, indent=2)


def gerar_feed_rss(dias):
    """Gera RSS feed XML."""
    import xml.sax.saxutils as saxutils
    items = ""
    for dia in dias[:7]:
        desc = saxutils.escape(f"Curadoria de {len(dia['noticias'])} notícias trending: " +
                               ". ".join(n['titulo'] for n in dia['noticias'][:3]))
        items += f"""
    <item>
      <title>D5N • {saxutils.escape(dia['data_br'])}</title>
      <link>https://d5n-videocast.netlify.app/{dia['date']}.html</link>
      <guid isPermaLink="true">https://d5n-videocast.netlify.app/{dia['date']}.html</guid>
      <pubDate>{dia['date']}T03:00:00-04:00</pubDate>
      <description>{desc}</description>
    </item>"""
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DropFiveNews • RSS</title>
    <link>https://d5n-videocast.netlify.app</link>
    <description>Curadoria diária de notícias trending para NotebookLM VideoCast</description>
    <language>pt-br</language>
    <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S -0400")}</lastBuildDate>
    <atom:link href="https://d5n-videocast.netlify.app/d5n-feed.xml" rel="self" type="application/rss+xml"/>
    {items}
  </channel>
</rss>"""


def main():
    parser = argparse.ArgumentParser(description='Gera página Netlify D5N')
    parser.add_argument('--data', default=DATE, help='Data YYYY-MM-DD')
    parser.add_argument('--titulo', default=datetime.now().strftime("%A, %d de %B").replace("Monday","Segunda").replace("Tuesday","Terça").replace("Wednesday","Quarta").replace("Thursday","Quinta").replace("Friday","Sexta").replace("Saturday","Sábado").replace("Sunday","Domingo"), help='Título da data')
    parser.add_argument('--noticias', nargs='*', help='Notícias no formato "PILAR::Título::Descrição"')
    args = parser.parse_args()
    
    # Se não veio notícias, buscar do pipeline
    if not args.noticias:
        noticias = load_today_news(args.data)
    else:
        noticias = []
        for n in args.noticias:
            parts = n.split('::', 2)
            noticias.append({
                'pilar': parts[0] if len(parts) > 0 else '',
                'titulo': parts[1] if len(parts) > 1 else n,
                'descricao': parts[2] if len(parts) > 2 else '',
                'fonte': 'D5N Pipeline',
            })
    
    data_br = args.titulo
    date = args.data
    
    # Carregar dias anteriores também
    dias = [{'date': date, 'data_br': data_br, 'noticias': noticias}]
    
    # Buscar dias anteriores
    from datetime import timedelta
    for i in range(1, 3):
        d = datetime.strptime(date, '%Y-%m-%d') - timedelta(days=i)
        d_str = d.strftime('%Y-%m-%d')
        prev = load_today_news(d_str, silent=True)
        if prev:
            dias.append({'date': d_str, 'data_br': d.strftime("%A, %d de %B").replace("Monday","Segunda").replace("Tuesday","Terça").replace("Wednesday","Quarta").replace("Thursday","Quinta").replace("Friday","Sexta").replace("Saturday","Sábado").replace("Sunday","Domingo"), 'noticias': prev})
    
    # Gerar arquivos
    index_html = gerar_index_html(dias)
    dia_html = gerar_dia_html(date, data_br, noticias)
    feed_json = gerar_feed_json(dias)
    feed_rss = gerar_feed_rss(dias)
    
    # Salvar
    os.makedirs(f"{BASE}/2026", exist_ok=True)
    
    with open(f"{BASE}/index.html", 'w') as f:
        f.write(index_html)
    print(f"✅ index.html — {len(index_html)} bytes")
    
    page_file = f"{BASE}/{date}.html"
    with open(page_file, 'w') as f:
        f.write(dia_html)
    print(f"✅ {date}.html — {len(dia_html)} bytes")
    
    # Também salvar como MD (NotebookLM prefere Markdown)
    md = f"# DropFiveNews • {data_br}\n\n"
    for n in noticias:
        md += f"## [{n.get('pilar','')}] {n['titulo']}\n\n{n.get('descricao', '')}\n\n"
    md_file = f"{BASE}/2026/{date}.md"
    with open(md_file, 'w') as f:
        f.write(md)
    print(f"✅ 2026/{date}.md — {len(md)} bytes")
    
    with open(f"{BASE}/feed.json", 'w') as f:
        f.write(feed_json)
    print(f"✅ feed.json — {len(feed_json)} bytes")
    
    with open(f"{BASE}/d5n-feed.xml", 'w') as f:
        f.write(feed_rss)
    print(f"✅ d5n-feed.xml — {len(feed_rss)} bytes")
    
    print(f"\n📊 {len(noticias)} notícias do dia + {len(dias)-1} dias anteriores")
    print(f"🌐 Netlify URL base: https://d5n-videocast.netlify.app")


# Módulo auxiliar para carregar dados do pipeline D5N
if __name__ != '__main__':
    exit(0)

# Pipeline loader
def load_today_news(date_str, silent=False):
    """Carrega notícias do pipeline D5N para uma data."""
    import json, re
    path = f"/root/.hermes/cron/output/drop5news-trends-{date_str}.txt"
    if not os.path.exists(path):
        if not silent:
            print(f"⚠️  Arquivo não encontrado: {path}")
        return []
    
    with open(path) as f:
        content = f.read()
    
    # Extrair títulos com pilar
    noticias = []
    sections = re.split(r'=== (\w+) ===', content)
    current_pilar = ''
    
    for i, part in enumerate(sections):
        part = part.strip()
        if part in ('GLOBAL', 'BRASIL', 'TECH', 'ECONOMIA', 'ECON'):
            current_pilar = {
                'GLOBAL': 'Global',
                'BRASIL': 'Brasil',
                'TECH': 'Tech',
                'ECONOMIA': 'Economia',
                'ECON': 'Economia',
            }.get(part, part)
        elif part and len(part) > 20:
            # Linhas que parecem títulos
            for line in part.split('\n'):
                line = line.strip()
                if not line or line.startswith('='):
                    continue
                # Pular linhas de metadados
                if re.match(r'^[\U0001f44d\U0001f4ac]', line):
                    continue
                if line.startswith('🔗') or line.startswith('http'):
                    continue
                if len(line) > 25 and not line.startswith('[') and not line.startswith('r/'):
                    noticias.append({
                        'pilar': current_pilar,
                        'titulo': re.sub(r'\s+\d{1,2}h\s*$', '', line).strip()[:120],
                        'descricao': '',
                        'fonte': 'D5N Pipeline',
                    })
    
    return noticias[:15]

if __name__ == '__main__':
    main()
