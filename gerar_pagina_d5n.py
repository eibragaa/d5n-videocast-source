#!/usr/bin/env python3
"""
gerar_pagina_d5n.py — Gera site D5N estilo telejornal premium.
- Tipografia: DM Serif Display (títulos) + Inter (corpo)
- Hierarquia: notícia principal destacada, demais compactas
- Player inline no topo com áudio do dia
- Bloco "Brief Executivo — premium"
- Dark mode calibrado com cores intencionais
"""

import os, sys, re, json, argparse
from datetime import datetime, timedelta

BASE = "/root/repositorio/d5n-videocast-source"
AUDIO_DIR = f"{BASE}/audio"
ARQUIVO_DIR = f"{BASE}/2026"
DATE = datetime.now().strftime("%Y-%m-%d")

PILARES_META = {
    "Global":   {"icon": "🌍", "cor": "#3B82F6", "bg": "#1E2D4A", "label": "GLOBAL"},
    "Brasil":   {"icon": "🇧🇷", "cor": "#22C55E", "bg": "#1A3A28", "label": "BRASIL"},
    "Tech":     {"icon": "🤖", "cor": "#A855F7", "bg": "#2D1B4E", "label": "TECH & IA"},
    "Economia": {"icon": "💰", "cor": "#F59E0B", "bg": "#3D2A10", "label": "ECONOMIA"},
}

def load_today_news(date_str, silent=False):
    path = f"/root/.hermes/cron/output/drop5news-trends-{date_str}.txt"
    if not os.path.exists(path):
        if not silent:
            print(f"⚠️  Trends não encontrados: {path}")
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    noticias = []
    sections = re.split(r'=== (\w+) ===', content)
    current_pilar = ""
    pilar_map = {'GLOBAL': 'Global', 'BRASIL': 'Brasil', 'TECH': 'Tech',
                 'ECONOMIA': 'Economia', 'ECON': 'Economia'}
    for i, part in enumerate(sections):
        part = part.strip()
        if part in pilar_map:
            current_pilar = pilar_map[part]
        elif part and len(part) > 20:
            for line in part.split('\n'):
                line = line.strip()
                if not line or line.startswith('='): continue
                if re.match(r'^[\U0001f44d\U0001f4ac]', line): continue
                if line.startswith('🔗') or line.startswith('http'): continue
                if len(line) > 25 and not line.startswith('[') and not line.startswith('r/'):
                    titulo = re.sub(r'\s+\d{1,2}h\s*$', '', line).strip()[:120]
                    noticias.append({
                        'pilar': current_pilar,
                        'titulo': titulo,
                        'descricao': '',
                        'fonte': 'D5N Pipeline',
                    })
    return noticias[:20]

def format_data_br(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    dias = {0:'Segunda-feira',1:'Terça-feira',2:'Quarta-feira',3:'Quinta-feira',
            4:'Sexta-feira',5:'Sábado',6:'Domingo'}
    meses = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
             7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
    return f"{dias[d.weekday()]}, {d.day} de {meses[d.month]} de {d.year}"

def find_latest_podcast():
    if not os.path.isdir(AUDIO_DIR):
        return None
    mp3s = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')], reverse=True)
    if not mp3s:
        return None
    latest = mp3s[0]
    path = f"{AUDIO_DIR}/{latest}"
    dur = 0
    try:
        import subprocess
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10)
        dur = round(float(r.stdout.strip()))
    except:
        dur = 0
    return {"file": latest, "path": f"/audio/{latest}", "duration": dur,
            "dur_str": f"{dur//60}:{dur%60:02d}"}

def list_episodes():
    if not os.path.isdir(AUDIO_DIR):
        return []
    mp3s = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')], reverse=True)
    eps = []
    for f in mp3s:
        path = f"{AUDIO_DIR}/{f}"
        dur = 0
        try:
            import subprocess
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10)
            dur = round(float(r.stdout.strip()))
        except:
            dur = 0
        eps.append({"file": f, "path": f"/audio/{f}",
                    "dur_str": f"{dur//60}:{dur%60:02d}", "duration": dur})
    return eps

def gerar_html(date, data_br, noticias, podcast, episodios):
    n = len(noticias)

    # ── Player ──
    player_html = ""
    if podcast:
        player_html = f"""
    <div class="player-wrap">
      <div class="player-inner">
        <div class="player-meta">
          <span class="player-label">🎙️ Episódio do Dia</span>
          <span class="player-dur">{podcast['dur_str']}</span>
        </div>
        <div class="player-bar">
          <audio controls preload="metadata">
            <source src="{podcast['path']}" type="audio/mpeg">
          </audio>
          <a href="{podcast['path']}" class="dl-btn" download title="Download MP3">⬇</a>
        </div>
      </div>
    </div>"""

    # ── Notícias por pilar ──
    por_pilar = {}
    for ntc in noticias:
        por_pilar.setdefault(ntc['pilar'] or 'Global', []).append(ntc)

    cards_html = ""
    for pilar, lista in por_pilar.items():
        meta = PILARES_META.get(pilar, {"icon":"📰","cor":"#888","bg":"#222","label":pilar})
        # Primeira = destaque
        primeira = lista[0]
        demais = lista[1:]
        items_destaque = f"""
          <div class="headline-wrap">
            <span class="headline-num">01</span>
            <div class="headline-content">
              <strong class="headline-title">{primeira['titulo']}</strong>
              <span class="headline-src">{primeira.get('fonte','D5N')}</span>
            </div>
          </div>"""
        items_compacto = ""
        for i, ntc in enumerate(demais, 2):
            items_compacto += f"""
          <div class="compact-item">
            <span class="compact-num">{i:02d}</span>
            <span class="compact-title">{ntc['titulo']}</span>
          </div>"""

        cards_html += f"""
      <div class="pilar-card" style="--acc:{meta['cor']};--bgc:{meta['bg']}">
        <h3 class="pilar-label">{meta['icon']} {meta['label']}</h3>
        {items_destaque}
        {items_compacto}
      </div>"""

    if not cards_html:
        cards_html = '<p class="empty">📭 Nenhuma notícia hoje ainda.</p>'

    # ── Ticker ──
    ticker_items = " • ".join(n['titulo'] for n in noticias[:15]) if noticias else "Aguardando..."

    # ── Premium teaser ──
    premium_html = """
    <div class="premium-teaser">
      <span class="premium-icon">🔒</span>
      <div class="premium-text">
        <strong>Brief Executivo</strong>
        <p>Análise aprofundada e contexto completo de cada notícia. Acesso reservado.</p>
      </div>
    </div>"""

    # ── Histórico ──
    historico_html = ""
    if episodios:
        rows = "".join(f"""
          <a href="{ep['path']}" class="ep-row">
            <span>{ep['file'].replace('.mp3','')}</span>
            <span class="ep-dur">{ep['dur_str']}</span>
            <span class="ep-play">▶</span>
          </a>""" for ep in episodios)
        historico_html = f"""
    <section class="historico">
      <h2>📻 Episódios</h2>
      <div class="ep-list">{rows}</div>
    </section>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="DropFiveNews — Curadoria diária de notícias. Ouça o podcast, leia as headlines.">
  <meta property="og:title" content="DropFiveNews — {data_br}">
  <meta property="og:description" content="{n} notícias em {len(por_pilar)} pilares.">
  <meta property="og:url" content="https://d5n-daily.netlify.app/">
  <meta name="color-scheme" content="dark">
  <title>DropFiveNews — {data_br}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
      font-family: 'Inter', -apple-system, system-ui, sans-serif;
      background: #08081A;
      color: #E2E2E8;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      min-height: 100vh;
    }}
    .wrapper {{ max-width: 900px; margin: 0 auto; padding: 28px 20px 80px; }}

    /* ── HEADER ── */
    .site-header {{
      text-align: center;
      padding: 32px 0 20px;
      border-bottom: 1px solid #1A1A30;
      margin-bottom: 28px;
    }}
    .site-header h1 {{
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 2.4em; font-weight: 400;
      color: #E94560; letter-spacing: -0.3px;
    }}
    .site-header h1 em {{ font-style: italic; color: #FFE66D; }}
    .site-header .date {{
      font-size: 0.85em; color: #6B6B80; margin-top: 6px;
    }}
    .site-header .sub {{
      font-size: 0.8em; color: #4A4A60; letter-spacing: 1.5px;
      text-transform: uppercase; margin-top: 2px;
    }}

    /* ── PLAYER ── */
    .player-wrap {{
      margin-bottom: 28px;
    }}
    .player-inner {{
      background: #0F0F2A;
      border: 1px solid #2A2A4A;
      border-radius: 12px;
      padding: 16px 20px;
    }}
    .player-meta {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 10px;
    }}
    .player-label {{ font-size: 0.85em; font-weight: 600; color: #8AB4F8; }}
    .player-dur {{ font-size: 0.8em; color: #6B6B80; font-variant-numeric: tabular-nums; }}
    .player-bar {{
      display: flex; gap: 10px; align-items: center;
    }}
    .player-bar audio {{ flex: 1; height: 36px; border-radius: 6px; }}
    .dl-btn {{
      display: inline-flex; align-items: center; justify-content: center;
      width: 36px; height: 36px; border-radius: 8px;
      background: #E94560; color: #fff; text-decoration: none;
      font-size: 1em; flex-shrink: 0;
    }}
    .dl-btn:hover {{ background: #D13450; }}

    /* ── NOTÍCIAS — 2 colunas ── */
    .news-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 24px;
    }}
    .pilar-card {{
      background: linear-gradient(180deg, var(--bgc) 0%, #0A0A20 100%);
      border-radius: 12px;
      padding: 18px;
      border: 1px solid color-mix(in srgb, var(--acc) 25%, transparent);
    }}
    .pilar-label {{
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1em; font-weight: 400;
      color: var(--acc);
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid color-mix(in srgb, var(--acc) 20%, transparent);
    }}

    /* Headline destaque */
    .headline-wrap {{
      display: flex; gap: 10px;
      margin-bottom: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(255,255,255,0.04);
    }}
    .headline-num {{
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.6em; color: var(--acc);
      line-height: 1; opacity: 0.5;
      min-width: 28px;
    }}
    .headline-content {{ flex: 1; }}
    .headline-title {{
      display: block; font-size: 0.92em; font-weight: 600;
      line-height: 1.4; color: #F0F0F5;
      margin-bottom: 4px;
    }}
    .headline-src {{
      font-size: 0.72em; color: #5A5A70; letter-spacing: 0.3px;
      text-transform: uppercase;
    }}

    /* Itens compactos */
    .compact-item {{
      display: flex; gap: 8px; align-items: baseline;
      padding: 5px 0;
    }}
    .compact-num {{
      font-size: 0.7em; color: var(--acc); opacity: 0.4;
      min-width: 18px; font-variant-numeric: tabular-nums;
    }}
    .compact-title {{
      font-size: 0.82em; color: #A0A0B5; line-height: 1.35;
    }}
    .empty {{ color: #5A5A70; text-align: center; padding: 40px;
              grid-column: 1 / -1; }}

    /* ── PREMIUM TEASER ── */
    .premium-teaser {{
      display: flex; gap: 14px; align-items: flex-start;
      background: linear-gradient(135deg, #1A1A30 0%, #12122A 100%);
      border: 1px solid #2A2A4A;
      border-radius: 10px;
      padding: 16px 20px;
      margin-bottom: 24px;
    }}
    .premium-icon {{ font-size: 1.2em; line-height: 1.4; }}
    .premium-text {{ flex: 1; }}
    .premium-text strong {{
      display: block; font-size: 0.85em; color: #FFE66D;
      margin-bottom: 2px;
    }}
    .premium-text p {{
      font-size: 0.78em; color: #6B6B80; margin: 0;
    }}

    /* ── HISTÓRICO ── */
    .historico {{ margin-bottom: 20px; }}
    .historico h2 {{
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.1em; font-weight: 400; color: #8AB4F8;
      margin-bottom: 10px;
    }}
    .ep-list {{ display: flex; flex-direction: column; gap: 4px; }}
    .ep-row {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 8px 14px; border-radius: 8px;
      background: #0F0F25; border: 1px solid #1A1A3A;
      text-decoration: none; color: #A0A0B5; font-size: 0.82em;
    }}
    .ep-row:hover {{ border-color: #E94560; }}
    .ep-dur {{ color: #5A5A70; }}
    .ep-play {{ color: #E94560; font-size: 0.9em; }}

    /* ── TICKER ── */
    .ticker-wrap {{
      position: fixed; bottom: 0; left: 0; right: 0; height: 34px;
      background: #0A0A20;
      border-top: 1px solid #2A2A4A;
      overflow: hidden; z-index: 100;
    }}
    .ticker {{
      display: flex; white-space: nowrap;
      animation: marquee 40s linear infinite;
    }}
    .ticker:hover {{ animation-play-state: paused; }}
    .ticker-item {{
      display: inline-flex; align-items: center;
      padding: 0 20px; font-size: 0.78em; color: #8AB4F8; height: 34px;
      opacity: 0.8;
    }}
    .ticker-item::before {{ content: "•"; margin-right: 8px; color: #E94560; }}
    @keyframes marquee {{
      0%   {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}

    /* ── FOOTER ── */
    .site-footer {{
      text-align: center; padding: 20px 0 50px;
      color: #3A3A50; font-size: 0.75em;
    }}
    .site-footer a {{ color: #E94560; text-decoration: none; }}

    /* ── RESPONSIVO ── */
    @media (max-width: 640px) {{
      .wrapper {{ padding: 16px 12px 70px; }}
      .site-header h1 {{ font-size: 1.6em; }}
      .news-grid {{ grid-template-columns: 1fr; }}
      .player-bar {{ flex-direction: column; }}
      .player-bar audio {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="wrapper">

    <header class="site-header">
      <h1>DROP <em>Five</em> NEWS</h1>
      <p class="date">{data_br}</p>
      <p class="sub">Curadoria Diária</p>
    </header>

    {player_html}

    <div class="news-grid">
      {cards_html}
    </div>

    {premium_html}

    {historico_html}

    <footer class="site-footer">
      <p><a href="https://instagram.com/ojeanbraga.s">@ojeanbraga.s</a> &middot; {n} notícias</p>
    </footer>

  </div>

  <div class="ticker-wrap">
    <div class="ticker">
      <span class="ticker-item">{ticker_items}</span>
      <span class="ticker-item">{ticker_items}</span>
      <span class="ticker-item">{ticker_items}</span>
      <span class="ticker-item">{ticker_items}</span>
    </div>
  </div>
</body>
</html>"""
    return html

def gerar_source_md(date, data_br, noticias):
    if not noticias:
        return None
    md = f"""# DROP FIVE NEWS — Boletim Diário
## {data_br}

INSTRUÇÕES (LEIA ANTES DE APRESENTAR):
- Idioma: português brasileiro (NÃO use português de Portugal)
- Contexto: Você é um apresentador de boletim de rádio. Apresente APENAS as notícias abaixo.
- NÃO analise, avalie ou comente sobre o site, o projeto, a curadoria ou as fontes.
- NÃO mencione NotebookLM, GitHub, feeds, JSON, RSS ou qualquer estrutura técnica.
- Organize por blocos temáticos na ordem abaixo.
- Use linguagem natural, coloquial brasileira, como um locutor de rádio.
- Cada bloco começa com uma transição curta entre os temas.

"""
    pilares = {'Global': '🌍 GLOBAL', 'Brasil': '🇧🇷 BRASIL',
               'Tech': '🤖 TECH & IA', 'Economia': '💰 ECONOMIA & CRYPTO'}
    current = ''
    idx = 1
    for n in noticias:
        p = n.get('pilar', '')
        if p != current:
            current = p
            md += f'\n### {pilares.get(p, p)}\n\n'
        md += f'{idx}. {n["titulo"]}\n\n'
        idx += 1
    return md

def main():
    parser = argparse.ArgumentParser(description='Gera site D5N')
    parser.add_argument('--data', default=DATE)
    parser.add_argument('--no-podcast', action='store_true')
    args = parser.parse_args()

    date = args.data
    data_br = format_data_br(date)

    noticias = load_today_news(date)

    podcast = None if args.no_podcast else find_latest_podcast()
    episodios = list_episodes() if not args.no_podcast else []

    os.makedirs(ARQUIVO_DIR, exist_ok=True)

    html = gerar_html(date, data_br, noticias, podcast, episodios)
    with open(f"{BASE}/index.html", 'w') as f:
        f.write(html)
    print(f"✅ index.html — {len(html)} bytes, {len(noticias)} notícias")

    # source.md
    md = gerar_source_md(date, data_br, noticias)
    if md:
        with open(f"{BASE}/source.md", 'w') as f:
            f.write(md)
        print(f"✅ source.md — {len(md)} bytes")

    # Markdown diário
    md_daily = f"# DropFiveNews • {data_br}\n\n"
    for n in noticias:
        md_daily += f"## [{n.get('pilar','')}] {n['titulo']}\n\n{n.get('descricao', '')}\n\n"
    with open(f"{ARQUIVO_DIR}/{date}.md", 'w') as f:
        f.write(md_daily)
    print(f"✅ 2026/{date}.md — {len(md_daily)} bytes")

    print(f"\n📊 {len(noticias)} notícias, {len(episodios)} episódios")
    print(f"🌐 https://d5n-daily.netlify.app/")

if __name__ == '__main__':
    main()
