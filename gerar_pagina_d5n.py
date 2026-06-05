#!/usr/bin/env python3
"""
gerar_pagina_d5n.py — Gera site D5N no padrão premium do Google Drive.
Libre Baskerville + DM Sans · Ticker com dots · Player custom · Scroll-reveal
"""

import os, sys, re, json, argparse
from datetime import datetime, timedelta

BASE = "/root/repositorio/d5n-videocast-source"
AUDIO_DIR = f"{BASE}/audio"
ARQUIVO_DIR = f"{BASE}/2026"
COUNTER_FILE = f"{BASE}/episode-counter.json"

def get_last_episode_num():
    """Retorna o último número de episódio do contador persistente."""
    try:
        with open(COUNTER_FILE) as f:
            return json.load(f).get("last_episode", 0)
    except: return 0
DATE = datetime.now().strftime("%Y-%m-%d")

PILAR_MAP = {"Global":"global","Brasil":"global","Tech":"tech","Economia":"econ"}
PILAR_DOT = {"global":"dot-global","tech":"dot-tech","econ":"dot-econ"}

def load_today_news(date_str, silent=False):
    path = f"/root/.hermes/cron/output/drop5news-trends-{date_str}.txt"
    if not os.path.exists(path):
        if not silent: print(f"⚠️  Trends não encontrados: {path}")
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    noticias = []
    sections = re.split(r'=== (\w+) ===', content)
    cur = ""
    pm = {'GLOBAL':'Global','BRASIL':'Brasil','TECH':'Tech','ECONOMIA':'Economia','ECON':'Economia'}
    for i, part in enumerate(sections):
        part = part.strip()
        if part in pm:
            cur = pm[part]
        elif part and len(part) > 20:
            for line in part.split('\n'):
                line = line.strip()
                if not line or line.startswith('='): continue
                if re.match(r'^[\U0001f44d\U0001f4ac]', line): continue
                if line.startswith('🔗') or line.startswith('http'): continue
                if len(line) > 25 and not line.startswith('[') and not line.startswith('r/'):
                    titulo = re.sub(r'\s+\d{1,2}h\s*$', '', line).strip()[:120]
                    noticias.append({'pilar':cur,'titulo':titulo,'fonte':'D5N'})
    return noticias[:20]

def format_data_br(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    dias = {0:'Segunda-feira',1:'Terça-feira',2:'Quarta-feira',3:'Quinta-feira',4:'Sexta-feira',5:'Sábado',6:'Domingo'}
    meses = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
    return f"{dias[d.weekday()]}, {d.day} de {meses[d.month]} de {d.year}"

def format_data_curta(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    meses = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
    return f"{d.day} {meses[d.month]} {d.year}"

def load_episode_history():
    """Carrega o histórico completo de episódios do JSON persistente."""
    try:
        with open(COUNTER_FILE) as f:
            return json.load(f).get("history", [])
    except: return []

def get_duration(filepath):
    """Obtém duração do MP3 via ffprobe, retorna 0 em erro."""
    try:
        import subprocess
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",filepath],capture_output=True,text=True,timeout=10)
        return round(float(r.stdout.strip()))
    except: return 0

def find_latest_podcast():
    history = load_episode_history()
    if not history: return None
    latest_entry = history[-1]  # último da lista = mais recente
    f = latest_entry["file"]
    path = f"{AUDIO_DIR}/{f}"
    dur = get_duration(path) if os.path.exists(path) else 0
    return {
        "file": f,
        "path": f"/audio/{f}",
        "duration": dur,
        "dur_str": f"{dur//60}:{dur%60:02d}",
        "num": latest_entry["num"].lstrip("0") or "0"
    }

def list_episodes():
    """Lista episódios do histórico persistente (reverso, mais recente primeiro).
    Só mostra episódios que existem em audio/. Os perdidos viram placeholder
    com link desabilitado."""
    history = load_episode_history()
    eps = []
    for entry in reversed(history):
        f = entry["file"]
        path = f"{AUDIO_DIR}/{f}"
        exists = os.path.exists(path)
        dur = get_duration(path) if exists else 0
        eps.append({
            "file": f,
            "path": f"/audio/{f}",
            "dur_str": f"{dur//60}:{dur%60:02d}" if exists else "—",
            "exists": exists,
            "num": entry["num"],
            "date": entry["date"]
        })
    return eps

def gerar_html(date, data_br, data_curta, noticias, podcast, episodios):
    n = len(noticias)
    por_pilar = {}
    for ntc in noticias:
        por_pilar.setdefault(ntc['pilar'] or 'Global', []).append(ntc)

    # ── Ticker ──
    ticker_items = ""
    for ntc in noticias[:15]:
        p = ntc['pilar'] or 'Global'
        cls = PILAR_DOT.get(PILAR_MAP.get(p,'global'),'dot-global')
        ticker_items += f'<span class="ticker-item"><span class="ticker-dot {cls}"></span>{ntc["titulo"]}</span>\n    '
    ticker_dup = ticker_items

    # ── Hero stats ──
    n_pilares = len([p for p in por_pilar if p])
    pod_dur = podcast['dur_str'] if podcast else "0:00"

    # ── Player ──
    player_html = ""
    if podcast:
        player_html = f'''
    <div class="player-bar">
      <button class="play-btn" id="playBtn" onclick="togglePlay()">
        <svg id="playIcon" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
      </button>
      <div class="player-info">
        <div class="player-title">D5N Episódio #{podcast["num"]} — {data_curta}</div>
        <div class="player-progress" id="progressBar" onclick="seekAudio(event)">
          <div class="player-progress-fill" id="progressFill"></div>
        </div>
      </div>
      <span class="player-time" id="playerTime">0:00 / {podcast["dur_str"]}</span>
      <a class="player-download" href="{podcast["path"]}" download title="Baixar MP3">↓ MP3</a>
      <button class="speed-btn" id="speedBtn" onclick="cycleSpeed()" title="Velocidade">1×</button>
    </div>
    <audio id="audioEl" src="{podcast["path"]}" preload="none"></audio>'''

    # ── Notícias ──
    sections_html = ""
    idx = 0
    for pilar in ['Global','Tech','Economia']:
        lista = por_pilar.get(pilar, [])
        if not lista:
            for k,v in por_pilar.items():
                if k and k.lower() == pilar.lower():
                    lista = v; break
        # Merge Brasil into Global
        if pilar == 'Global':
            br = por_pilar.get('Brasil', [])
            if not br:
                for k,v in por_pilar.items():
                    if k and 'brasil' in k.lower():
                        br = v; break
            if br:
                lista = lista + br
        if not lista and pilar == 'Economia':
            for k,v in por_pilar.items():
                if k and ('economia' in k.lower() or 'econ' in k.lower() or 'crypto' in k.lower()):
                    lista = v; break
        if not lista: continue

        # Detect pilar name for display
        pilar_display = pilar
        if pilar == 'Economia': pilar_display = 'Economia & Crypto'
        if pilar == 'Global': pilar_display = 'Global'
        if pilar == 'Tech': pilar_display = 'Tech'

        cls_name = PILAR_MAP.get(pilar, 'global')
        icon = {'Global':'🌍','Tech':'🤖','Economia':'💰','Brasil':'🇧🇷'}.get(pilar, '📰')

        news_items = ""
        for i, ntc in enumerate(lista):
            idx += 1
            num = f"{idx:02d}"
            featured = ' featured' if i == 0 else ''
            fonte = ntc.get('fonte', 'D5N') or 'D5N'
            news_items += f'''
      <div class="news-item{featured}" data-animate>
        <span class="news-num">{num}</span>
        <span class="news-headline">{ntc['titulo']}</span>
        <span class="news-source">{fonte}</span>
      </div>'''

        sections_html += f'''
  <section class="section">
    <div class="section-header">
      <span class="section-icon">{icon}</span>
      <span class="section-name {cls_name}">{pilar_display}</span>
      <span class="section-count">{len(lista)} notícias</span>
    </div>
    <div class="news-list">{news_items}
    </div>
  </section>'''

    # ── Episódios anteriores (archive) ──
    archive_html = ""
    if episodios:
        for ep in episodios[:20]:  # mostra até 20
            if ep.get("exists", False):
                archive_html += f'''
    <a class="archive-link" href="{ep["path"]}">
      <div>
        <div class="archive-link-date">Ep #{ep["num"]} · {format_data_curta(ep["date"])}</div>
        <div class="archive-link-text">{ep["dur_str"]}</div>
      </div>
      <span class="archive-link-arrow">→</span>
    </a>'''
            else:
                archive_html += f'''
    <div class="archive-link archive-link--missing">
      <div>
        <div class="archive-link-date">Ep #{ep["num"]} · {format_data_curta(ep["date"])}</div>
        <div class="archive-link-text">indisponível</div>
      </div>
      <span class="archive-link-archive-ghost">◌</span>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<title>DropFiveNews — {data_br}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap" rel="stylesheet">
<style>
  *,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
  :root {{
    --bg:#0d1117; --surface:#131920; --border:#1e2733; --border-lt:#192028;
    --text:#e2e8f0; --muted:#64748b; --faint:#1e2d3d; --accent:#94a3b8;
    --accent-dim:#334155; --global:#6db88a; --tech:#60a5d4; --econ:#a89060; --red:#e06060;
  }}
  html {{ font-size:16px; scroll-behavior:smooth; }}
  body {{
    background:var(--bg); color:var(--text);
    font-family:'DM Sans',sans-serif; font-weight:300;
    line-height:1.6; min-height:100vh; overflow-x:hidden;
  }}
  header {{
    position:sticky; top:0; z-index:100; background:var(--bg);
    border-bottom:1px solid var(--border); padding:0 2rem;
    display:flex; align-items:center; justify-content:space-between; height:52px;
  }}
  .logo {{ font-family:'Libre Baskerville',serif; font-size:1rem; font-weight:700; letter-spacing:0.04em; color:var(--text); text-decoration:none; }}
  .logo span {{ color:var(--accent); }}
  .header-meta {{ font-size:0.7rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); }}
  .header-right {{ display:flex; align-items:center; gap:1.5rem; }}
  .edition-badge {{ font-size:0.65rem; letter-spacing:0.15em; text-transform:uppercase; color:var(--accent); border:1px solid var(--accent-dim); padding:2px 8px; border-radius:2px; }}

  .ticker-wrap {{ border-bottom:1px solid var(--border-lt); background:var(--surface); overflow:hidden; height:34px; display:flex; align-items:center; }}
  .ticker-label {{ flex-shrink:0; font-size:0.6rem; letter-spacing:0.18em; text-transform:uppercase; color:var(--accent); background:var(--bg); padding:0 1rem; height:100%; display:flex; align-items:center; border-right:1px solid var(--border); z-index:1; }}
  .ticker-track {{ display:flex; white-space:nowrap; animation:ticker 80s linear infinite; gap:0; }}
  .ticker-item {{ font-size:0.7rem; color:var(--muted); padding:0 2.5rem; letter-spacing:0.03em; border-right:1px solid var(--border-lt); height:34px; display:flex; align-items:center; gap:0.5rem; transition:color 0.2s; }}
  .ticker-item:hover {{ color:var(--text); }}
  .ticker-dot {{ width:4px; height:4px; border-radius:50%; flex-shrink:0; }}
  .dot-global {{ background:var(--global); }}
  .dot-tech {{ background:var(--tech); }}
  .dot-econ {{ background:var(--econ); }}
  @keyframes ticker {{ 0%{{transform:translateX(0);}} 100%{{transform:translateX(-50%);}} }}

  .container {{ max-width:900px; margin:0 auto; padding:0 2rem; }}
  .hero {{ padding:3.5rem 0 2.5rem; border-bottom:1px solid var(--border); }}
  .hero-eyebrow {{ font-size:0.65rem; letter-spacing:0.2em; text-transform:uppercase; color:var(--muted); margin-bottom:1rem; }}
  .hero-title {{ font-family:'Libre Baskerville',serif; font-size:clamp(2rem,5vw,3.2rem); font-weight:700; line-height:1.1; color:var(--text); margin-bottom:0.5rem; }}
  .hero-title em {{ font-style:italic; color:var(--accent); }}
  .hero-sub {{ font-size:0.85rem; color:var(--muted); margin-top:1rem; display:flex; align-items:center; gap:1.5rem; }}
  .hero-stat {{ display:flex; align-items:baseline; gap:0.35rem; }}
  .hero-stat strong {{ font-family:'Libre Baskerville',serif; font-size:1.4rem; color:var(--text); font-weight:400; }}
  .hero-stat span {{ font-size:0.7rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); }}
  .divider-v {{ width:1px; height:24px; background:var(--border); }}

  .player-bar {{ margin:2rem 0 0; padding:1rem 1.25rem; background:var(--surface); border:1px solid var(--border); border-radius:3px; display:flex; align-items:center; gap:1rem; }}
  .play-btn {{ width:36px; height:36px; border-radius:50%; border:1px solid var(--accent-dim); background:transparent; color:var(--accent); cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all 0.2s; }}
  .play-btn:hover {{ background:var(--accent); color:var(--bg); border-color:var(--accent); }}
  .play-btn svg {{ width:14px; height:14px; }}
  .player-info {{ flex:1; min-width:0; }}
  .player-title {{ font-size:0.75rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--text); margin-bottom:0.2rem; }}
  .player-progress {{ width:100%; height:2px; background:var(--border); border-radius:1px; cursor:pointer; margin-top:0.4rem; position:relative; overflow:hidden; }}
  .player-progress-fill {{ height:100%; width:0%; background:var(--accent); border-radius:1px; transition:width 0.1s linear; }}
  .player-time {{ font-size:0.65rem; color:var(--muted); flex-shrink:0; font-variant-numeric:tabular-nums; }}
  .player-download {{ color:var(--muted); text-decoration:none; font-size:0.7rem; letter-spacing:0.05em; flex-shrink:0; transition:color 0.2s; }}
  .player-download:hover {{ color:var(--accent); }}
  .speed-btn {{ width:32px; height:32px; border-radius:4px; border:1px solid var(--accent-dim); background:transparent; color:var(--muted); cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:500; letter-spacing:0.02em; transition:all 0.2s; }}
  .speed-btn:hover {{ color:var(--accent); border-color:var(--accent); background:rgba(148,163,184,0.08); }}

  .section {{ padding:2.5rem 0; border-bottom:1px solid var(--border-lt); }}
  .section-header {{ display:flex; align-items:baseline; gap:0.75rem; margin-bottom:1.75rem; padding-bottom:0.75rem; border-bottom:1px solid var(--border); }}
  .section-icon {{ font-size:0.85rem; }}
  .section-name {{ font-family:'Libre Baskerville',serif; font-size:0.9rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; }}
  .section-name.global {{ color:var(--global); }}
  .section-name.tech {{ color:var(--tech); }}
  .section-name.econ {{ color:var(--econ); }}
  .section-count {{ font-size:0.65rem; color:var(--muted); letter-spacing:0.1em; margin-left:auto; }}

  .news-list {{ display:flex; flex-direction:column; }}
  .news-item {{ display:grid; grid-template-columns:2.5rem 1fr auto; gap:0 1rem; align-items:start; padding:1.1rem 0; border-bottom:1px solid var(--border-lt); cursor:pointer; opacity:0; transform:translateY(18px); transition:opacity 0.5s ease,transform 0.5s ease,background 0.2s; position:relative; }}
  .news-item:last-child {{ border-bottom:none; }}
  .news-item.visible {{ opacity:1; transform:translateY(0); }}
  .news-item:hover {{ background:var(--surface); margin:0 -1.25rem; padding-left:1.25rem; padding-right:1.25rem; border-radius:2px; }}
  .news-num {{ font-family:'Libre Baskerville',serif; font-size:0.7rem; color:var(--faint); padding-top:0.15rem; text-align:right; font-style:italic; }}
  .news-headline {{ font-size:0.925rem; font-weight:400; line-height:1.45; color:var(--text); transition:color 0.2s; }}
  .news-item:hover .news-headline {{ color:#fff; }}
  .news-source {{ font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); white-space:nowrap; padding-top:0.2rem; transition:color 0.2s; }}
  .news-item:hover .news-source {{ color:var(--accent); }}
  .news-item.featured .news-headline {{ font-family:'Libre Baskerville',serif; font-size:1.05rem; font-weight:700; line-height:1.35; }}
  .news-item.featured .news-num {{ font-size:0.8rem; color:var(--accent-dim); }}

  .premium-block {{ margin:2.5rem 0; padding:1.5rem; border:1px solid var(--accent-dim); border-radius:3px; background:linear-gradient(135deg,rgba(200,169,110,0.04) 0%,transparent 60%); position:relative; overflow:hidden; }}
  .premium-block::before {{ content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,var(--accent),transparent); opacity:0.5; }}
  .premium-eyebrow {{ font-size:0.6rem; letter-spacing:0.2em; text-transform:uppercase; color:var(--accent); margin-bottom:0.6rem; display:flex; align-items:center; gap:0.5rem; }}
  .premium-eyebrow::after {{ content:''; flex:1; height:1px; background:var(--accent-dim); opacity:0.4; }}
  .premium-title {{ font-family:'Libre Baskerville',serif; font-size:1.05rem; font-weight:700; color:var(--text); margin-bottom:0.5rem; }}
  .premium-desc {{ font-size:0.82rem; color:var(--muted); line-height:1.5; margin-bottom:1.2rem; }}
  .premium-preview {{ display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem; padding:1rem; background:rgba(0,0,0,0.3); border-radius:2px; border-left:2px solid var(--accent-dim); filter:blur(3px); user-select:none; pointer-events:none; }}
  .premium-preview-line {{ height:10px; background:var(--faint); border-radius:2px; }}
  .premium-preview-line:nth-child(1) {{ width:85%; }}
  .premium-preview-line:nth-child(2) {{ width:70%; }}
  .premium-preview-line:nth-child(3) {{ width:90%; }}
  .premium-preview-line:nth-child(4) {{ width:60%; }}
  .btn-premium {{ display:inline-flex; align-items:center; gap:0.5rem; background:transparent; border:1px solid var(--accent); color:var(--accent); font-family:'DM Sans',sans-serif; font-size:0.72rem; font-weight:500; letter-spacing:0.12em; text-transform:uppercase; padding:0.5rem 1.1rem; border-radius:2px; cursor:pointer; text-decoration:none; transition:all 0.2s; }}
  .btn-premium:hover {{ background:var(--accent); color:var(--bg); }}

  footer {{ border-top:1px solid var(--border); padding:2rem 0; margin-top:1rem; }}
  .footer-inner {{ display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem; }}
  .footer-brand {{ font-family:'Libre Baskerville',serif; font-size:0.8rem; color:var(--muted); }}
  .footer-brand strong {{ color:var(--text); }}
  .footer-links {{ display:flex; gap:1.5rem; }}
  .footer-links a {{ font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); text-decoration:none; transition:color 0.2s; }}
  .footer-links a:hover {{ color:var(--accent); }}

  @keyframes fadeSlideUp {{ from{{opacity:0;transform:translateY(12px);}} to{{opacity:1;transform:translateY(0);}} }}
  .hero {{ animation:fadeSlideUp 0.6s ease both; }}
  .player-bar {{ animation:fadeSlideUp 0.6s 0.15s ease both; }}
  .ticker-wrap {{ animation:fadeSlideUp 0.4s ease both; }}

  .archive-link {{ display:flex; align-items:center; justify-content:space-between; padding:1rem 0; text-decoration:none; border-bottom:1px solid var(--border-lt); transition:padding 0.2s; }}
  .archive-link:hover {{ padding-left:0.5rem; }}
  .archive-link-text {{ font-size:0.82rem; color:var(--muted); }}
  .archive-link-date {{ font-family:'Libre Baskerville',serif; font-size:0.88rem; color:var(--text); font-style:italic; }}
  .archive-link-arrow {{ color:var(--accent); font-size:0.8rem; transition:transform 0.2s; }}
  .archive-link:hover .archive-link-arrow {{ transform:translateX(4px); }}
  .archive-link--missing {{ opacity:0.35; cursor:default; }}
  .archive-link--missing .archive-link-date {{ color:var(--muted); }}
  .archive-link--missing .archive-link-text {{ font-style:italic; color:var(--faint); }}
  .archive-link-archive-ghost {{ color:var(--faint); font-size:0.7rem; }}

  @media (max-width:600px) {{
    header {{ padding:0 1rem; }} .container {{ padding:0 1rem; }}
    .header-meta {{ display:none; }} .hero {{ padding:2rem 0 1.5rem; }}
    .news-item {{ grid-template-columns:2rem 1fr; }} .news-source {{ display:none; }}
    .footer-inner {{ flex-direction:column; align-items:flex-start; }}
  }}
</style>
</head>
<body>

<header>
  <a class="logo" href="/">drop<em style="font-style:italic">five</em><span>news</span></a>
  <span class="header-meta">{data_br}</span>
  <div class="header-right">
    <span class="edition-badge">#{podcast["num"] if podcast else "---"}</span>
  </div>
</header>

<div class="ticker-wrap">
  <span class="ticker-label">hoje</span>
  <div class="ticker-track" id="ticker">
    {ticker_items}
    {ticker_dup}
  </div>
</div>

<main>
<div class="container">

  <div class="hero">
    <p class="hero-eyebrow">Curadoria diária · Inteligência artificial</p>
    <h1 class="hero-title">As notícias<br>que <em>importam</em> hoje.</h1>
    <div class="hero-sub">
      <div class="hero-stat"><strong>{n}</strong><span>notícias</span></div>
      <div class="divider-v"></div>
      <div class="hero-stat"><strong>{n_pilares}</strong><span>pilares</span></div>
      <div class="divider-v"></div>
      <div class="hero-stat"><strong>{pod_dur}</strong><span>podcast</span></div>
    </div>
    {player_html}
  </div>

  {sections_html}

  <div class="premium-block" data-animate>
    <div class="premium-eyebrow">✦ Premium</div>
    <h3 class="premium-title">Brief Executivo de hoje</h3>
    <p class="premium-desc">3 bullets acionáveis — o que aconteceu, por que importa, o que observar. Sem ruído.</p>
    <div class="premium-preview" aria-hidden="true">
      <div class="premium-preview-line"></div>
      <div class="premium-preview-line"></div>
      <div class="premium-preview-line"></div>
      <div class="premium-preview-line"></div>
    </div>
    <a href="#" class="btn-premium">Acessar Brief ↗</a>
  </div>

  <section class="section" style="border-bottom:none;padding-bottom:0">
    <div class="section-header">
      <span class="section-icon">📅</span>
      <span class="section-name" style="color:var(--muted)">Episódios</span>
    </div>
    {archive_html if archive_html else '<p style="font-size:0.82rem;color:var(--muted);padding:1rem 0">Nenhum episódio anterior.</p>'}
  </section>

</div>
</main>

<footer>
  <div class="container">
    <div class="footer-inner">
      <div class="footer-brand">
        <strong>dropfivenews</strong> · Curadoria por <a href="https://www.instagram.com/jeanbraga.ai" style="color:var(--accent);text-decoration:none">@jeanbraga.ai</a><br>
        <span style="font-size:0.65rem">Atualizado em {data_br.lower()}</span>
      </div>
      <div class="footer-links">
        <a href="/feed.json">JSON Feed</a>
        <a href="/d5n-feed.xml">RSS</a>
        <a href="https://github.com/eibragaa/d5n-videocast-source">GitHub</a>
      </div>
    </div>
  </div>
</footer>

<script>
  const items = document.querySelectorAll('[data-animate]');
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach((entry, i) => {{
      if (entry.isIntersecting) {{
        const siblings = [...entry.target.parentElement.querySelectorAll('[data-animate]')];
        const idx = siblings.indexOf(entry.target);
        entry.target.style.transitionDelay = `${{idx * 60}}ms`;
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }}
    }});
  }}, {{ threshold:0.1, rootMargin:'0px 0px -40px 0px' }});
  items.forEach(el => observer.observe(el));

  const audio = document.getElementById('audioEl');
  const playIcon = document.getElementById('playIcon');
  const fill = document.getElementById('progressFill');
  const timeEl = document.getElementById('playerTime');
  const icons = {{ play:'<polygon points="5,3 19,12 5,21"/>', pause:'<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>' }};
  function fmt(s) {{ const m=Math.floor(s/60); const sec=Math.floor(s%60).toString().padStart(2,'0'); return `${{m}}:${{sec}}`; }}
  function togglePlay() {{ if(audio.paused){{audio.play();playIcon.innerHTML=icons.pause;}}else{{audio.pause();playIcon.innerHTML=icons.play;}} }}
  const speeds=[0.75,1,1.25,1.5,2]; let speedIdx=1;
  function cycleSpeed() {{ speedIdx=(speedIdx+1)%speeds.length; audio.playbackRate=speeds[speedIdx]; document.getElementById('speedBtn').textContent=speeds[speedIdx]+'×'; }}
  audio.addEventListener('timeupdate',()=>{{ if(!audio.duration)return; const pct=(audio.currentTime/audio.duration)*100; fill.style.width=pct+'%'; timeEl.textContent=`${{fmt(audio.currentTime)}} / ${{fmt(audio.duration)}}`; }});
  audio.addEventListener('ended',()=>{{ playIcon.innerHTML=icons.play; fill.style.width='0%'; }});
  function seekAudio(e){{ if(!audio.duration)return; const rect=e.currentTarget.getBoundingClientRect(); const pct=(e.clientX-rect.left)/rect.width; audio.currentTime=pct*audio.duration; }}
</script>
</body>
</html>'''
    return html

def gerar_source_md(date, data_br, noticias):
    if not noticias: return None
    md = f"# DROP FIVE NEWS — Boletim Diário\n## {data_br}\n\nINSTRUÇÕES (LEIA ANTES DE APRESENTAR):\n- Idioma: português brasileiro (NÃO use português de Portugal)\n- Contexto: Você é um apresentador de boletim de rádio. Apresente APENAS as notícias abaixo.\n- NÃO analise, avalie ou comente sobre o site, o projeto, a curadoria ou as fontes.\n- NÃO mencione NotebookLM, GitHub, feeds, JSON, RSS ou qualquer estrutura técnica.\n- Organize por blocos temáticos na ordem abaixo.\n- Use linguagem natural, coloquial brasileira, como um locutor de rádio.\n- Cada bloco começa com uma transição curta entre os temas.\n\n"
    pilares = {'Global':'🌍 GLOBAL','Brasil':'🇧🇷 BRASIL','Tech':'🤖 TECH & IA','Economia':'💰 ECONOMIA & CRYPTO'}
    cur = ''; idx = 1
    for n in noticias:
        p = n.get('pilar','')
        if p != cur: cur = p; md += f'\n### {pilares.get(p,p)}\n\n'
        md += f'{idx}. {n["titulo"]}\n\n'; idx += 1
    return md

def gerar_feeds_json(date, data_br, noticias):
    items = [{"id":date,"title":f"D5N • {data_br}","url":f"https://d5n-daily.netlify.app/","date_published":date,"summary":f"{len(noticias)} notícias","tags":["notícias","D5N"],"content_text":"\n".join(f"[{n.get('pilar','')}] {n['titulo']}" for n in noticias)}]
    return json.dumps({"version":"https://jsonfeed.org/version/1","title":"DropFiveNews","home_page_url":"https://d5n-daily.netlify.app","feed_url":"https://d5n-daily.netlify.app/feed.json","description":"Curadoria diária de notícias","author":{"name":"Jean Braga","url":"https://instagram.com/ojeanbraga.s"},"items":items},ensure_ascii=False,indent=2)

def gerar_feed_rss(date, data_br, noticias):
    import xml.sax.saxutils as saxutils
    desc = saxutils.escape(f"{len(noticias)} notícias: "+". ".join(n['titulo'] for n in noticias[:3]))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DropFiveNews</title>
    <link>https://d5n-daily.netlify.app</link>
    <description>Curadoria diária de notícias</description>
    <language>pt-br</language>
    <atom:link href="https://d5n-daily.netlify.app/d5n-feed.xml" rel="self" type="application/rss+xml"/>
    <item>
      <title>D5N • {saxutils.escape(data_br)}</title>
      <link>https://d5n-daily.netlify.app/</link>
      <guid isPermaLink="true">https://d5n-daily.netlify.app/</guid>
      <pubDate>{date}T03:00:00-04:00</pubDate>
      <description>{desc}</description>
    </item>
  </channel>
</rss>'''

def main():
    parser = argparse.ArgumentParser(description='Gera site D5N premium')
    parser.add_argument('--data', default=DATE)
    parser.add_argument('--no-podcast', action='store_true')
    args = parser.parse_args()
    date = args.data
    data_br = format_data_br(date)
    data_curta = format_data_curta(date)
    noticias = load_today_news(date)

    # Fallback: se não achou trends, ler source.md existente do repo
    if not noticias:
        src_path = f"{BASE}/source.md"
        if os.path.exists(src_path):
            with open(src_path) as f:
                for line in f:
                    m = re.match(r'^\d+\.\s+(.+)$', line.strip())
                    if m:
                        noticias.append({'pilar':'','titulo':m.group(1).strip()[:120],'fonte':'D5N'})
    if noticias:
        print(f"📄 Fallback: {len(noticias)} notícias recuperadas de source.md")
    else:
        print("❌ ERRO: Nenhuma notícia disponível (sem trends e sem fallback)")
        sys.exit(1)
    podcast = None if args.no_podcast else find_latest_podcast()
    episodios = list_episodes() if not args.no_podcast else []
    os.makedirs(ARQUIVO_DIR, exist_ok=True)

    html = gerar_html(date, data_br, data_curta, noticias, podcast, episodios)
    with open(f"{BASE}/index.html",'w') as f: f.write(html)
    print(f"✅ index.html — {len(html)} bytes, {len(noticias)} notícias")

    md = gerar_source_md(date, data_br, noticias)
    if md:
        with open(f"{BASE}/source.md",'w') as f: f.write(md)
        print(f"✅ source.md — {len(md)} bytes")

    md_daily = f"# DropFiveNews • {data_br}\n\n"+"\n".join(f"## [{n.get('pilar','')}] {n['titulo']}\n\n" for n in noticias)
    with open(f"{ARQUIVO_DIR}/{date}.md",'w') as f: f.write(md_daily)
    print(f"✅ 2026/{date}.md — {len(md_daily)} bytes")

    feed_j = gerar_feeds_json(date, data_br, noticias)
    with open(f"{BASE}/feed.json",'w') as f: f.write(feed_j)
    print(f"✅ feed.json — {len(feed_j)} bytes")

    feed_r = gerar_feed_rss(date, data_br, noticias)
    with open(f"{BASE}/d5n-feed.xml",'w') as f: f.write(feed_r)
    print(f"✅ d5n-feed.xml — {len(feed_r)} bytes")

    print(f"\n📊 {len(noticias)} notícias, {len(episodios)} episódios")
    print(f"🌐 https://d5n-daily.netlify.app/")

if __name__ == '__main__':
    main()
