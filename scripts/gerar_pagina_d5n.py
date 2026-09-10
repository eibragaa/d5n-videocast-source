#!/usr/bin/env python3
"""Gera o index.html do D5N Daily a partir dos feeds RSS (fonte única de verdade).

Design system editorial premium: tokens centralizados, ProgramCard master
com variações de tema por programa, players customizados, arquivo agrupado
por mês. Zero bibliotecas externas além de Google Fonts.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).parent.parent.resolve()
INDEX_HTML = REPO / "index.html"
TZ = ZoneInfo("America/Sao_Paulo")
IT = {"it": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
MESES_FULL = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
              'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
DIAS = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
        'Sexta-feira', 'Sábado', 'Domingo']

FEEDS = {
    "d5n": REPO / "podcast.xml",
    "mc": REPO / "manha-conectada/feeds/manha-conectada.xml",
    "fm": REPO / "fechamento/feeds/fechamento.xml",
}

PROGRAMS = {
    "d5n": {
        "badge": "DROP FIVE",
        "schedule": "05H · SEG–SÁB",
        "name": "Drop Five News",
        "tagline": "As notícias essenciais, com contexto, em um briefing para começar o dia.",
        "byline": "Curadoria diária",
        "theme": "d5n",
        "ep_label": True,
        "cover": "/podcast-cover.jpg",
    },
    "mc": {
        "badge": "MANHÃ CONECTADA",
        "schedule": "11H · SEG–SEX",
        "name": "Manhã Conectada",
        "tagline": "O que definiu a manhã — e o sinal que ainda pode mudar o dia.",
        "byline": "Com Antonio",
        "theme": "mc",
        "ep_label": False,
        "cover": "/manha-conectada-cover.jpg",
    },
    "fm": {
        "badge": "FECHAMENTO",
        "schedule": "17H · SEG–SEX",
        "name": "Fechamento do Mercado",
        "tagline": "O pregão em contexto — números, porquês e o radar de amanhã.",
        "byline": "Com Antonio",
        "theme": "fm",
        "ep_label": False,
        "cover": "/fechamento-cover.jpg",
    },
}

ARCHIVE_PAGE_SIZE = 20


def esc(s: str) -> str:
    return html_mod.escape(s or "", quote=True)


def parse_feed(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return []
    items = []
    for item in root.findall(".//item"):
        enc = item.find("enclosure")
        pub = item.find("pubDate")
        dur_el = item.find("it:duration", IT)
        summ = item.find("it:summary", IT)
        title = item.find("title")
        if enc is None:
            continue
        url = enc.get("url", "")
        if not url.endswith(".mp3"):
            continue
        d = None
        if pub is not None and pub.text:
            try:
                d = parsedate_to_datetime(pub.text).astimezone(TZ).date()
            except Exception:
                d = None
        dur = 0
        if dur_el is not None and dur_el.text:
            try:
                p = dur_el.text.split(":")
                if len(p) == 3:
                    dur = int(p[0]) * 3600 + int(p[1]) * 60 + int(p[2])
                elif len(p) == 2:
                    dur = int(p[0]) * 60 + int(p[1])
                else:
                    dur = int(float(dur_el.text))
            except (ValueError, TypeError):
                dur = 0
        s = ""
        if summ is not None and summ.text:
            s = re.sub(r"<[^>]+>", "", summ.text).strip()
        t = title.text.strip() if title is not None and title.text else ""
        items.append({"url": url, "date": d, "duration": dur,
                      "summary": s, "title": t})
    items.sort(key=lambda x: x["date"] or date(2000, 1, 1), reverse=True)
    return items


def local_path(url: str) -> str:
    """Converte URL absoluta do feed em path local servido pelo Netlify."""
    fname = url.split("/")[-1]
    if fname.startswith("manha-conectada-"):
        return f"/manha-conectada/audio/{fname}"
    if fname.startswith("fechamento-"):
        return f"/fechamento/audio/{fname}"
    return f"/audio/{fname}"


def fmt_dur(sec: int) -> str:
    if sec >= 3600:
        return f"{sec // 3600}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"
    return f"{sec // 60}:{sec % 60:02d}"


def fmt_date(d: date | None) -> str:
    if not d:
        return "—"
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


def fmt_date_long(d: date | None) -> str:
    if not d:
        return "—"
    return f"{d.day} de {MESES_FULL[d.month - 1]} de {d.year}"


def today_label() -> str:
    t = date.today()
    return f"{DIAS[t.weekday()]}, {t.day} de {MESES_FULL[t.month - 1]} de {t.year}"


def ep_number(url: str) -> str:
    m = re.search(r"-ep(\d+)-", url)
    return m.group(1) if m else ""


def truncate(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ---------------------------------------------------------------- CSS
CSS = r"""
/* ============ D5N DESIGN SYSTEM ============ */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  /* surfaces */
  --bg:#0B0E14; --surface:#10141D; --surface-2:#151B26; --surface-3:#1B2330;
  --border:#1E2634; --border-soft:#171E2A;
  /* text */
  --text:#E8ECF2; --text-2:#9AA5B4; --muted:#5C6675;
  /* program accents */
  --d5n:#5B8DEF; --mc:#8B7CF6; --fm:#3FB97F;
  --d5n-soft:rgba(91,141,239,.12); --mc-soft:rgba(139,124,246,.12); --fm-soft:rgba(63,185,127,.12);
  /* type */
  --font-display:'Inter Tight','Inter',system-ui,sans-serif;
  --font-body:'Inter',system-ui,sans-serif;
  --font-mono:'DM Mono',ui-monospace,monospace;
  /* radius */
  --r-card:20px; --r-inner:14px; --r-btn:12px; --r-pill:999px;
  /* spacing scale */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px; --s9:96px;
  /* shadow */
  --shadow-1:0 1px 2px rgba(0,0,0,.25);
  --shadow-2:0 8px 32px rgba(0,0,0,.35);
  /* motion */
  --t-fast:150ms; --t-med:220ms; --ease:cubic-bezier(.4,0,.2,1);
}
html{font-size:16px;scroll-behavior:smooth}
body{
  background:var(--bg);color:var(--text);
  font-family:var(--font-body);font-weight:400;line-height:1.6;
  min-height:100vh;overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
}
::selection{background:var(--d5n);color:#fff}
a{color:inherit}
button{font-family:inherit}
:focus-visible{outline:2px solid var(--d5n);outline-offset:3px;border-radius:4px}

/* ============ HEADER ============ */
.site-header{
  position:sticky;top:0;z-index:100;
  background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border-soft);
  transition:box-shadow var(--t-med) var(--ease),background var(--t-med) var(--ease);
}
.site-header.is-scrolled{
  background:color-mix(in srgb,var(--bg) 96%,transparent);
  box-shadow:0 8px 32px rgba(0,0,0,.35);
}
.header-inner{
  max-width:1200px;margin:0 auto;padding:0 var(--s5);
  height:60px;display:flex;align-items:center;gap:var(--s6);
}
.brand{
  font-family:var(--font-display);font-weight:800;font-size:1.05rem;
  letter-spacing:-.01em;text-decoration:none;display:flex;align-items:baseline;gap:6px;
}
.brand-mark{
  width:22px;height:22px;border-radius:6px;flex-shrink:0;align-self:center;
  background:linear-gradient(135deg,var(--d5n),var(--mc) 55%,var(--fm));
}
.main-nav{display:flex;gap:var(--s1);margin-left:auto}
.nav-link{
  font-size:.8rem;font-weight:500;color:var(--text-2);text-decoration:none;
  padding:6px 12px;border-radius:var(--r-pill);position:relative;
  transition:color var(--t-fast) var(--ease),background var(--t-fast) var(--ease);
}
.nav-link:hover{color:var(--text);background:var(--surface-2)}
.nav-link::after{
  content:"";position:absolute;left:12px;right:12px;bottom:2px;height:2px;
  border-radius:2px;background:var(--nav-accent,var(--d5n));
  transform:scaleX(0);transform-origin:left;transition:transform var(--t-med) var(--ease);
}
.nav-link:hover::after{transform:scaleX(1)}
.nav-link--d5n{--nav-accent:var(--d5n)}
.nav-link--mc{--nav-accent:var(--mc)}
.nav-link--fm{--nav-accent:var(--fm)}
.header-date{
  font-family:var(--font-mono);font-size:.68rem;color:var(--muted);
  letter-spacing:.04em;white-space:nowrap;
}
.menu-btn{
  display:none;width:40px;height:40px;border:1px solid var(--border);
  background:var(--surface);border-radius:var(--r-btn);color:var(--text);
  cursor:pointer;align-items:center;justify-content:center;
}
.menu-btn svg{width:18px;height:18px}

/* ============ TICKER ============ */
.ticker{
  border-bottom:1px solid var(--border-soft);background:var(--surface);
  overflow:hidden;height:36px;display:flex;align-items:stretch;
}
.ticker-label{
  flex-shrink:0;display:flex;align-items:center;padding:0 var(--s4);
  font-size:.62rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;
  color:var(--d5n);background:var(--bg);border-right:1px solid var(--border-soft);z-index:2;
}
.ticker-viewport{overflow:hidden;flex:1;display:flex;align-items:center}
.ticker-track{display:flex;white-space:nowrap;animation:ticker 90s linear infinite;will-change:transform}
.ticker:hover .ticker-track{animation-play-state:paused}
.ticker-item{
  font-size:.72rem;color:var(--text-2);padding:0 var(--s6);
  display:inline-flex;align-items:center;gap:var(--s2);
  border-right:1px solid var(--border-soft);height:36px;
}
.ticker-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
.ticker-dot--global{background:var(--d5n)}
.ticker-dot--tech{background:var(--mc)}
.ticker-dot--econ{background:var(--fm)}
@keyframes ticker{to{transform:translateX(-50%)}}

/* ============ LAYOUT ============ */
.container{max-width:1200px;margin:0 auto;padding:0 var(--s5)}

/* ============ HERO ============ */
.hero{
  position:relative;padding:var(--s9) 0 var(--s7);overflow:hidden;
}
.hero::before{
  content:"";position:absolute;inset:-40% -20% auto;height:520px;pointer-events:none;
  background:
    radial-gradient(560px 300px at 18% 0%,rgba(91,141,239,.10),transparent 65%),
    radial-gradient(480px 260px at 55% 10%,rgba(139,124,246,.08),transparent 65%),
    radial-gradient(420px 240px at 88% 0%,rgba(63,185,127,.07),transparent 65%);
}
.hero > *{position:relative}
.hero-eyebrow{
  font-size:.68rem;font-weight:600;letter-spacing:.2em;text-transform:uppercase;
  color:var(--d5n);margin-bottom:var(--s4);display:flex;align-items:center;gap:var(--s3);
}
.hero-eyebrow::before{content:"";width:24px;height:1px;background:var(--d5n)}
.hero-title{
  font-family:var(--font-display);font-weight:800;letter-spacing:-.03em;
  font-size:clamp(2.2rem,5.2vw,3.6rem);line-height:1.05;max-width:14ch;
}
.hero-title em{font-style:normal;color:var(--text-2)}
.hero-sub{
  margin-top:var(--s4);font-size:1rem;color:var(--text-2);max-width:52ch;
}
.hero-stats{
  display:flex;gap:var(--s6);margin-top:var(--s6);
  padding-top:var(--s5);border-top:1px solid var(--border-soft);
}
.hstat{display:flex;flex-direction:column;gap:2px}
.hstat strong{
  font-family:var(--font-display);font-weight:700;font-size:1.35rem;letter-spacing:-.02em;
}
.hstat span{
  font-size:.66rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
}

/* ============ SECTION HEADERS ============ */
.section{padding:var(--s7) 0}
.section + .section{border-top:1px solid var(--border-soft)}
.section-head{margin-bottom:var(--s6)}
.section-kicker{
  font-size:.66rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
  color:var(--muted);margin-bottom:var(--s2);
}
.section-title{
  font-family:var(--font-display);font-weight:700;letter-spacing:-.02em;
  font-size:clamp(1.5rem,3vw,2rem);
}
.section-sub{color:var(--text-2);font-size:.92rem;margin-top:var(--s2)}

/* ============ PROGRAM CARDS ============ */
.programs-grid{
  display:grid;gap:var(--s5);
  grid-template-columns:1.25fr 1fr;
  grid-template-areas:"featured side-a" "featured side-b";
}
.program-card{
  --accent:var(--d5n); --accent-soft:var(--d5n-soft);
  position:relative;display:flex;flex-direction:column;
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:var(--s6);
  transition:transform var(--t-med) var(--ease),border-color var(--t-med) var(--ease),box-shadow var(--t-med) var(--ease);
}
.program-card:hover{
  transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 40%,var(--border));
  box-shadow:var(--shadow-2),0 0 0 1px color-mix(in srgb,var(--accent) 18%,transparent);
}
.program-card::before{
  content:"";position:absolute;top:0;left:var(--s6);right:var(--s6);height:2px;
  background:linear-gradient(90deg,var(--accent),transparent 70%);
  border-radius:0 0 2px 2px;opacity:.85;
}
.program-card--d5n{--accent:var(--d5n);--accent-soft:var(--d5n-soft);grid-area:featured}
.program-card--mc{--accent:var(--mc);--accent-soft:var(--mc-soft);grid-area:side-a}
.program-card--fm{--accent:var(--fm);--accent-soft:var(--fm-soft);grid-area:side-b}

.pc-head{display:flex;gap:var(--s5);align-items:flex-start;margin-bottom:var(--s5)}
.pc-cover{
  width:88px;height:88px;flex-shrink:0;border-radius:var(--r-inner);
  object-fit:cover;display:block;
  border:1px solid var(--border);
  box-shadow:var(--shadow-1);
}
.program-card--d5n .pc-cover{width:112px;height:112px}
.pc-head-text{min-width:0;flex:1}
.pc-top{display:flex;align-items:center;justify-content:space-between;gap:var(--s3);margin-bottom:var(--s3)}
.pc-badge{
  display:inline-flex;align-items:center;gap:var(--s2);
  font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);background:var(--accent-soft);
  padding:5px 10px;border-radius:var(--r-pill);
}
.pc-badge::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--accent)}
.pc-schedule{
  font-family:var(--font-mono);font-size:.66rem;color:var(--muted);letter-spacing:.06em;
}
.pc-name{
  font-family:var(--font-display);font-weight:750;letter-spacing:-.02em;
  font-size:clamp(1.35rem,2.4vw,1.8rem);line-height:1.12;
}
.program-card--d5n .pc-name{font-size:clamp(1.7rem,3vw,2.3rem)}
.pc-tagline{color:var(--text-2);font-size:.88rem;margin-top:var(--s2);max-width:44ch}
.pc-byline{
  display:flex;gap:var(--s4);margin-top:var(--s3);
  font-size:.72rem;color:var(--muted);
}
.pc-byline span + span::before{content:"·";margin-right:var(--s4);color:var(--border)}

.pc-divider{height:1px;background:var(--border-soft);margin:var(--s5) 0}

.pc-latest-label{
  font-size:.62rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);display:flex;align-items:center;gap:var(--s2);
}
.pc-latest-label::before{
  content:"";width:6px;height:6px;border-radius:50%;background:var(--accent);
  animation:pulse 2.4s var(--ease) infinite;
}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.pc-latest-meta{
  display:flex;align-items:baseline;gap:var(--s3);margin-top:var(--s2);flex-wrap:wrap;
}
.pc-date{font-family:var(--font-display);font-weight:650;font-size:1.05rem;letter-spacing:-.01em}
.pc-duration{font-family:var(--font-mono);font-size:.78rem;color:var(--text-2)}
.pc-summary{
  margin-top:var(--s3);font-size:.84rem;color:var(--text-2);line-height:1.55;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}

/* player */
.pc-player{
  margin-top:var(--s5);padding:var(--s4);
  background:var(--surface-2);border:1px solid var(--border-soft);
  border-radius:var(--r-inner);
  display:flex;align-items:center;gap:var(--s3);
}
.pc-play{
  width:44px;height:44px;flex-shrink:0;border:none;cursor:pointer;
  border-radius:50%;background:var(--accent);color:#0B0E14;
  display:flex;align-items:center;justify-content:center;
  transition:transform var(--t-fast) var(--ease),box-shadow var(--t-fast) var(--ease);
  box-shadow:0 0 0 0 color-mix(in srgb,var(--accent) 40%,transparent);
}
.pc-play:hover{transform:scale(1.06);box-shadow:0 0 0 6px color-mix(in srgb,var(--accent) 14%,transparent)}
.pc-play:active{transform:scale(.97)}
.pc-play svg{width:16px;height:16px}
.pc-play .icon-pause{display:none}
.pc-play.is-playing .icon-play{display:none}
.pc-play.is-playing .icon-pause{display:block}
.pc-track{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}
.pc-progress{
  position:relative;height:6px;border-radius:var(--r-pill);
  background:var(--surface-3);cursor:pointer;overflow:hidden;
}
.pc-progress-fill{
  position:absolute;inset:0 auto 0 0;width:0%;
  background:var(--accent);border-radius:inherit;
  transition:width .12s linear;
}
.pc-progress:hover .pc-progress-fill{filter:brightness(1.15)}
.pc-times{
  display:flex;justify-content:space-between;
  font-family:var(--font-mono);font-size:.66rem;color:var(--muted);
}
.pc-speed{
  flex-shrink:0;border:1px solid var(--border);background:transparent;
  color:var(--text-2);font-family:var(--font-mono);font-size:.66rem;font-weight:500;
  padding:5px 9px;border-radius:var(--r-pill);cursor:pointer;
  transition:all var(--t-fast) var(--ease);
}
.pc-speed:hover{color:var(--accent);border-color:var(--accent)}

.pc-actions{display:flex;gap:var(--s3);margin-top:var(--s5)}
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:var(--s2);
  font-size:.82rem;font-weight:600;text-decoration:none;cursor:pointer;
  padding:11px 20px;border-radius:var(--r-btn);border:1px solid transparent;
  transition:all var(--t-fast) var(--ease);
}
.btn-primary{background:var(--accent);color:#0B0E14}
.btn-primary:hover{filter:brightness(1.1);transform:translateY(-1px)}
.btn-primary:active{transform:translateY(0)}
.btn-ghost{
  background:transparent;color:var(--text-2);border-color:var(--border);
}
.btn-ghost:hover{color:var(--text);border-color:var(--text-2)}
.btn svg{width:14px;height:14px}

/* archive inside card */
.pc-archive{margin-top:var(--s5);border-top:1px solid var(--border-soft);padding-top:var(--s4)}
.pc-archive-head{
  display:flex;align-items:center;justify-content:space-between;
  font-size:.66rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
}
.pc-archive-list{display:flex;flex-wrap:wrap;gap:var(--s2);margin-top:var(--s3)}
.pc-chip{
  font-family:var(--font-mono);font-size:.68rem;color:var(--text-2);
  background:var(--surface-2);border:1px solid var(--border-soft);
  padding:6px 11px;border-radius:var(--r-pill);cursor:pointer;
  transition:all var(--t-fast) var(--ease);
}
.pc-chip:hover{color:var(--text);border-color:var(--accent)}
.pc-chip.is-active{
  color:var(--accent);border-color:var(--accent);background:var(--accent-soft);
}

/* featured card extras */
.program-card--d5n{padding:var(--s7)}
.program-card--d5n .pc-play{width:52px;height:52px}
.program-card--d5n .pc-play svg{width:18px;height:18px}

/* ============ ARCHIVE ============ */
.archive-filters{display:flex;gap:var(--s2);flex-wrap:wrap;margin-bottom:var(--s5)}
.filter-chip{
  font-size:.74rem;font-weight:600;color:var(--text-2);
  background:var(--surface);border:1px solid var(--border);
  padding:7px 14px;border-radius:var(--r-pill);cursor:pointer;
  transition:all var(--t-fast) var(--ease);
}
.filter-chip:hover{color:var(--text);border-color:var(--text-2)}
.filter-chip.is-active{color:#0B0E14;background:var(--text);border-color:var(--text)}
.archive-month{
  font-family:var(--font-display);font-size:.78rem;font-weight:700;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
  margin:var(--s6) 0 var(--s3);display:flex;align-items:center;gap:var(--s3);
}
.archive-month::after{content:"";flex:1;height:1px;background:var(--border-soft)}
.archive-list{display:flex;flex-direction:column}
.archive-row{
  display:grid;grid-template-columns:44px 86px 1fr auto auto 40px;
  align-items:center;gap:var(--s4);
  padding:var(--s3) var(--s4);border-radius:var(--r-inner);
  border:1px solid transparent;cursor:pointer;
  transition:background var(--t-fast) var(--ease),border-color var(--t-fast) var(--ease);
}
.archive-row[hidden]{display:none}
.archive-thumb{
  width:44px;height:44px;border-radius:10px;object-fit:cover;display:block;
  border:1px solid var(--border-soft);
}
.archive-row:hover{background:var(--surface);border-color:var(--border-soft)}
.archive-row.is-playing{background:var(--surface);border-color:var(--accent,var(--d5n))}
.archive-ep{
  font-family:var(--font-mono);font-size:.7rem;font-weight:500;
  color:var(--accent,var(--d5n));letter-spacing:.04em;
}
.archive-row--d5n{--accent:var(--d5n)}
.archive-row--mc{--accent:var(--mc)}
.archive-row--fm{--accent:var(--fm)}
.archive-main{min-width:0}
.archive-title{
  font-size:.86rem;font-weight:550;color:var(--text);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.archive-prog{font-size:.68rem;color:var(--muted)}
.archive-date{font-family:var(--font-mono);font-size:.7rem;color:var(--text-2);white-space:nowrap}
.archive-dur{font-family:var(--font-mono);font-size:.7rem;color:var(--muted);white-space:nowrap}
.archive-play{
  width:32px;height:32px;border-radius:50%;border:1px solid var(--border);
  background:transparent;color:var(--text-2);cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:all var(--t-fast) var(--ease);
}
.archive-play:hover{border-color:var(--accent,var(--d5n));color:var(--accent,var(--d5n))}
.archive-play svg{width:11px;height:11px}
.archive-row.is-playing .archive-play{background:var(--accent,var(--d5n));color:#0B0E14;border-color:transparent}

/* pagination */
.archive-pagination{
  display:flex;align-items:center;justify-content:center;gap:var(--s3);
  margin-top:var(--s6);
}
.page-btn{
  min-width:38px;height:38px;padding:0 12px;
  font-family:var(--font-mono);font-size:.74rem;color:var(--text-2);
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-btn);cursor:pointer;
  transition:all var(--t-fast) var(--ease);
}
.page-btn:hover:not(:disabled){color:var(--text);border-color:var(--text-2)}
.page-btn:disabled{opacity:.35;cursor:default}
.page-btn.is-current{
  color:#0B0E14;background:var(--text);border-color:var(--text);font-weight:600;
}
.page-info{font-family:var(--font-mono);font-size:.68rem;color:var(--muted)}

/* ============ FOOTER ============ */
.site-footer{
  border-top:1px solid var(--border-soft);margin-top:var(--s8);
  padding:var(--s7) 0 var(--s6);
}
.footer-inner{
  display:flex;align-items:center;justify-content:space-between;gap:var(--s5);flex-wrap:wrap;
}
.footer-note{font-size:.74rem;color:var(--muted)}
.footer-links{display:flex;gap:var(--s5)}
.footer-links a{
  font-size:.74rem;color:var(--text-2);text-decoration:none;
  transition:color var(--t-fast) var(--ease);
}
.footer-links a:hover{color:var(--text)}

/* reveal animation */
[data-animate]{opacity:0;transform:translateY(14px);transition:opacity .5s var(--ease),transform .5s var(--ease)}
[data-animate].is-visible{opacity:1;transform:none}

/* ============ RESPONSIVE ============ */
@media (max-width:1024px){
  .programs-grid{grid-template-columns:1fr;grid-template-areas:"featured" "side-a" "side-b"}
  .program-card--d5n{padding:var(--s6)}
}
@media (max-width:768px){
  .header-inner{padding:0 var(--s4);gap:var(--s4)}
  .main-nav{
    display:none;position:absolute;top:60px;left:0;right:0;
    flex-direction:column;background:var(--bg);border-bottom:1px solid var(--border);
    padding:var(--s3);gap:2px;
  }
  .main-nav.is-open{display:flex}
  .nav-link{padding:12px 16px;border-radius:var(--r-btn)}
  .menu-btn{display:flex}
  .header-date{display:none}
  .container{padding:0 var(--s4)}
  .hero{padding:var(--s7) 0 var(--s6)}
  .hero-stats{gap:var(--s5);flex-wrap:wrap}
  .program-card{padding:var(--s5)}
  .pc-cover{width:72px;height:72px}
  .program-card--d5n .pc-cover{width:84px;height:84px}
  .pc-actions{flex-direction:column}
  .btn{width:100%}
  .archive-row{grid-template-columns:44px 1fr auto 40px;grid-template-areas:"thumb main date play" "thumb main dur play"}
  .archive-thumb{grid-area:thumb}
  .archive-ep{display:none}
  .archive-main{grid-area:main}
  .archive-date{grid-area:date}
  .archive-dur{grid-area:dur;justify-self:end}
  .archive-play{grid-area:play}
}
@media (max-width:380px){
  .pc-player{flex-wrap:wrap}
  .pc-speed{margin-left:auto}
}

/* ============ REDUCED MOTION ============ */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms !important;animation-iteration-count:1 !important;transition-duration:.01ms !important}
  .ticker-track{animation:none;flex-wrap:wrap;white-space:normal}
  [data-animate]{opacity:1;transform:none}
  html{scroll-behavior:auto}
}
"""


# ---------------------------------------------------------------- HTML pieces
def player_html(pid: str, dur: int) -> str:
    return f"""
      <div class="pc-player">
        <button class="pc-play" id="{pid}PlayBtn" type="button" aria-label="Reproduzir episódio">
          <svg class="icon-play" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="6,4 20,12 6,20"/></svg>
          <svg class="icon-pause" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
        </button>
        <div class="pc-track">
          <div class="pc-progress" id="{pid}Progress" role="slider" tabindex="0"
               aria-label="Progresso do episódio" aria-valuemin="0" aria-valuemax="{dur}" aria-valuenow="0">
            <div class="pc-progress-fill" id="{pid}ProgressFill"></div>
          </div>
          <div class="pc-times">
            <span id="{pid}TimeCurrent">0:00</span>
            <span id="{pid}TimeTotal">{fmt_dur(dur)}</span>
          </div>
        </div>
        <button class="pc-speed" id="{pid}Speed" type="button" title="Velocidade de reprodução" aria-label="Velocidade de reprodução">1×</button>
      </div>"""


def chips_html(eps: list[dict], pid: str, limit: int = 7) -> str:
    chips = []
    for i, e in enumerate(eps[:limit]):
        src = local_path(e["url"])
        active = " is-active" if i == 0 else ""
        chips.append(
            f'<button type="button" class="pc-chip{active}" '
            f'data-program="{pid}" data-src="{esc(src)}" '
            f'data-date="{esc(fmt_date(e["date"]))}" data-duration="{e["duration"]}" '
            f'data-summary="{esc(truncate(e["summary"], 220))}" '
            f'title="{esc(fmt_date(e["date"]))} · {fmt_dur(e["duration"])}">'
            f'{esc(fmt_date(e["date"]))}</button>'
        )
    return "\n        ".join(chips)


def program_card(key: str, eps: list[dict], featured: bool) -> str:
    p = PROGRAMS[key]
    pid = key
    if not eps:
        return ""
    latest = eps[0]
    src = local_path(latest["url"])
    dur = latest["duration"]
    epn = ep_number(latest["url"])
    ep_tag = f'<span class="pc-duration">EP {esc(epn)}</span>' if (p["ep_label"] and epn) else ""
    summary = esc(truncate(latest["summary"], 200))
    cls = f"program-card program-card--{p['theme']}"
    return f"""
    <article class="{cls}" id="{key}" data-animate aria-labelledby="{pid}Name">
      <div class="pc-head">
        <img class="pc-cover" src="{esc(p['cover'])}" alt="Capa do programa {esc(p['name'])}" width="112" height="112" loading="lazy">
        <div class="pc-head-text">
          <div class="pc-top">
            <span class="pc-badge">{esc(p['badge'])}</span>
            <span class="pc-schedule">{esc(p['schedule'])}</span>
          </div>
          <h3 class="pc-name" id="{pid}Name">{esc(p['name'])}</h3>
          <p class="pc-tagline">{esc(p['tagline'])}</p>
          <div class="pc-byline"><span>{esc(p['byline'])}</span><span>{esc(p['schedule'])}</span></div>
        </div>
      </div>
      <div class="pc-divider"></div>
      <span class="pc-latest-label">Última edição</span>
      <div class="pc-latest-meta">
        <span class="pc-date" id="{pid}Date">{esc(fmt_date(latest['date']))}</span>
        <span class="pc-duration" id="{pid}Dur">{fmt_dur(dur)}</span>
        {ep_tag}
      </div>
      <p class="pc-summary" id="{pid}Summary">{summary}</p>
      {player_html(pid, dur)}
      <div class="pc-actions">
        <button class="btn btn-primary" id="{pid}Cta" type="button">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="6,4 20,12 6,20"/></svg>
          Ouvir episódio
        </button>
        <a class="btn btn-ghost" href="#arquivo" data-filter-link="{key}">Ver arquivo</a>
      </div>
      <div class="pc-archive">
        <div class="pc-archive-head"><span>Arquivo recente</span></div>
        <div class="pc-archive-list" id="{pid}Chips">
        {chips_html(eps, pid)}
        </div>
      </div>
      <audio id="{pid}Audio" src="{esc(src)}" preload="metadata"></audio>
    </article>"""


def archive_html(all_eps: list[dict]) -> str:
    """all_eps: lista de dicts com campos extras program/ep."""
    rows = []
    current_month = None
    for e in all_eps:
        d = e["date"]
        if d:
            month_key = f"{MESES_FULL[d.month - 1].upper()} {d.year}"
        else:
            month_key = "ANTERIORES"
        if month_key != current_month:
            current_month = month_key
            rows.append(f'<div class="archive-month">{esc(month_key)}</div>')
        src = local_path(e["url"])
        prog = e["program"]
        epn = e.get("ep") or ""
        ep_txt = f"EP {epn}" if epn else PROGRAMS[prog]["badge"].title()
        title = e["title"] or e["summary"] or PROGRAMS[prog]["name"]
        rows.append(
            f'      <div class="archive-row archive-row--{prog}" data-program="{prog}" '
            f'data-src="{esc(src)}" data-duration="{e["duration"]}" tabindex="0" role="button" '
            f'aria-label="Ouvir {esc(PROGRAMS[prog]["name"])} de {esc(fmt_date(d))}">'
            f'<img class="archive-thumb" src="{esc(PROGRAMS[prog]["cover"])}" alt="" width="44" height="44" loading="lazy">'
            f'<span class="archive-ep">{esc(ep_txt)}</span>'
            f'<div class="archive-main">'
            f'<div class="archive-title">{esc(truncate(title, 70))}</div>'
            f'<div class="archive-prog">{esc(PROGRAMS[prog]["name"])}</div>'
            f'</div>'
            f'<span class="archive-date">{esc(fmt_date(d))}</span>'
            f'<span class="archive-dur">{fmt_dur(e["duration"])}</span>'
            f'<button class="archive-play" type="button" aria-hidden="true" tabindex="-1">'
            f'<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6,4 20,12 6,20"/></svg>'
            f'</button></div>'
        )
    return "\n".join(rows)


def ticker_html(ticker_items: list[str]) -> str:
    if not ticker_items:
        return ""
    items = []
    for it in ticker_items:
        cat, _, text = it.partition("|")
        dot = {"global": "global", "tech": "tech", "econ": "econ"}.get(cat.strip(), "global")
        items.append(
            f'<span class="ticker-item"><span class="ticker-dot ticker-dot--{dot}"></span>{esc(text.strip())}</span>'
        )
    # duplicate for seamless loop
    seq = "\n      ".join(items)
    return f"""<div class="ticker" aria-label="Manchetes do dia">
    <span class="ticker-label">Hoje</span>
    <div class="ticker-viewport">
      <div class="ticker-track" id="tickerTrack">
      {seq}
      {seq}
      </div>
    </div>
  </div>"""


# ---------------------------------------------------------------- JS
JS = r"""
(function(){
"use strict";
const $ = (id) => document.getElementById(id);
const fmt = (s) => {
  s = Math.max(0, Math.floor(s || 0));
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), ss = s%60;
  return h > 0 ? `${h}:${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`
               : `${m}:${String(ss).padStart(2,'0')}`;
};
const SPEEDS = [1, 1.25, 1.5, 2];
const players = {};
let activePid = null;

function stopOthers(except){
  Object.keys(players).forEach(pid => {
    if (pid !== except && players[pid] && !players[pid].audio.paused){
      players[pid].audio.pause();
    }
  });
  document.querySelectorAll('.archive-row.is-playing').forEach(r => r.classList.remove('is-playing'));
}

function syncUI(pid){
  const p = players[pid]; if(!p) return;
  const a = p.audio;
  const cur = a.currentTime, dur = a.duration || p.fallbackDur || 0;
  const pct = dur > 0 ? (cur/dur)*100 : 0;
  p.fill.style.width = pct + '%';
  p.progress.setAttribute('aria-valuenow', Math.round(cur));
  p.progress.setAttribute('aria-valuemax', Math.round(dur));
  p.timeCur.textContent = fmt(cur);
  p.timeTot.textContent = fmt(dur);
  const playing = !a.paused;
  p.btn.classList.toggle('is-playing', playing);
  p.btn.setAttribute('aria-label', playing ? 'Pausar episódio' : 'Reproduzir episódio');
}

function initPlayer(pid){
  const audio = $(pid+'Audio'), btn = $(pid+'PlayBtn'), cta = $(pid+'Cta'),
        progress = $(pid+'Progress'), fill = $(pid+'ProgressFill'),
        timeCur = $(pid+'TimeCurrent'), timeTot = $(pid+'TimeTotal'),
        speed = $(pid+'Speed');
  if(!audio || !btn) return;
  const p = players[pid] = {
    audio, btn, progress, fill, timeCur, timeTot, speed,
    speedIdx: 0, fallbackDur: parseInt(progress?.getAttribute('aria-valuemax') || '0', 10)
  };
  const toggle = () => {
    if (audio.paused){ stopOthers(pid); activePid = pid; audio.play().catch(()=>{}); }
    else audio.pause();
  };
  btn.addEventListener('click', toggle);
  if (cta) cta.addEventListener('click', toggle);
  audio.addEventListener('play', () => { stopOthers(pid); activePid = pid; syncUI(pid); });
  audio.addEventListener('pause', () => syncUI(pid));
  audio.addEventListener('ended', () => syncUI(pid));
  audio.addEventListener('timeupdate', () => syncUI(pid));
  audio.addEventListener('loadedmetadata', () => syncUI(pid));
  if (progress){
    const seek = (clientX) => {
      const r = progress.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
      const dur = audio.duration || p.fallbackDur || 0;
      if (dur > 0) audio.currentTime = ratio * dur;
    };
    progress.addEventListener('click', (e) => seek(e.clientX));
    progress.addEventListener('keydown', (e) => {
      const dur = audio.duration || p.fallbackDur || 0;
      if (e.key === 'ArrowRight'){ audio.currentTime = Math.min(dur, audio.currentTime + 15); e.preventDefault(); }
      if (e.key === 'ArrowLeft'){ audio.currentTime = Math.max(0, audio.currentTime - 15); e.preventDefault(); }
      if (e.key === ' ' || e.key === 'Enter'){ toggle(); e.preventDefault(); }
    });
  }
  if (speed){
    speed.addEventListener('click', () => {
      p.speedIdx = (p.speedIdx + 1) % SPEEDS.length;
      audio.playbackRate = SPEEDS[p.speedIdx];
      speed.textContent = SPEEDS[p.speedIdx] + '×';
    });
  }
  syncUI(pid);
}

function loadEpisode(pid, src, dateTxt, dur, summary, chip){
  const p = players[pid]; if(!p) return;
  if (p.audio.getAttribute('src') !== src){
    p.audio.src = src;
    p.audio.load();
  }
  p.fallbackDur = dur || p.fallbackDur;
  const dateEl = $(pid+'Date'), durEl = $(pid+'Dur'), sumEl = $(pid+'Summary');
  if (dateEl && dateTxt) dateEl.textContent = dateTxt;
  if (durEl && dur) durEl.textContent = fmt(dur);
  if (sumEl && summary) sumEl.textContent = summary;
  if (p.progress) p.progress.setAttribute('aria-valuemax', Math.round(dur || 0));
  document.querySelectorAll(`#${pid}Chips .pc-chip`).forEach(c => c.classList.remove('is-active'));
  if (chip) chip.classList.add('is-active');
  stopOthers(pid); activePid = pid;
  p.audio.play().catch(()=>{});
}

// chips inside program cards
document.querySelectorAll('.pc-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    loadEpisode(
      chip.dataset.program, chip.dataset.src, chip.dataset.date,
      parseInt(chip.dataset.duration || '0', 10), chip.dataset.summary || '', chip
    );
  });
});

// archive rows
const FILTER_LABELS = { all:'Todos', d5n:'Drop Five', mc:'Manhã Conectada', fm:'Fechamento' };
document.querySelectorAll('.archive-row').forEach(row => {
  const play = () => {
    const pid = row.dataset.program;
    loadEpisode(pid, row.dataset.src, null, parseInt(row.dataset.duration || '0', 10), '', null);
    document.querySelectorAll('.archive-row.is-playing').forEach(r => r.classList.remove('is-playing'));
    row.classList.add('is-playing');
    const card = document.getElementById(pid);
    if (card) card.scrollIntoView({behavior:'smooth', block:'center'});
  };
  row.addEventListener('click', play);
  row.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' '){ play(); e.preventDefault(); }
  });
});

// archive filters + pagination
const PAGE_SIZE = 20;
let currentFilter = 'all';
let currentPage = 1;

function visibleRows(){
  return Array.from(document.querySelectorAll('.archive-row'))
    .filter(r => currentFilter === 'all' || r.dataset.program === currentFilter);
}

function renderArchive(){
  const rows = visibleRows();
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRows = new Set(rows.slice(start, start + PAGE_SIZE));

  document.querySelectorAll('.archive-row').forEach(r => { r.hidden = !pageRows.has(r); });
  document.querySelectorAll('.archive-month').forEach(m => {
    let el = m.nextElementSibling, visible = false;
    while (el && !el.classList.contains('archive-month')){
      if (el.classList.contains('archive-row') && !el.hidden) visible = true;
      el = el.nextElementSibling;
    }
    m.hidden = !visible;
  });

  const nav = $('archivePagination');
  if (nav){
    nav.innerHTML = '';
    if (totalPages > 1){
      const prev = document.createElement('button');
      prev.className = 'page-btn'; prev.type = 'button'; prev.textContent = '←';
      prev.disabled = currentPage === 1;
      prev.setAttribute('aria-label', 'Página anterior');
      prev.addEventListener('click', () => { currentPage--; renderArchive(); });
      nav.appendChild(prev);

      const win = [];
      for (let i = 1; i <= totalPages; i++){
        if (i === 1 || i === totalPages || Math.abs(i - currentPage) <= 2) win.push(i);
      }
      let last = 0;
      win.forEach(i => {
        if (i - last > 1){
          const gap = document.createElement('span');
          gap.className = 'page-info'; gap.textContent = '…';
          nav.appendChild(gap);
        }
        const b = document.createElement('button');
        b.className = 'page-btn' + (i === currentPage ? ' is-current' : '');
        b.type = 'button'; b.textContent = i;
        b.setAttribute('aria-label', 'Página ' + i);
        if (i === currentPage) b.setAttribute('aria-current', 'page');
        b.addEventListener('click', () => { currentPage = i; renderArchive(); });
        nav.appendChild(b);
        last = i;
      });

      const next = document.createElement('button');
      next.className = 'page-btn'; next.type = 'button'; next.textContent = '→';
      next.disabled = currentPage === totalPages;
      next.setAttribute('aria-label', 'Próxima página');
      next.addEventListener('click', () => { currentPage++; renderArchive(); });
      nav.appendChild(next);

      const info = document.createElement('span');
      info.className = 'page-info';
      info.textContent = rows.length + ' episódios';
      nav.appendChild(info);
    }
  }
}

function applyFilter(f){
  currentFilter = f;
  currentPage = 1;
  document.querySelectorAll('.filter-chip').forEach(c =>
    c.classList.toggle('is-active', c.dataset.filter === f));
  renderArchive();
}
document.querySelectorAll('.filter-chip').forEach(c =>
  c.addEventListener('click', () => applyFilter(c.dataset.filter)));
document.querySelectorAll('[data-filter-link]').forEach(a =>
  a.addEventListener('click', () => applyFilter(a.dataset.filterLink)));

// mobile nav
const menuBtn = $('menuBtn'), nav = $('mainNav');
if (menuBtn && nav){
  menuBtn.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => nav.classList.remove('is-open')));
}

// reveal on scroll
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!reduceMotion && 'IntersectionObserver' in window){
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => { if (en.isIntersecting){ en.target.classList.add('is-visible'); io.unobserve(en.target); } });
  }, {threshold: .08});
  document.querySelectorAll('[data-animate]').forEach(el => io.observe(el));
} else {
  document.querySelectorAll('[data-animate]').forEach(el => el.classList.add('is-visible'));
}

// header scrolled state
const header = document.querySelector('.site-header');
if (header){
  const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
  window.addEventListener('scroll', onScroll, {passive:true});
  onScroll();
}

['d5n','mc','fm'].forEach(initPlayer);
renderArchive();
})();
"""


# ---------------------------------------------------------------- page
def build_page(eps: dict[str, list[dict]], ticker_items: list[str]) -> str:
    today = today_label()
    title_date = today_label()

    # latest of each for hero stats
    d5n_eps, mc_eps, fm_eps = eps["d5n"], eps["mc"], eps["fm"]
    total_eps = len(d5n_eps) + len(mc_eps) + len(fm_eps)

    # merged archive
    merged = []
    for key, lst in eps.items():
        for e in lst:
            merged.append({**e, "program": key, "ep": ep_number(e["url"])})
    merged.sort(key=lambda x: x["date"] or date(2000, 1, 1), reverse=True)

    cards = (
        program_card("d5n", d5n_eps, featured=True)
        + program_card("mc", mc_eps, featured=False)
        + program_card("fm", fm_eps, featured=False)
    )

    ticker = ticker_html(ticker_items)
    archive = archive_html(merged)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0B0E14">
<meta name="description" content="Drop Five News: notícias essenciais, contexto e tecnologia em um podcast diário, de segunda a sábado.">
<meta name="author" content="Drop Five News">
<link rel="canonical" href="https://d5n-daily.netlify.app/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="Drop Five News" href="/podcast.xml">
<link rel="alternate" type="application/rss+xml" title="Manhã Conectada" href="/manha-conectada.xml">
<link rel="alternate" type="application/rss+xml" title="Fechamento do Mercado" href="/fechamento.xml">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Drop Five News">
<meta property="og:title" content="Drop Five News — notícias essenciais para o seu dia">
<meta property="og:description" content="Brasil, mundo e tecnologia com contexto, curadoria e um novo episódio de segunda a sábado.">
<meta property="og:url" content="https://d5n-daily.netlify.app/">
<meta property="og:image" content="https://d5n-daily.netlify.app/social-card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Drop Five News">
<meta name="twitter:description" content="Notícias essenciais e contexto em um podcast diário.">
<meta name="twitter:image" content="https://d5n-daily.netlify.app/social-card.png">
<title>Drop Five News — {esc(title_date)}</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"PodcastSeries","name":"Drop Five News","url":"https://d5n-daily.netlify.app/","description":"Notícias essenciais, contexto e tecnologia em um podcast diário.","inLanguage":"pt-BR"}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@650;700;750;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/" aria-label="Drop Five News — página inicial">
      <span class="brand-mark" aria-hidden="true"></span>D5N
    </a>
    <button class="menu-btn" id="menuBtn" type="button" aria-label="Abrir menu" aria-expanded="false" aria-controls="mainNav">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/></svg>
    </button>
    <nav class="main-nav" id="mainNav" aria-label="Programas">
      <a class="nav-link nav-link--d5n" href="#d5n">Drop Five</a>
      <a class="nav-link nav-link--mc" href="#mc">Manhã Conectada</a>
      <a class="nav-link nav-link--fm" href="#fm">Fechamento</a>
      <a class="nav-link" href="#arquivo">Arquivo</a>
    </nav>
    <span class="header-date">{esc(today)}</span>
  </div>
</header>

{ticker}

<main class="container" id="conteudo">

  <section class="hero" data-animate>
    <p class="hero-eyebrow">Podcast diário · Curadoria editorial</p>
    <h1 class="hero-title">Notícias essenciais.<br><em>Contexto para começar o dia.</em></h1>
    <p class="hero-sub">Brasil, mundo, tecnologia e mercado em uma curadoria diária, com contexto e áudio.</p>
    <div class="hero-stats">
      <div class="hstat"><strong>{total_eps}</strong><span>episódios</span></div>
      <div class="hstat"><strong>3</strong><span>programas</span></div>
      <div class="hstat"><strong>Seg–Sáb</strong><span>edição diária</span></div>
    </div>
  </section>

  <section class="section" aria-labelledby="programsTitle">
    <div class="section-head" data-animate>
      <p class="section-kicker">Programas</p>
      <h2 class="section-title" id="programsTitle">Escolha sua edição</h2>
      <p class="section-sub">Três momentos para acompanhar o que importa.</p>
    </div>
    <div class="programs-grid">
{cards}
    </div>
  </section>

  <section class="section" id="arquivo" aria-labelledby="archiveTitle">
    <div class="section-head" data-animate>
      <p class="section-kicker">Arquivo</p>
      <h2 class="section-title" id="archiveTitle">Todas as edições</h2>
      <p class="section-sub">Ouça qualquer episódio diretamente do arquivo.</p>
    </div>
    <div class="archive-filters" role="group" aria-label="Filtrar por programa">
      <button class="filter-chip is-active" type="button" data-filter="all">Todos</button>
      <button class="filter-chip" type="button" data-filter="d5n">Drop Five</button>
      <button class="filter-chip" type="button" data-filter="mc">Manhã Conectada</button>
      <button class="filter-chip" type="button" data-filter="fm">Fechamento</button>
    </div>
    <div class="archive-list" id="archiveList">
{archive}
    </div>
    <nav class="archive-pagination" id="archivePagination" aria-label="Paginação do arquivo"></nav>
  </section>

</main>

<footer class="site-footer">
  <div class="container footer-inner">
    <span class="footer-note">© {date.today().year} Drop Five News — curadoria editorial diária.</span>
    <div class="footer-links">
      <a href="/podcast.xml">RSS Drop Five</a>
      <a href="/manha-conectada.xml">RSS Manhã</a>
      <a href="/fechamento.xml">RSS Fechamento</a>
    </div>
  </div>
</footer>

<script>{JS}</script>
</body>
</html>
"""


def extract_ticker(old_html: str) -> list[str]:
    """Extrai itens do ticker do HTML antigo: categoria|texto."""
    items = []
    for m in re.finditer(
        r'<span class="ticker-dot dot-(global|tech|econ)"></span>(.*?)</span>',
        old_html, re.DOTALL,
    ):
        cat, text = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\*\*", "", text).strip()
        text = re.sub(r"\s+", " ", text)
        if text and len(items) < 16:
            items.append(f"{cat}|{text}")
    # dedupe keeping order
    seen, out = set(), []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out[:14]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    eps = {k: parse_feed(p) for k, p in FEEDS.items()}
    for k, v in eps.items():
        print(f"  {k}: {len(v)} episódios")
    if not all(eps.values()):
        print("ERRO: um ou mais feeds vazios", file=sys.stderr)
        return 1

    ticker_items: list[str] = []
    ticker_file = REPO / "data" / "ticker.txt"
    if ticker_file.exists():
        ticker_items = [l.strip() for l in ticker_file.read_text(encoding="utf-8").splitlines() if "|" in l]
        print(f"  ticker: {len(ticker_items)} itens de data/ticker.txt")
    elif INDEX_HTML.exists():
        ticker_items = extract_ticker(INDEX_HTML.read_text(encoding="utf-8"))
        print(f"  ticker: {len(ticker_items)} itens preservados do HTML")

    page = build_page(eps, ticker_items)

    if args.dry_run:
        print(f"DRY RUN — {len(page)} chars gerados")
        return 0

    INDEX_HTML.write_text(page, encoding="utf-8")
    print(f"OK — {INDEX_HTML} ({len(page)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
