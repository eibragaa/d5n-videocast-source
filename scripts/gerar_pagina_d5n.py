#!/usr/bin/env python3
"""Atualiza o index.html com dados dos feeds RSS (episódios, datas, durações)."""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

REPO = Path(__file__).parent.parent.resolve()
INDEX_HTML = REPO / "index.html"
FEEDS = {
    "MC": REPO / "manha-conectada/feeds/manha-conectada.xml",
    "FM": REPO / "fechamento/feeds/fechamento.xml",
    "D5N": REPO / "podcast.xml",
}
TZ = ZoneInfo("America/Sao_Paulo")
ITUNES_NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


def parse_feed(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception:
        return []
    items = []
    for item in root.findall(".//item"):
        enclosure = item.find("enclosure")
        pub = item.find("pubDate")
        title = item.find("title")
        duration_el = item.find("itunes:duration", ITUNES_NS)
        summary_el = item.find("itunes:summary", ITUNES_NS)
        if enclosure is None:
            continue
        url = enclosure.get("url", "")
        if not url.endswith(".mp3"):
            continue
        dur = 0
        dur_text = duration_el.text if duration_el is not None else "0"
        if dur_text:
            try:
                if ":" in dur_text:
                    parts = dur_text.split(":")
                    if len(parts) == 3:
                        dur = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:
                        dur = int(parts[0]) * 60 + int(parts[1])
                else:
                    dur = int(float(dur_text))
            except (ValueError, TypeError):
                dur = 0
        pub_date = None
        if pub is not None and pub.text:
            try:
                dt = parsedate_to_datetime(pub.text)
                pub_date = dt.astimezone(TZ).date()
            except Exception:
                pub_date = None
        summary = ""
        if summary_el is not None and summary_el.text:
            summary = re.sub(r'<[^>]+>', '', summary_el.text)[:200]
        items.append({
            "url": url,
            "date": pub_date,
            "title": title.text if title is not None else "",
            "duration": dur,
            "summary": summary,
        })
    items.sort(key=lambda x: x["date"] or date(2000, 1, 1), reverse=True)
    return items


def format_date_br(d: date) -> str:
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return f"{d.day} {meses[d.month - 1]} {d.year}"


def format_dur(seconds: int) -> str:
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


def today_label() -> str:
    today = date.today()
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
            "Sexta-feira", "Sábado", "Domingo"]
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    return f"{dias[today.weekday()]}, {today.day} de {meses[today.month - 1]} de {today.year}"


def extract_filename(url: str) -> str:
    return url.split("/")[-1] or ""


def update_index(html: str, episodes: dict) -> str:
    today_str = today_label()
    html = re.sub(r"<title>.*?</title>", f"<title>Drop Five News — {today_str}</title>", html)
    html = re.sub(r'<span class="header-meta">.*?</span>',
                  f'<span class="header-meta">{today_str}</span>', html)

    mc_eps = episodes.get("MC", [])
    fm_eps = episodes.get("FM", [])
    d5n_eps = episodes.get("D5N", [])

    latest = date.today()
    latest_str = format_date_br(latest)

    # MC
    if mc_eps:
        ep = mc_eps[0]
        fname = extract_filename(ep["url"])
        dur = ep["duration"]
        dur_str = format_dur(dur)
        ep_date = format_date_br(ep["date"]) if ep["date"] else latest_str
        ep_summary = ep["summary"][:120] + "…" if len(ep["summary"]) > 120 else ep["summary"]

        html = re.sub(r'(<audio id="morningAudio" src=")[^"]*(")',
                      rf'\1/{fname}\2', html)
        html = re.sub(r'id="morningDate">[^<]+',
                      f'id="morningDate">{ep_date}', html)
        html = re.sub(r'aria-valuemax="(\d+)"(?=[^>]*id="morningProgress")',
                      f'aria-valuemax="{dur}"', html)
        html = re.sub(r'id="morningTime">[^<]+',
                      f'id="morningTime">0:00 / {dur_str}', html)
        html = re.sub(r'(id="morningSummary">)[^<]+',
                      rf'\g<1>{ep_summary}', html)
        html = re.sub(r'(href="/audio/)[^"]*("\s+download)',
                      rf'\g<1>{fname}\2', html)

        # MC archive buttons
        archive_re = r'<div class="morning-history"[^>]*>.*?</div>\s*</div>\s*</section>'
        archive_btns = ""
        for e in mc_eps[:7]:
            fname_e = extract_filename(e["url"])
            d_str = format_date_br(e["date"]) if e["date"] else latest_str
            dur_e = e["duration"]
            summ_e = e["summary"][:150] + "…" if len(e["summary"]) > 150 else e["summary"]
            summ_e = summ_e.replace('"', '&quot;')
            cls = "morning-episode"
            if fname_e == fname:
                cls += " is-active"
            archive_btns += (
                f'<button type="button" class="{cls}" '
                f'data-audio="/{fname_e}" data-date="{d_str}" '
                f'data-duration="{dur_e}" data-summary="{summ_e}" '
                f'onclick="selectMorningEpisode(this)" '
                f'aria-label="Ouvir Manhã Conectada de {d_str}">'
                f'<span>{d_str}</span><small>{format_dur(dur_e)}</small></button>'
            )
        new_mc_archive = (
            f'<div class="morning-history" aria-label="Edições da Manhã Conectada">'
            f'<span class="morning-history-label">Arquivo</span>'
            f'{archive_btns}</div>'
        )
        html = re.sub(archive_re, new_mc_archive, html, flags=re.DOTALL)

    # FM
    if fm_eps:
        ep = fm_eps[0]
        fname = extract_filename(ep["url"])
        dur = ep["duration"]
        dur_str = format_dur(dur)
        ep_date = format_date_br(ep["date"]) if ep["date"] else latest_str
        ep_summary = ep["summary"][:120] + "…" if len(ep["summary"]) > 120 else ep["summary"]

        html = re.sub(r'(<audio id="fechamentoAudio" src=")[^"]*(")',
                      rf'\1/{fname}\2', html)
        html = re.sub(r'id="fechamentoDate">[^<]+',
                      f'id="fechamentoDate">{ep_date}', html)
        html = re.sub(r'aria-valuemax="(\d+)"(?=[^>]*id="fechamentoProgress")',
                      f'aria-valuemax="{dur}"', html)
        html = re.sub(r'id="fechamentoTime">[^<]+',
                      f'id="fechamentoTime">0:00 / {dur_str}', html)
        html = re.sub(r'(id="fechamentoSummary">)[^<]+',
                      rf'\g<1>{ep_summary}', html)
        html = re.sub(r'(href="/audio/fechamento-)[^"]*("\s+download)',
                      rf'\g<1>{fname}" download', html)

        # FM archive buttons
        archive_re = r'<div class="morning-history"[^>]*>.*?</div>\s*</div>\s*</section>'
        archive_btns = ""
        for e in fm_eps[:7]:
            fname_e = extract_filename(e["url"])
            d_str = format_date_br(e["date"]) if e["date"] else latest_str
            dur_e = e["duration"]
            summ_e = e["summary"][:150] + "…" if len(e["summary"]) > 150 else e["summary"]
            summ_e = summ_e.replace('"', '&quot;')
            cls = "morning-episode fechamento-episode"
            if fname_e == fname:
                cls += " is-active"
            archive_btns += (
                f'<button type="button" class="{cls}" '
                f'data-audio="/{fname_e}" data-date="{d_str}" '
                f'data-duration="{dur_e}" data-summary="{summ_e}" '
                f'onclick="selectFechamentoEpisode(this)" '
                f'aria-label="Ouvir Fechamento de {d_str}">'
                f'<span>{d_str}</span><small>{format_dur(dur_e)}</small></button>'
            )
        new_fm_archive = (
            f'<div class="morning-history" aria-label="Edições do Fechamento">'
            f'<span class="morning-history-label">Arquivo</span>'
            f'{archive_btns}</div>'
        )
        html = re.sub(archive_re, new_fm_archive, html, flags=re.DOTALL)

    # D5N
    if d5n_eps:
        ep = d5n_eps[0]
        fname = extract_filename(ep["url"])
        dur = ep["duration"]
        dur_str = format_dur(dur)
        ep_date = format_date_br(ep["date"]) if ep["date"] else latest_str
        html = re.sub(r'(<audio id="audioEl" src=")[^"]*(")',
                      rf'\1/{fname}\2', html)

    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    episodes = {}
    for name, path in FEEDS.items():
        episodes[name] = parse_feed(path)
        print(f"  {name}: {len(episodes[name])} episódios em {path.name}")

    if not INDEX_HTML.exists():
        print(f"ERRO: {INDEX_HTML} não encontrado")
        sys.exit(1)

    html = INDEX_HTML.read_text(encoding="utf-8")
    html = update_index(html, episodes)

    if args.dry_run:
        print("DRY RUN — índice não escrito")
        return

    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"Atualizado: {INDEX_HTML}")


if __name__ == "__main__":
    main()
