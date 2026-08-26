#!/usr/bin/env python3
"""
gerar_pagina_d5n.py — Gera o site do Drop Five News conforme o BrandBook v1.0.
Inter · Midnight Navy · Electric Blue · Violet · Player custom
"""

import os, sys, re, json, argparse, subprocess
import html as html_lib
from datetime import datetime, timedelta

BASE = os.environ.get("D5N_BASE", os.path.dirname(os.path.abspath(__file__)))
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
    path = f"{BASE}/drop5news-trends-{date_str}.txt"
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

def load_coverage_for_date(date_str):
    """Carrega scores do Coverage Ledger SQLite para as notícias do dia.
    Retorna dict: {titulo_normalizado: {score, source_name, source_authority, pillar, quality_score}}
    """
    db_path = os.environ.get("D5N_COVERAGE_DB", os.path.join(BASE, ".coverage-ledger", "coverage.db"))
    result = {"scores": {}, "quality_score": None, "episode_num": None, "pillars_covered": []}
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Pega quality_score do episódio — primeiro tenta o mais recente com score, se não achar, pega qualquer um
        cur = conn.execute(
            "SELECT episode_num, quality_score, pillars_covered FROM episodes WHERE covered_date = ? AND quality_score IS NOT NULL ORDER BY episode_num DESC LIMIT 1",
            (date_str,)
        )
        ep = cur.fetchone()
        if not ep:
            cur = conn.execute(
                "SELECT episode_num, quality_score, pillars_covered FROM episodes WHERE covered_date = ? ORDER BY episode_num DESC LIMIT 1",
                (date_str,)
            )
            ep = cur.fetchone()
        if ep:
            result["quality_score"] = ep["quality_score"]
            result["episode_num"] = ep["episode_num"]
            try:
                result["pillars_covered"] = json.loads(ep["pillars_covered"])
            except:
                pass
        
        # Pega scores das notícias do dia
        cur = conn.execute(
            "SELECT title, score, source_name, source_authority, pillar FROM coverage WHERE covered_date = ? AND episode_num IS NOT NULL",
            (date_str,)
        )
        for row in cur.fetchall():
            # Normaliza título para match
            key = row["title"].strip().lower()
            # Remove pontuação
            key = re.sub(r'[^\w\s]', '', key)
            result["scores"][key] = {
                "score": row["score"],
                "source": row["source_name"] or "D5N",
                "authority": row["source_authority"] or 50,
                "pillar": row["pillar"],
            }
        conn.close()
    except Exception as e:
        print(f"⚠️  Coverage Ledger não disponível: {e}")
    return result

def match_coverage(titulo, coverage_data):
    """Tenta encontrar score no coverage para um título de notícia.
    Usa fuzzy match: direto, parcial, e por palavras-chave."""
    if not coverage_data or "scores" not in coverage_data:
        return None
    key = re.sub(r'[^\w\s]', '', titulo.strip().lower())
    
    # 1. Match direto
    if key in coverage_data["scores"]:
        return coverage_data["scores"][key]
    
    # 2. Um título contém o outro
    for k, v in coverage_data["scores"].items():
        if k in key or key in k:
            return v
    
    # 3. Match parcial (primeiros 40 chars)
    for k, v in coverage_data["scores"].items():
        if len(key) > 25 and len(k) > 25:
            if key[:35] == k[:35] or k[:35] in key or key[:35] in k:
                return v
    
    # 4. Match por palavras-chave (pelo menos 2 palavras significativas em comum)
    words = set(w for w in key.split() if len(w) > 3)
    best = None
    best_count = 0
    for k, v in coverage_data["scores"].items():
        kw = set(w for w in k.split() if len(w) > 3)
        common = len(words & kw)
        if common > best_count and common >= 2:
            best_count = common
            best = v
    if best:
        return best
    
    return None

def get_badge_html(score, source_name, authority):
    """Gera badge de score + tooltip 'Por que essa?'"""
    if score is None:
        return '<span class="score-badge score-none">—</span>'
    
    if score >= 85:
        badge_class = "score-hot"
        label = f"🔥 {int(score)}"
        tag = "⭐ Destaque"
    elif score >= 70:
        badge_class = "score-warm"
        label = f"🔥 {int(score)}"
        tag = "🔥 Tendência"
    elif score >= 50:
        badge_class = "score-mid"
        label = f"{int(score)}"
        tag = ""
    else:
        badge_class = "score-low"
        label = f"📉 {int(score)}"
        tag = ""
    
    tooltip = f"Score: {int(score)}/100 · Fonte: {source_name or 'D5N'} · Autoridade: {authority}/100"
    tag_html = f'<span class="curation-tag">{tag}</span>' if tag else ""
    return f'<span class="score-badge {badge_class}" title="{tooltip}">{label}</span>{tag_html}'

def get_pillar_avg_scores(coverage_data):
    """Calcula score medio por pilar a partir do coverage ledger."""
    if not coverage_data or "scores" not in coverage_data:
        return {}
    pillar_scores = {}
    for k, v in coverage_data["scores"].items():
        p = v.get("pillar", "").upper()
        if p not in pillar_scores:
            pillar_scores[p] = {"scores": [], "sources": set()}
        pillar_scores[p]["scores"].append(v["score"])
        pillar_scores[p]["sources"].add(v.get("source", ""))
    result = {}
    for p, data in pillar_scores.items():
        avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 50
        result[p] = {"avg": round(avg), "count": len(data["scores"]), "sources": ", ".join(sorted(data["sources"])[:3])}
    return result

def voice_schedule_name(date_str):
    """Escala editorial: Seg/Qua/Sáb Thalita; Ter/Qui Francisca; Sex dupla."""
    try:
        weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()
    except (TypeError, ValueError):
        return ""
    return {
        0: "Thalita",
        1: "Francisca",
        2: "Thalita",
        3: "Francisca",
        4: "Thalita + Francisca",
        5: "Thalita",
        6: "",
    }[weekday]


def get_voice_of_day(date_str):
    """Retorna a apresentação do dia conforme a escala usada pelo mixer e pelos gates."""
    name = voice_schedule_name(date_str)
    if not name:
        return None
    if name == "Thalita":
        return {"name": name, "bio": "Jornalista formal, precisa e analítica", "avatar": "🎙️",
                "tone": "formal", "tagline": "Drop Five News, com Thalita"}
    if name == "Francisca":
        return {"name": name, "bio": "Comunicadora casual, envolvente e direta", "avatar": "🎧",
                "tone": "casual", "tagline": "Drop Five News, com Francisca"}
    return {"name": name, "bio": "Edição especial com apresentação alternada", "avatar": "🎙️",
            "tone": "dual", "tagline": "Drop Five News, com Thalita e Francisca"}


def historical_voice_name(date_str):
    """Aplica aos créditos a mesma escala editorial efetivamente exigida no áudio."""
    return voice_schedule_name(date_str)

def format_data_br(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    dias = {0:'Segunda-feira',1:'Terça-feira',2:'Quarta-feira',3:'Quinta-feira',4:'Sexta-feira',5:'Sábado',6:'Domingo'}
    meses = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
    return f"{dias[d.weekday()]}, {d.day} de {meses[d.month]} de {d.year}"

def format_data_curta(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    meses = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
    return f"{d.day} {meses[d.month]} {d.year}"

def is_weekend(date_str):
    """Retorna True se a data cai em sábado (5) ou domingo (6)."""
    from datetime import datetime
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').weekday() >= 5
    except:
        return False

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


EXPECTED_CHAPTER_IDS = [
    "intro", "mundo", "brasil", "tecnologia", "economia", "interacao",
    "ofertas", "frase", "recomendacoes", "historia", "outro",
]
REQUIRED_CHAPTER_IDS = {"intro", "mundo", "brasil", "tecnologia", "economia", "outro"}
MIN_CHAPTERS = 7
CHAPTER_LABELS = {
    "intro": "Abertura",
    "mundo": "Mundo",
    "brasil": "Brasil",
    "tecnologia": "Tecnologia & IA",
    "economia": "Economia & Mercados",
    "ofertas": "Ofertas do Dia",
    "frase": "Frase do Dia",
    "interacao": "Sua vez",
    "recomendacoes": "Recomendações",
    "historia": "História do dia",
    "outro": "Encerramento",
}


def format_chapter_time(seconds):
    seconds = max(0, int(float(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def validate_chapters(chapters, duration):
    """Valida e normaliza os nove capítulos canônicos contra o MP3 real."""
    if not isinstance(chapters, list) or len(chapters) < MIN_CHAPTERS:
        return []
    ids = [chapter.get("id") for chapter in chapters]
    expected = [section_id for section_id in EXPECTED_CHAPTER_IDS if section_id in ids]
    if not REQUIRED_CHAPTER_IDS.issubset(ids) or ids != expected:
        return []
    try:
        total = float(duration)
        starts = [float(chapter["start"]) for chapter in chapters]
    except (KeyError, TypeError, ValueError):
        return []
    if total <= 0 or abs(starts[0]) > 0.05:
        return []
    if any(current >= following for current, following in zip(starts, starts[1:])):
        return []
    if starts[-1] >= total:
        return []

    normalized = []
    for index, chapter in enumerate(chapters):
        start = starts[index]
        end = starts[index + 1] if index + 1 < len(starts) else total
        chapter_id = chapter["id"]
        if end <= start:
            return []
        normalized.append({
            "id": chapter_id,
            "label": CHAPTER_LABELS[chapter_id],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
        })
    return normalized


def load_episode_chapters(date_str, duration):
    """Carrega o manifesto versionado do episódio; episódios antigos têm fallback vazio."""
    path = os.path.join(BASE, "chapters", f"{date_str}.json")
    try:
        with open(path, encoding="utf-8") as chapter_file:
            manifest = json.load(chapter_file)
        if manifest.get("editorial_date") != date_str:
            return []
        return validate_chapters(manifest.get("chapters"), duration)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return []


def render_chapter_segments(chapters):
    """Renderiza segmentos proporcionais, clicáveis e acessíveis como no YouTube."""
    rendered = []
    for index, chapter in enumerate(chapters):
        chapter_id = chapter.get("id")
        canonical_label = CHAPTER_LABELS[chapter_id] if chapter_id in CHAPTER_LABELS else str(chapter["label"])
        label = html_lib.escape(canonical_label, quote=True)
        timestamp = format_chapter_time(chapter["start"])
        rendered.append(
            f'<button type="button" class="chapter-segment" '
            f'style="--chapter-weight:{chapter["duration"]:.3f}" '
            f'data-chapter-index="{index}" data-chapter-start="{chapter["start"]:g}" '
            f'aria-label="Ir para o capítulo {label}, em {timestamp}">'
            f'<span class="chapter-segment-track"><span class="chapter-segment-fill"></span></span>'
            f'<span class="chapter-tooltip">{label}<small>{timestamp}</small></span>'
            f'</button>'
        )
    return "".join(rendered)


def chapters_data_attribute(chapters):
    payload = json.dumps(chapters, ensure_ascii=False, separators=(",", ":"))
    return html_lib.escape(payload, quote=True)


def find_latest_podcast():
    """Encontra o episódio publicado mais recente que existe em audio/.

    O podcast é público de segunda a sábado; domingo não gera episódio, mas o
    site continua exibindo o último player disponível.
    """
    history = load_episode_history()
    if not history:
        return None
    from datetime import datetime as _dt
    for entry in reversed(history):
        f = entry["file"]
        path = f"{AUDIO_DIR}/{f}"
        if not os.path.exists(path):
            continue
        try:
            ep_date = _dt.strptime(entry["date"], "%Y-%m-%d")
        except (KeyError, TypeError, ValueError):
            continue
        dur = get_duration(path)
        voice_name = historical_voice_name(entry["date"])
        return {
            "file": f,
            "path": f"/audio/{f}",
            "duration": dur,
            "dur_str": f"{dur//60}:{dur%60:02d}",
            "num": entry["num"].lstrip("0") or "0",
            "date": entry["date"],
            "voice": voice_name,
            "chapters": load_episode_chapters(entry["date"], dur),
        }
    return None

def list_episodes():
    """Lista episódios do histórico persistente (reverso, mais recente primeiro).
    Inclui voz do dia e duração para cada episódio existente."""
    from datetime import datetime as _dt

    history = load_episode_history()
    eps = []
    for entry in reversed(history):
        f = entry["file"]
        path = f"{AUDIO_DIR}/{f}"
        exists = os.path.exists(path)
        dur = get_duration(path) if exists else 0
        # Voice do dia
        try:
            vname = historical_voice_name(entry["date"])
        except: vname = ""
        eps.append({
            "file": f,
            "path": f"/audio/{f}",
            "dur_str": f"{dur//60}:{dur%60:02d}" if exists else "—",
            "duration": dur,
            "exists": exists,
            "num": entry["num"],
            "date": entry["date"],
            "voice": vname,
            "chapters": load_episode_chapters(entry["date"], dur) if exists else [],
        })
    return eps


def _manha_summary(date_str):
    """Extrai o cold open do roteiro canônico sem expor metadados técnicos."""
    source_path = os.path.join(BASE, "manha-conectada", "roteiros", f"source-manha-{date_str}.md")
    try:
        with open(source_path, encoding="utf-8") as source_file:
            content = source_file.read()
        match = re.search(
            r"## Roteiro aprovado\s+(.+?)(?:\n\s*\n|\n## )",
            content,
            flags=re.S,
        )
        if not match:
            return "As notícias que já definiram a manhã e o que ainda pode mudar até o começo da tarde."
        summary = re.sub(r"\s+", " ", match.group(1)).strip()
        summary = re.sub(
            r"\s*Eu sou Antonio e esta é a Manhã Conectada, do Drop Five News\.?",
            "",
            summary,
            flags=re.I,
        ).strip()
        if len(summary) > 235:
            summary = summary[:232].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
        return summary
    except OSError:
        return "As notícias que já definiram a manhã e o que ainda pode mudar até o começo da tarde."


def load_manha_conectada_episodes(limit=None):
    """Carrega apenas edições canônicas, publicáveis e com áudio presente."""
    manifest_dir = os.path.join(BASE, "manha-conectada", "manifests")
    if not os.path.isdir(manifest_dir):
        return []

    episodes = []
    for manifest_path in sorted(
        (os.path.join(manifest_dir, name) for name in os.listdir(manifest_dir) if name.endswith(".json")),
        reverse=True,
    ):
        try:
            with open(manifest_path, encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
            date_str = str(manifest.get("date", ""))
            datetime.strptime(date_str, "%Y-%m-%d")
            expected_file = f"manha-conectada-{date_str}.mp3"
            output_name = os.path.basename(str(manifest.get("output", "")))
            audio_path = os.path.join(BASE, "manha-conectada", "audio", expected_file)
            duration = round(float(manifest.get("audio", {}).get("duration", 0)))
            if (
                str(manifest.get("program", "")).strip().upper() != "MANHÃ CONECTADA"
                or manifest.get("prototype") is not False
                or output_name != expected_file
                or not os.path.isfile(audio_path)
                or duration <= 0
            ):
                continue
            voice = str(manifest.get("voice", ""))
            episodes.append({
                "date": date_str,
                "date_label": format_data_curta(date_str),
                "file": expected_file,
                "path": f"/audio/{expected_file}",
                "duration": duration,
                "dur_str": f"{duration // 60}:{duration % 60:02d}",
                "presenter": "Antonio" if "Antonio" in voice else voice,
                "summary": _manha_summary(date_str),
                "words": int(manifest.get("text_gate", {}).get("words", 0) or 0),
            })
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if limit is not None and len(episodes) >= limit:
            break
    return episodes


def render_manha_conectada_program(episodes):
    """Renderiza o programa matinal como produto próprio dentro da marca D5N."""
    if not episodes:
        return ""

    latest = episodes[0]
    episode_buttons = []
    for index, episode in enumerate(episodes):
        active = " is-active" if index == 0 else ""
        episode_buttons.append(
            f'<button type="button" class="morning-episode{active}" '
            f'data-audio="{html_lib.escape(episode["path"], quote=True)}" '
            f'data-date="{html_lib.escape(episode["date_label"], quote=True)}" '
            f'data-duration="{episode["duration"]}" '
            f'data-summary="{html_lib.escape(episode["summary"], quote=True)}" '
            f'onclick="selectMorningEpisode(this)" '
            f'aria-label="Ouvir Manhã Conectada de {html_lib.escape(episode["date_label"], quote=True)}">'
            f'<span>{html_lib.escape(episode["date_label"])}</span>'
            f'<small>{episode["dur_str"]}</small></button>'
        )

    return f'''
  <section class="morning-program" id="manha-conectada" data-animate aria-labelledby="morningTitle">
    <div class="morning-intro">
      <div class="morning-kicker"><span class="morning-sun" aria-hidden="true"></span> Edição das 11</div>
      <h2 id="morningTitle">Manhã<br><strong>Conectada</strong></h2>
      <p>Um briefing para entender o que definiu a manhã — e o sinal que ainda pode mudar o dia.</p>
      <div class="morning-byline"><span>Com Antonio</span><span>Seg–Sex · 11h</span></div>
    </div>
    <div class="morning-listen">
      <div class="morning-now">
        <span class="morning-live-dot" aria-hidden="true"></span>
        <span id="morningDate">{html_lib.escape(latest["date_label"])}</span>
        <span>Última edição</span>
      </div>
      <p class="morning-summary" id="morningSummary">{html_lib.escape(latest["summary"])}</p>
      <div class="morning-player">
        <button class="morning-play" id="morningPlayBtn" type="button" onclick="toggleMorningPlay()" aria-label="Reproduzir Manhã Conectada">
          <span id="morningPlayGlyph" aria-hidden="true">▶</span>
        </button>
        <div class="morning-progress" id="morningProgress" role="slider" tabindex="0" aria-label="Progresso da Manhã Conectada" aria-valuemin="0" aria-valuemax="{latest["duration"]}" aria-valuenow="0">
          <div class="player-chapters" id="morningChapters" data-chapters="[]"><div class="chapter-segment" style="--chapter-weight:1" data-chapter-index="0"><span class="chapter-segment-track"><span class="chapter-segment-fill" id="morningProgressFill"></span></span><span class="chapter-tooltip">Manhã Conectada<small>00:00</small></span></div></div>
        </div>
        <span class="morning-time" id="morningTime">0:00 / {latest["dur_str"]}</span>
        <a class="morning-download" id="morningDownload" href="{html_lib.escape(latest["path"], quote=True)}" download aria-label="Baixar esta edição">↓</a>
      </div>
      <audio id="morningAudio" src="{html_lib.escape(latest["path"], quote=True)}" preload="metadata"></audio>
      <div class="morning-history" aria-label="Edições anteriores da Manhã Conectada">
        <span class="morning-history-label">Arquivo</span>
        {''.join(episode_buttons)}
      </div>
    </div>
  </section>'''



def _fechamento_summary(date_str):
    source_path = os.path.join(BASE, "fechamento", "roteiros", f"source-fechamento-{date_str}.md")
    try:
        with open(source_path, encoding="utf-8") as f:
            content = f.read()
        m = re.search(r"## Roteiro aprovado\s+(.+?)(?:\n\s*\n|\n## )", content, flags=re.S)
        if not m:
            return "O resumo do pregao com contexto, numeros e o Radar Amanha."
        summary = re.sub(r"\s+", " ", m.group(1)).strip()
        summary = re.sub(r"\s*Boa noite! Eu sou Antonio e este e o Fechamento do Mercado, do Drop Five News\.?", "", summary, flags=re.I).strip()
        if len(summary) > 235:
            summary = summary[:232].rsplit(" ", 1)[0].rstrip(" ,;:") + "\u2026"
        return summary
    except OSError:
        return "O resumo do pregao com contexto, numeros e o Radar Amanha."

def load_fechamento_episodes(limit=None):
    manifest_dir = os.path.join(BASE, "fechamento", "manifests")
    if not os.path.isdir(manifest_dir):
        return []
    episodes = []
    for manifest_path in sorted((os.path.join(manifest_dir, n) for n in os.listdir(manifest_dir) if n.endswith(".json")), reverse=True):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            date_str = str(manifest.get("date", ""))
            datetime.strptime(date_str, "%Y-%m-%d")
            expected_file = f"fechamento-{date_str}.mp3"
            output_name = os.path.basename(str(manifest.get("output", "")))
            audio_path = os.path.join(BASE, "fechamento", "audio", expected_file)
            duration = round(float(manifest.get("audio", {}).get("duration", 0)))
            if (str(manifest.get("program", "")).strip().upper() != "FECHAMENTO DO MERCADO" or manifest.get("prototype") is not False or output_name != expected_file or not os.path.isfile(audio_path) or duration <= 0):
                continue
            voice = str(manifest.get("voice", ""))
            episodes.append({"date": date_str, "date_label": format_data_curta(date_str), "file": expected_file, "path": f"/audio/{expected_file}", "duration": duration, "dur_str": f"{duration // 60}:{duration % 60:02d}", "presenter": "Antonio" if "Antonio" in voice else voice, "summary": _fechamento_summary(date_str), "words": int(manifest.get("text_gate", {}).get("words", 0) or 0)})
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if limit is not None and len(episodes) >= limit:
            break
    return episodes

def render_fechamento_program(episodes):
    if not episodes:
        return ""
    latest = episodes[0]
    btns = []
    for i, ep in enumerate(episodes):
        active = " is-active" if i == 0 else ""
        btns.append('<button type="button" class="morning-episode fechamento-episode' + active + '" data-audio="' + html_lib.escape(ep["path"], quote=True) + '" data-date="' + html_lib.escape(ep["date_label"], quote=True) + '" data-duration="' + str(ep["duration"]) + '" data-summary="' + html_lib.escape(ep["summary"], quote=True) + '" onclick="selectFechamentoEpisode(this)" aria-label="Ouvir Fechamento de ' + html_lib.escape(ep["date_label"], quote=True) + '"><span>' + html_lib.escape(ep["date_label"]) + '</span><small>' + ep["dur_str"] + '</small></button>')
    return '<section class="morning-program fechamento-program" id="fechamento" data-animate aria-labelledby="fechamentoTitle"><div class="morning-intro fechamento-intro"><div class="morning-kicker fechamento-kicker"><span class="morning-sun fechamento-sun" aria-hidden="true"></span> Edição das 17h</div><h2 id="fechamentoTitle">Fechamento<br><strong>do Mercado</strong></h2><p>O pregao em contexto — numeros, porques e o Radar Amanha.</p><div class="morning-byline"><span>Com Antonio</span><span>Seg–Sex \u00b7 17h</span></div></div><div class="morning-listen"><div class="morning-now"><span class="morning-live-dot fechamento-dot" aria-hidden="true"></span><span id="fechamentoDate">' + html_lib.escape(latest["date_label"]) + '</span><span>Ultima edicao</span></div><p class="morning-summary" id="fechamentoSummary">' + html_lib.escape(latest["summary"]) + '</p><div class="morning-player"><button class="morning-play" id="fechamentoPlayBtn" type="button" onclick="toggleFechamentoPlay()" aria-label="Reproduzir Fechamento"><span id="fechamentoPlayGlyph" aria-hidden="true">\u25b6</span></button><div class="morning-progress" id="fechamentoProgress" role="slider" tabindex="0" aria-label="Progresso do Fechamento" aria-valuemin="0" aria-valuemax="' + str(latest["duration"]) + '" aria-valuenow="0"><div class="player-chapters" id="fechamentoChapters" data-chapters="[]"><div class="chapter-segment" style="--chapter-weight:1" data-chapter-index="0"><span class="chapter-segment-track"><span class="chapter-segment-fill" id="fechamentoProgressFill"></span></span><span class="chapter-tooltip">Fechamento do Mercado<small>00:00</small></span></div></div></div><span class="morning-time" id="fechamentoTime">0:00 / ' + latest["dur_str"] + '</span><a class="morning-download" id="fechamentoDownload" href="' + html_lib.escape(latest["path"], quote=True) + '" download>\u2193</a></div><audio id="fechamentoAudio" src="' + html_lib.escape(latest["path"], quote=True) + '" preload="metadata"></audio><div class="morning-history" aria-label="Edicoes do Fechamento"><span class="morning-history-label">Arquivo</span>' + ''.join(btns) + '</div></div></section>'

def gerar_html(date, data_br, data_curta, noticias, podcast, episodios, coverage_data=None, voice=None):
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
    n_pilares = 4  # Fix: sempre 4 pilares (Global, Tech, Economia, Brasil)
    pod_dur = podcast['dur_str'] if podcast else "0:00"
    manha_episodes = load_manha_conectada_episodes()
    morning_html = render_manha_conectada_program(manha_episodes)
    morning_nav = '<a class="header-program-link" href="#manha-conectada">Manhã Conectada</a>' if morning_html else ''
    fechamento_episodes = load_fechamento_episodes()
    fechamento_html = render_fechamento_program(fechamento_episodes)
    fechamento_nav = '<a class="header-program-link" href="#fechamento">Fechamento</a>' if fechamento_html else ''
    premium_block = fechamento_html if fechamento_html else '  <div class="premium-block" data-animate>\n    <div class="premium-eyebrow">\u2726 Proximo formato \u00b7 Em desenvolvimento</div>\n    <h3 class="premium-title">Fechamento do Mercado</h3>\n    <p class="premium-desc">O resumo das 17h com mercados, d\u00f3lar, ativos e os movimentos que ajudam a preparar o pr\u00f3ximo dia.</p>\n    <span class="btn-premium" aria-label="Fechamento do Mercado em desenvolvimento">Em breve</span>\n  </div>'
    
    # Quality score do Coverage Ledger
    qs = coverage_data.get("quality_score") if coverage_data else None
    qs_stat = f'\n      <div class="divider-v"></div>\n      <div class="hero-stat quality-stat"><strong>{int(qs)}</strong><span>qualidade</span></div>' if qs is not None else ''

    # ── Player com capítulos reais e download ──
    player_html = ""
    if podcast:
        pod_dur_sec = int(podcast.get("duration", 0))
        chapters = podcast.get("chapters") or []
        display_chapters = chapters or [{
            "id": "full",
            "label": "Episódio completo",
            "start": 0,
            "end": pod_dur_sec,
            "duration": pod_dur_sec,
        }]
        chapters_json = chapters_data_attribute(display_chapters)
        chapter_segments = render_chapter_segments(display_chapters)
        current_chapter = (
            f'Capítulo 1 de {len(chapters)} · {html_lib.escape(chapters[0]["label"])}'
            if chapters else "Episódio completo"
        )
        total_dur_min = pod_dur_sec // 60
        total_dur_sec = pod_dur_sec % 60

        player_html = f'''
    <section class="d5n-program" data-animate aria-labelledby="d5nTitle">
      <div class="d5n-intro">
        <div class="d5n-kicker"><span class="d5n-sun" aria-hidden="true"></span> Edição das 05h</div>
        <h2 id="d5nTitle">Hoje no<br><strong>Drop Five News</strong></h2>
        <p>Notícias essenciais, contexto e tecnologia em um briefing para começar o dia informado.</p>
        <div class="morning-byline"><span>Curadoria diária</span><span>Seg–Sáb · 05h</span></div>
      </div>
      <div class="morning-listen morning-listen--d5n">
        <div class="morning-now" style="color:var(--d5n)"><span class="morning-live-dot" style="background:var(--d5n)"></span><span>Última edição</span><span>{data_curta}</span></div>
        <div class="player-bar" style="margin:1rem 0 0">
          <div class="player-track">
        <button class="play-btn" id="playBtn" onclick="togglePlay()" aria-label="Reproduzir episódio">
          <svg id="playIcon" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
          <svg id="pauseIcon" viewBox="0 0 24 24" fill="currentColor" style="display:none"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
        </button>
        <div class="player-progress" id="progressBar" onclick="seekAudio(event)" role="slider" tabindex="0" aria-label="Progresso do episódio" aria-valuemin="0" aria-valuemax="{pod_dur_sec}" aria-valuenow="0">
          <div class="player-chapters" id="chaptersContainer" data-chapters="{chapters_json}">{chapter_segments}</div>
        </div>
        <span class="player-time" id="playerTime">0:00 / {total_dur_min}:{total_dur_sec:02d}</span>
        <a class="player-download" href="{podcast["path"]}" download title="Baixar MP3">↓ MP3</a>
        <button class="player-copy-btn" onclick="copyAudioLink()" title="Copiar link do áudio" id="copyBtn">🔗</button>
        <button class="speed-btn" id="speedBtn" onclick="cycleSpeed()" title="Velocidade">1×</button>
      </div>
      <div class="player-meta">
        <div class="player-title">Hoje no Drop Five News — Episódio #{podcast["num"]} — {data_curta}</div>
        <div class="chapter-current" id="currentChapter" aria-live="polite">{current_chapter}</div>
      </div>
        </div>
      </div>
    </section>
    <audio id="audioEl" src="{podcast["path"]}" preload="metadata"></audio>'''
    else:
        player_html = ''

    # ── Voice of the Day ──
    voice_html = ""
    if voice:
        voice_html = f'''
    <div class="voice-section">
      <div class="voice-avatar">{voice["avatar"]}</div>
      <div class="voice-info">
        <div class="voice-name">Apresentação: {voice["name"]}</div>
        <div class="voice-bio">{voice["bio"]}</div>
      </div>
    </div>'''

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
            # Tenta match com coverage ledger
            cov = match_coverage(ntc['titulo'], coverage_data)
            if not cov and coverage_data:
                # Fallback: usar media do pilar
                pavg = get_pillar_avg_scores(coverage_data)
                pkey = (ntc.get('pilar') or 'GLOBAL').upper()
                if pkey in pavg:
                    cov = {"score": pavg[pkey]["avg"], "source": pavg[pkey]["sources"][:30] if pavg[pkey]["sources"] else "D5N", "authority": 50}
            score_badge = get_badge_html(cov['score'] if cov else None, cov['source'] if cov else 'D5N', cov['authority'] if cov else 50) if coverage_data else ''
            
            # Adicionar classe de pilar para borda colorida
            pilar_class = f' pilar-{cls_name}' if cls_name else ''
            
            news_items += f'''
      <div class="news-item{featured}{pilar_class}" data-animate>
        <span class="news-num">{num}</span>
        <span class="news-headline">{ntc['titulo']}</span>
        <span class="news-meta"><span class="news-source">{fonte}</span>{score_badge}</span>
      </div>'''

        # Contexto rápido por pilar
        context_text = f"{len(lista)} notícias"
        if pilar == 'Global':
            context_text += " · Foco: geopolítica, eleições, conflitos"
        elif pilar == 'Tech':
            context_text += " · Foco: IA, inovação, regulamentação"
        elif pilar == 'Economia':
            context_text += " · Foco: mercados, crypto, indicadores"
        elif pilar == 'Brasil':
            context_text += " · Foco: política, economia, justiça"
        
        sections_html += f'''
  <section class="section">
    <div class="section-header">
      <span class="section-icon">{icon}</span>
      <span class="section-name {cls_name}">{pilar_display}</span>
      <span class="section-count">{len(lista)} notícias</span>
    </div>
    <div class="section-context">
      <strong>O dia:</strong> {context_text}
    </div>
    <div class="news-list">{news_items}
    </div>
  </section>'''

    # ── Episódios anteriores (archive) — 3 visíveis + dropdown ──
    archive_html = ""
    archive_count = 0
    if episodios:
        archive_count = len(episodios)
        for i, ep in enumerate(episodios):
            vis_class = "archive-link--visible" if i < 3 else "archive-link--hidden"
            voice_badge = f'<span class="archive-voice">{ep.get("voice","")}</span>' if ep.get("voice") else ""
            ep_duration = int(ep.get("duration", 0))
            ep_chapters = ep.get("chapters") or [{
                "id": "full", "label": "Episódio completo", "start": 0,
                "end": ep_duration, "duration": ep_duration,
            }]
            ep_chapters_attr = chapters_data_attribute(ep_chapters)
            if ep.get("exists", False):
                archive_html += f'''
    <div class="archive-link {vis_class}" data-audio="{ep["path"]}" data-duration="{ep_duration}" data-episode="{ep["num"]}" data-date="{format_data_curta(ep["date"])}" data-chapters="{ep_chapters_attr}" onclick="playArchive(this)">
      <div>
        <div class="archive-link-date">Ep #{ep["num"]} · {format_data_curta(ep["date"])}</div>
        <div class="archive-link-meta">{ep["dur_str"]} {voice_badge}</div>
      </div>
      <span class="archive-link-play">▶</span>
    </div>'''
            else:
                archive_html += f'''
    <div class="archive-link {vis_class} archive-link--missing">
      <div>
        <div class="archive-link-date">Ep #{ep["num"]} · {format_data_curta(ep["date"])}</div>
        <div class="archive-link-meta">indisponível</div>
      </div>
      <span class="archive-link-archive-ghost">◌</span>
    </div>'''
        if archive_count > 3:
            archive_html += f'''
    <button class="archive-toggle" type="button" aria-expanded="false" aria-controls="archive-list">
      <span class="archive-toggle-label">Ver episódios anteriores ({archive_count - 3})</span>
      <span class="archive-toggle-arrow">↓</span>
    </button>'''
        archive_html = f'<div class="archive-archive" id="archive-list">\n{archive_html}\n  </div>'

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0B1020">
<meta name="description" content="Drop Five News: notícias essenciais, contexto e tecnologia em um podcast diário, de segunda a sábado.">
<meta name="author" content="Drop Five News">
<link rel="canonical" href="https://d5n-daily.netlify.app/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/site.webmanifest">
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
<title>Drop Five News — {data_br}</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"PodcastSeries","name":"Drop Five News","url":"https://d5n-daily.netlify.app/","description":"Notícias essenciais, contexto e tecnologia em um podcast diário.","inLanguage":"pt-BR"}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
    font-family:'Inter',sans-serif; font-weight:300;
    line-height:1.6; min-height:100vh; overflow-x:hidden;
  }}
  header {{
    position:sticky; top:0; z-index:100; background:var(--bg);
    border-bottom:1px solid var(--border); padding:0 2rem;
    display:flex; align-items:center; justify-content:space-between; height:52px;
  }}
  .logo {{ font-family:'Inter',sans-serif; font-size:1rem; font-weight:700; letter-spacing:0.04em; color:var(--text); text-decoration:none; }}
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
  .hero-title {{ font-family:'Inter',sans-serif; font-size:clamp(2rem,5vw,3.2rem); font-weight:700; line-height:1.1; color:var(--text); margin-bottom:0.5rem; }}
  .hero-title em {{ font-style:italic; color:var(--accent); }}
  .hero-sub {{ font-size:0.85rem; color:var(--muted); margin-top:1rem; display:flex; align-items:center; gap:1.5rem; }}
  .hero-stat {{ display:flex; align-items:baseline; gap:0.35rem; }}
  .hero-stat strong {{ font-family:'Inter',sans-serif; font-size:1.4rem; color:var(--text); font-weight:400; }}
  .hero-stat span {{ font-size:0.7rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); }}
  .divider-v {{ width:1px; height:24px; background:var(--border); }}

  .player-bar {{ margin:2rem 0 0; padding:0.75rem 1.25rem; background:var(--surface); border:1px solid var(--border); border-radius:14px; position:relative; overflow:hidden; }}
  .player-track {{ display:flex; align-items:center; gap:0.5rem; }}
  .play-btn {{ width:32px; height:32px; border-radius:50%; border:1px solid var(--accent-dim); background:transparent; color:var(--accent); cursor:pointer; flex-shrink:0; display:flex; align-items:center; justify-content:center; transition:all 0.2s; }}
  .play-btn:hover {{ background:var(--accent-dim); color:#fff; }}
  .play-btn svg {{ width:14px; height:14px; }}
  .player-progress {{ flex:1; height:10px; cursor:pointer; position:relative; min-width:120px; }}
  .player-chapters {{ position:absolute; inset:0; display:flex; gap:3px; align-items:center; z-index:3; }}
  .chapter-segment {{ position:relative; flex:var(--chapter-weight) 1 0; min-width:4px; height:100%; padding:0; border:0; background:transparent; cursor:pointer; overflow:visible; }}
  .chapter-segment-track {{ position:absolute; inset:1px 0; overflow:hidden; border-radius:999px; background:var(--border); transition:transform .15s ease,background .15s ease; }}
  .chapter-segment-fill {{ display:block; height:100%; width:0; border-radius:inherit; background:var(--brand-gradient); transition:width .1s linear; }}
  .chapter-segment:hover .chapter-segment-track,.chapter-segment:focus-visible .chapter-segment-track,.chapter-segment.is-active .chapter-segment-track {{ transform:scaleY(1.45); background:var(--accent-dim); }}
  .chapter-segment:focus-visible {{ outline:2px solid var(--brand-cyan); outline-offset:4px; border-radius:3px; }}
  .chapter-tooltip {{ position:absolute; z-index:20; bottom:20px; left:50%; transform:translate(-50%,4px); opacity:0; visibility:hidden; pointer-events:none; background:#05080d; border:1px solid var(--border); color:#fff; font-size:.62rem; font-weight:600; line-height:1.2; padding:7px 9px; border-radius:6px; white-space:nowrap; box-shadow:0 8px 24px rgba(0,0,0,.35); transition:opacity .15s ease,transform .15s ease; }}
  .chapter-tooltip small {{ display:block; color:var(--text-secondary); font-size:.56rem; font-weight:500; margin-top:3px; }}
  .chapter-segment:hover .chapter-tooltip,.chapter-segment:focus-visible .chapter-tooltip {{ opacity:1; visibility:visible; transform:translate(-50%,0); }}
  .player-time {{ font-family:'DM Mono',monospace; font-size:0.6rem; color:var(--muted); white-space:nowrap; flex-shrink:0; }}
  .player-download {{ color:var(--muted); text-decoration:none; font-size:0.6rem; flex-shrink:0; transition:color 0.2s; }}
  .player-download:hover {{ color:var(--accent); }}
  .player-copy-btn {{ width:22px; height:22px; border:none; background:transparent; color:var(--muted); cursor:pointer; font-size:0.65rem; display:flex; align-items:center; justify-content:center; flex-shrink:0; border-radius:3px; transition:all 0.15s; }}
  .player-copy-btn:hover {{ color:var(--accent); background:rgba(200,169,110,0.06); }}
  .player-copy-btn.copied {{ color:#4ade80; }}
  .speed-btn {{ padding:2px 7px; border-radius:3px; border:1px solid var(--accent-dim); background:transparent; color:var(--muted); cursor:pointer; flex-shrink:0; font-family:'Inter',sans-serif; font-size:0.55rem; font-weight:500; letter-spacing:0.04em; transition:all 0.15s; }}
  .speed-btn:hover {{ color:var(--accent); border-color:var(--accent); }}
  .player-meta {{ display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-top:.55rem; }}
  .player-title {{ font-size:0.65rem; color:var(--muted); letter-spacing:0.04em; }}
  .chapter-current {{ font-size:.65rem; color:var(--brand-cyan); font-weight:600; letter-spacing:.02em; text-align:right; }}

  .section {{ padding:2.5rem 0; border-bottom:1px solid var(--border-lt); }}
  .section-header {{ display:flex; align-items:baseline; gap:0.75rem; margin-bottom:1.75rem; padding-bottom:0.75rem; border-bottom:1px solid var(--border); }}
  .section-icon {{ font-size:0.85rem; }}
  .section-name {{ font-family:'Inter',sans-serif; font-size:0.9rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; }}
  .section-name.global {{ color:var(--global); }}
  .section-name.tech {{ color:var(--tech); }}
  .section-name.econ {{ color:var(--econ); }}
  .section-count {{ font-size:0.65rem; color:var(--muted); letter-spacing:0.1em; margin-left:auto; }}
  .section-context {{
    margin-bottom:1rem; padding:0.75rem 1rem; background:var(--surface);
    border:1px solid var(--border); border-radius:6px; font-size:0.85rem;
    color:var(--text-secondary); line-height:1.5;
  }}
  .section-context strong {{ color:var(--text); font-weight:600; }}

  .search-bar {{
    margin:2rem 0; padding:0.75rem 1rem; background:var(--surface);
    border:1px solid var(--border); border-radius:6px; display:flex;
    align-items:center; gap:0.75rem;
  }}
  .search-bar input {{
    flex:1; background:transparent; border:none; color:var(--text);
    font-size:0.9rem; outline:none;
  }}
  .search-bar input::placeholder {{ color:var(--faint); }}
  .filter-buttons {{
    display:flex; gap:0.5rem; margin-bottom:1.5rem; flex-wrap:wrap;
  }}
  .filter-btn {{
    padding:0.5rem 1rem; background:var(--surface); border:1px solid var(--border);
    border-radius:6px; color:var(--text-secondary); font-size:0.85rem;
    cursor:pointer; transition:all 0.2s;
  }}
  .filter-btn:hover {{ background:var(--surface-raised); color:var(--text); }}
  .filter-btn.active {{
    background:var(--accent); border-color:var(--accent); color:#fff;
  }}

  .news-list {{ display:flex; flex-direction:column; }}
    display:flex; gap:0.5rem; margin-bottom:1.5rem; flex-wrap:wrap;
  }}
  .filter-btn {{
    padding:0.5rem 1rem; background:var(--surface); border:1px solid var(--border);
    border-radius:6px; color:var(--text-secondary); font-size:0.85rem;
    cursor:pointer; transition:all 0.2s;
  }}
  .filter-btn:hover {{ background:var(--surface-raised); color:var(--text); }}
  .filter-btn.active {{
    background:var(--accent); border-color:var(--accent); color:#fff;
  }}

  .news-list {{ display:flex; flex-direction:column; }}
  .news-item {{ display:grid; grid-template-columns:2.5rem 1fr auto; gap:0 1rem; align-items:start; padding:1.1rem 0; border-bottom:1px solid var(--border-lt); cursor:pointer; opacity:1; transform:none; transition:background 0.2s; position:relative; }}
  .news-item:last-child {{ border-bottom:none; }}
  .news-item.visible {{ opacity:1; transform:translateY(0); }}
  .news-item:hover {{ background:var(--surface); margin:0 -1.25rem; padding-left:1.25rem; padding-right:1.25rem; border-radius:2px; }}
  .news-num {{ font-family:'Inter',sans-serif; font-size:0.7rem; color:var(--faint); padding-top:0.15rem; text-align:right; font-style:italic; }}
  .news-headline {{ font-size:0.925rem; font-weight:400; line-height:1.45; color:var(--text); transition:color 0.2s; }}
  .news-item:hover .news-headline {{ color:#fff; }}
  .news-source {{ font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); white-space:nowrap; padding-top:0.2rem; transition:color 0.2s; }}
  .news-item:hover .news-source {{ color:var(--accent); }}
  .news-item.featured .news-headline {{ font-family:'Inter',sans-serif; font-size:1.05rem; font-weight:700; line-height:1.35; }}
  .news-item.featured .news-num {{ font-size:0.8rem; color:var(--accent-dim); }}

  .premium-block {{ margin:2.5rem 0; padding:1.5rem; border:1px solid var(--accent-dim); border-radius:3px; background:linear-gradient(135deg,rgba(200,169,110,0.04) 0%,transparent 60%); position:relative; overflow:hidden; }}

  /* ── Score Badges ── */
  .news-meta {{ display:flex; align-items:center; gap:0.5rem; padding-top:0.2rem; }}
  .score-badge {{ display:inline-flex; align-items:center; gap:0.25rem; font-size:0.58rem; font-weight:500; letter-spacing:0.04em; padding:1px 6px; border-radius:3px; cursor:help; transition:all 0.2s; }}
  .score-badge:hover {{ transform:scale(1.05); }}
  .score-hot {{ background:rgba(230,180,60,0.15); color:#e6b43c; border:1px solid rgba(230,180,60,0.3); }}
  .score-warm {{ background:rgba(230,140,60,0.12); color:#e68c3c; border:1px solid rgba(230,140,60,0.25); }}
  .score-mid {{ background:rgba(148,163,184,0.1); color:var(--muted); border:1px solid rgba(148,163,184,0.15); }}
  .score-low {{ background:rgba(224,96,96,0.1); color:var(--red); border:1px solid rgba(224,96,96,0.2); }}
  .score-none {{ background:rgba(148,163,184,0.05); color:var(--faint); border:1px solid rgba(148,163,184,0.08); }}
  .curation-tag {{ display:inline-flex; font-size:0.55rem; font-weight:500; letter-spacing:0.05em; padding:1px 5px; border-radius:2px; }}
  .curation-tag:first-letter {{ display:none; }}

  /* ── Quality Stat ── */
  .quality-stat strong {{ color:var(--global) !important; }}

  /* ── Voice of the Day ── */
  .voice-section {{ margin:2rem 0 1rem; padding:1.25rem; border:1px solid var(--border); border-radius:3px; background:var(--surface); display:flex; align-items:center; gap:1rem; }}
  .voice-avatar {{ width:40px; height:40px; border-radius:50%; background:var(--bg); border:1px solid var(--accent-dim); display:flex; align-items:center; justify-content:center; font-size:1.2rem; flex-shrink:0; }}
  .voice-info {{ flex:1; min-width:0; }}
  .voice-name {{ font-family:'Inter',sans-serif; font-size:0.82rem; font-weight:700; color:var(--text); }}
  .voice-bio {{ font-size:0.7rem; color:var(--muted); }}
  .premium-block::before {{ content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,var(--accent),transparent); opacity:0.5; }}
  .premium-eyebrow {{ font-size:0.6rem; letter-spacing:0.2em; text-transform:uppercase; color:var(--accent); margin-bottom:0.6rem; display:flex; align-items:center; gap:0.5rem; }}
  .premium-eyebrow::after {{ content:''; flex:1; height:1px; background:var(--accent-dim); opacity:0.4; }}
  .premium-title {{ font-family:'Inter',sans-serif; font-size:1.05rem; font-weight:700; color:var(--text); margin-bottom:0.5rem; }}
  .premium-desc {{ font-size:0.82rem; color:var(--muted); line-height:1.5; margin-bottom:1.2rem; }}
  .premium-preview {{ display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem; padding:1rem; background:rgba(0,0,0,0.3); border-radius:2px; border-left:2px solid var(--accent-dim); filter:blur(3px); user-select:none; pointer-events:none; }}
  .premium-preview-line {{ height:10px; background:var(--faint); border-radius:2px; }}
  .premium-preview-line:nth-child(1) {{ width:85%; }}
  .premium-preview-line:nth-child(2) {{ width:70%; }}
  .premium-preview-line:nth-child(3) {{ width:90%; }}
  .premium-preview-line:nth-child(4) {{ width:60%; }}
  .btn-premium {{ display:inline-flex; align-items:center; gap:0.5rem; background:transparent; border:1px solid var(--accent); color:var(--accent); font-family:'Inter',sans-serif; font-size:0.72rem; font-weight:500; letter-spacing:0.12em; text-transform:uppercase; padding:0.5rem 1.1rem; border-radius:2px; cursor:pointer; text-decoration:none; transition:all 0.2s; }}
  .btn-premium:hover {{ background:var(--accent); color:var(--bg); }}

  /* Premium programs grid (Manhã Conectada + Fechamento) */
  .premium-programs {{ display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin:1.25rem 0 1.5rem; }}
  .premium-program {{ padding:1rem; background:rgba(0,0,0,0.25); border:1px solid var(--border); border-radius:4px; }}
  .premium-program-time {{ font-family:'Inter',sans-serif; font-size:1.4rem; font-weight:700; color:var(--accent); margin-bottom:0.3rem; letter-spacing:-0.02em; }}
  .premium-program-name {{ font-size:0.85rem; font-weight:500; color:var(--text); margin-bottom:0.6rem; }}
  .premium-program-hook {{ font-size:0.72rem; line-height:1.55; color:var(--muted); margin-bottom:0.75rem; }}
  .premium-program-hook strong {{ color:var(--text); font-weight:500; }}
  .premium-program-meta {{ font-size:0.6rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--faint); padding-top:0.5rem; border-top:1px solid var(--border-lt); }}
  .premium-fineprint {{ font-size:0.65rem; color:var(--faint); margin-top:0.75rem; line-height:1.5; }}
  @media (max-width:600px) {{ .premium-programs {{ grid-template-columns:1fr; }} }}

  .igclip-banner {{ margin:2.5rem 0 0; padding:0 2rem; }}
  .igclip-banner-inner {{ display:flex; align-items:center; gap:1rem; max-width:900px; margin:0 auto; padding:0.9rem 1.25rem; background:var(--surface); border:1px solid var(--border); border-radius:4px; }}
  .igclip-banner-icon {{ flex-shrink:0; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:0.85rem; background:linear-gradient(135deg,#f58529,#dd2a7b,#8133c4); color:#fff; }}
  .igclip-banner-text {{ flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }}
  .igclip-banner-text strong {{ font-size:0.8rem; color:var(--text); letter-spacing:0.02em; }}
  .igclip-banner-text span {{ font-size:0.7rem; color:var(--muted); line-height:1.4; }}
  .igclip-banner-link {{ flex-shrink:0; font-size:0.72rem; font-weight:600; letter-spacing:0.05em; color:#fff; background:linear-gradient(135deg,#f58529,#dd2a7b,#8133c4); text-decoration:none; padding:0.5rem 1rem; border-radius:3px; transition:opacity 0.2s; }}
  .igclip-banner-link:hover {{ opacity:0.85; }}
  @media (max-width:560px) {{ .igclip-banner-inner {{ flex-wrap:wrap; }} .igclip-banner-link {{ width:100%; text-align:center; }} }}

  footer {{ border-top:1px solid var(--border); padding:2rem 0; margin-top:1rem; }}
  .footer-inner {{ display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem; }}
  .footer-brand {{ font-family:'Inter',sans-serif; font-size:0.8rem; color:var(--muted); }}
  .footer-brand strong {{ color:var(--text); }}
  .footer-links {{ display:flex; gap:1.5rem; }}
  .footer-links a {{ font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); text-decoration:none; transition:color 0.2s; }}
  .footer-links a:hover {{ color:var(--accent); }}

  @keyframes fadeSlideUp {{ from{{opacity:0;transform:translateY(12px);}} to{{opacity:1;transform:translateY(0);}} }}
  .hero {{ animation:fadeSlideUp 0.6s ease both; }}
  .player-bar {{ animation:fadeSlideUp 0.6s 0.15s ease both; }}
  .player-bar .player-track, .player-bar .player-meta {{ position:relative; z-index:1; }}
  /* D5N box com header padrão grid 2col (igual MC/FM) — classes reutilizadas */
  .d5n-program {{ display:grid; grid-template-columns:minmax(230px,.82fr) minmax(0,1.35fr); margin:3rem 0 2.5rem; overflow:hidden; border:1px solid var(--d5n-line); border-radius:14px; background:var(--d5n-deep); box-shadow:inset 0 1px rgba(255,255,255,.025); position:relative; }}
  .d5n-program::before {{ content:""; position:absolute; inset:0; background-image:url("/podcast-cover.png"); background-size:cover; background-position:center; opacity:0.10; pointer-events:none; z-index:0; }}
  .d5n-intro {{ position:relative; padding:2rem; border-right:1px solid var(--d5n-line); background:rgba(17,26,43,0.88); overflow:hidden; backdrop-filter:blur(1px); z-index:1; }}
  .d5n-intro::after {{ content:'05'; position:absolute; right:-.15rem; bottom:-1.3rem; color:transparent; -webkit-text-stroke:1px rgba(148,163,184,.14); font-size:8.5rem; font-weight:700; line-height:1; letter-spacing:-.08em; pointer-events:none; }}
  .d5n-kicker {{ display:flex; align-items:center; gap:.55rem; margin-bottom:1.3rem; color:var(--d5n); font-size:.63rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }}
  .d5n-sun {{ width:10px; height:10px; border-radius:50%; background:var(--d5n); box-shadow:0 0 0 4px rgba(148,163,184,.1); }}
  .d5n-intro h2 {{ position:relative; z-index:1; color:var(--text); font-size:clamp(1.55rem,3.5vw,2.15rem); font-weight:600; line-height:.98; letter-spacing:-.045em; }}
  .d5n-intro h2 strong {{ color:var(--d5n); font-weight:700; }}
  .d5n-intro p {{ position:relative; z-index:1; max-width:26rem; margin-top:1.2rem; color:var(--text-secondary); font-size:.82rem; line-height:1.65; }}
  .d5n-intro .morning-byline {{ gap:.8rem; }}
  .d5n-intro .morning-byline span {{ white-space:nowrap; }}
  .d5n-program .morning-listen--d5n {{ background:rgba(19,25,32,0.55); }}

  .weekend-notice {{ margin:2rem 0 0; padding:0.75rem 1rem; background:var(--surface); border:1px solid var(--border); border-radius:3px; display:flex; align-items:center; gap:0.75rem; opacity:0.7; }}
  .weekend-icon {{ font-size:1.2rem; flex-shrink:0; }}
  .weekend-title {{ font-size:0.75rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--muted); }}
  .weekend-desc {{ font-size:0.7rem; color:var(--faint); }}
  .ticker-wrap {{ animation:fadeSlideUp 0.4s ease both; }}

  .archive-link {{ display:flex; align-items:center; justify-content:space-between; padding:1rem 0; text-decoration:none; border-bottom:1px solid var(--border-lt); transition:padding 0.2s; cursor:pointer; }}
  .archive-link:hover {{ padding-left:0.5rem; background:rgba(148,163,184,0.03); }}
  .archive-link-meta {{ font-size:0.78rem; color:var(--muted); display:flex; align-items:center; gap:0.5rem; }}
  .archive-link-date {{ font-family:'Inter',sans-serif; font-size:0.88rem; color:var(--text); font-style:italic; }}
  .archive-link-play {{ color:var(--accent); font-size:0.85rem; width:2rem; height:2rem; display:flex; align-items:center; justify-content:center; border-radius:50%; background:rgba(148,163,184,0.08); transition:all 0.2s; flex-shrink:0; }}
  .archive-link:hover .archive-link-play {{ background:rgba(148,163,184,0.15); color:#fff; }}
  .archive-link--missing {{ opacity:0.35; cursor:default; }}
  .archive-link--missing .archive-link-date {{ color:var(--muted); }}
  .archive-link--missing .archive-link-meta {{ font-style:italic; color:var(--faint); }}
  .archive-link-archive-ghost {{ color:var(--faint); font-size:0.7rem; }}
  .archive-voice {{ font-size:0.68rem; padding:1px 6px; background:rgba(148,163,184,0.08); border:1px solid rgba(148,163,184,0.15); border-radius:3px; color:var(--accent); letter-spacing:0.03em; }}

  /* Dropdown: 3 visíveis por padrão, resto oculto até clicar */
  .archive-link--hidden {{ display:none; }}
  .archive-archive.expanded .archive-link--hidden {{ display:flex; }}
  .archive-toggle {{
    display:flex; align-items:center; justify-content:center; gap:0.5rem;
    width:100%; margin-top:0.75rem; padding:0.7rem 1rem;
    background:transparent; border:1px solid var(--border);
    border-radius:6px; color:var(--muted); cursor:pointer;
    font-family:inherit; font-size:0.78rem; font-weight:400;
    transition:all 0.2s ease;
  }}
  .archive-toggle:hover {{
    border-color:var(--accent-dim); color:var(--text);
    background:rgba(148,163,184,0.04);
  }}
  .archive-toggle-arrow {{ font-size:0.85rem; transition:transform 0.25s ease; }}
  .archive-archive.expanded .archive-toggle-arrow {{ transform:rotate(180deg); }}

  /* Identidade oficial — BrandBook Drop Five News v1.0 */
  :root {{
    --bg:#0B1020; --surface:#11182b; --surface-raised:#172039;
    --border:#253252; --border-lt:#19243d; --text:#F8FAFC;
    --text-secondary:#d7deea; --muted:#93a1b8; --faint:#52617a;
    --accent:#00D4FF; --accent-2:#7C3AED; --accent-dim:#245c78;
    --brand-gradient:linear-gradient(115deg,var(--accent),var(--accent-2));
  }}
  body {{ background:var(--bg); font-family:'Inter',sans-serif; font-weight:400; }}
  body::before {{ content:''; position:fixed; inset:0; pointer-events:none; opacity:.1; z-index:-1; background-image:radial-gradient(rgba(0,212,255,.3) 1px,transparent 1px); background-size:32px 32px; mask-image:linear-gradient(to bottom,black,transparent 55%); }}
  header {{ background:rgba(11,16,32,.94); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px); height:64px; padding-top:env(safe-area-inset-top); }}
  .logo {{ display:inline-flex; align-items:center; gap:.65rem; font-family:'Inter',sans-serif; font-size:.82rem; letter-spacing:.01em; text-transform:none; }}
  .brand-mark {{ width:34px; height:34px; border-radius:8px; box-shadow:none; }}
  .logo-wordmark {{ color:var(--text); font-weight:600; }} .logo-wordmark strong {{ color:var(--accent); font-weight:700; }}
  .hero {{ position:relative; padding:4.75rem 0 3rem; }}
  .hero::after {{ content:'05'; position:absolute; right:0; top:1.5rem; font-family:'Inter',sans-serif; font-size:8rem; font-weight:700; line-height:1; color:transparent; -webkit-text-stroke:1px rgba(0,212,255,.10); pointer-events:none; }}
  .hero-eyebrow {{ color:var(--accent); font-weight:500; }}
  .hero-title {{ max-width:680px; font-family:'Inter',sans-serif; font-size:clamp(2.5rem,7vw,4.8rem); font-weight:700; letter-spacing:-.045em; }}
  .hero-title em {{ font-style:normal; color:var(--accent); }}
  .hero-lead {{ max-width:610px; margin-top:1rem; color:var(--text-secondary); font-size:clamp(.95rem,2vw,1.08rem); line-height:1.7; }}
  .player-bar {{ padding:1.15rem 1.25rem; border-radius:10px; border-color:var(--border); background:var(--surface); box-shadow:none; }}
  .play-btn {{ width:42px; height:42px; border:0; color:#0B1020; background:var(--brand-gradient); box-shadow:none; }}
  .play-btn:hover {{ transform:translateY(-1px); background:var(--brand-gradient); color:#071019; filter:brightness(1.08); }}
  .player-meta {{ margin-top:.65rem; }}
  .search-bar,.filter-btn,.section-context,.premium-block,.voice-section {{ border-radius:10px; }}
  .news-item:hover {{ border-radius:10px; }}
  .archive-toggle {{ border-radius:10px; }}
  .skip-link {{ position:fixed; left:1rem; top:-5rem; z-index:1000; padding:.75rem 1rem; border-radius:8px; background:var(--accent); color:#071019; font-weight:600; text-decoration:none; }}
  .skip-link:focus {{ top:1rem; }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:3px; }}
  @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation-duration:.01ms!important; animation-iteration-count:1!important; scroll-behavior:auto!important; transition-duration:.01ms!important; }} }}

  /* ── Manhã Conectada ── */
  :root {{ --morning:#f4b942; --morning-deep:#241d12; --morning-line:#5b4925; --fechamento:#0ea5e9; --fechamento-deep:#0a1a2a; --fechamento-line:#164a6a; --d5n:#94a3b8; --d5n-deep:#111a2b; --d5n-line:#2a3a52; }}
  .header-program-link {{ color:var(--text-secondary); font-size:.68rem; font-weight:600; letter-spacing:.04em; text-decoration:none; transition:color .2s ease; }}
  .header-program-link:hover {{ color:var(--morning); }}
  .morning-program {{ display:grid; grid-template-columns:minmax(230px,.82fr) minmax(0,1.35fr); margin:3rem 0 2.5rem; overflow:hidden; border:1px solid var(--border); border-radius:14px; background:var(--surface); box-shadow:inset 0 1px rgba(255,255,255,.025); }}
  .morning-intro {{ position:relative; padding:2rem; border-right:1px solid var(--border); background:rgba(16,23,39,0.72); overflow:hidden; backdrop-filter:blur(1px); }}
  .morning-intro::after {{ content:'11'; position:absolute; right:-.15rem; bottom:-1.3rem; color:transparent; -webkit-text-stroke:1px rgba(244,185,66,.14); font-size:8.5rem; font-weight:700; line-height:1; letter-spacing:-.08em; pointer-events:none; }}
  .morning-kicker {{ display:flex; align-items:center; gap:.55rem; margin-bottom:1.3rem; color:var(--morning); font-size:.63rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }}
  .morning-sun {{ width:10px; height:10px; border-radius:50%; background:var(--morning); box-shadow:0 0 0 4px rgba(244,185,66,.1); }}
  .morning-intro h2 {{ position:relative; z-index:1; color:var(--text); font-size:clamp(1.8rem,4vw,2.55rem); font-weight:600; line-height:.98; letter-spacing:-.045em; }}
  .morning-intro h2 strong {{ color:var(--morning); font-weight:700; }}
  .morning-intro p {{ position:relative; z-index:1; max-width:26rem; margin-top:1.2rem; color:var(--text-secondary); font-size:.82rem; line-height:1.65; }}
  .morning-byline {{ position:relative; z-index:1; display:flex; gap:1rem; margin-top:1.4rem; color:var(--muted); font-size:.62rem; letter-spacing:.08em; text-transform:uppercase; }}
  .morning-byline span + span {{ padding-left:1rem; border-left:1px solid var(--border); }}
  .morning-listen {{ display:flex; min-width:0; flex-direction:column; justify-content:center; padding:2rem; background:rgba(19,25,32,0.55); backdrop-filter:blur(1px); }}
  .morning-now {{ display:flex; align-items:center; gap:.6rem; color:var(--morning); font-size:.63rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; }}
  .morning-now span:last-child {{ margin-left:auto; color:var(--muted); font-weight:500; }}
  .morning-live-dot {{ width:6px; height:6px; border-radius:50%; background:var(--morning); box-shadow:0 0 0 4px rgba(244,185,66,.08); }}
  .morning-summary {{ min-height:3.7rem; margin:1rem 0 1.35rem; color:var(--text); font-size:.92rem; font-weight:500; line-height:1.55; }}
  .morning-player {{ display:flex; align-items:center; gap:.8rem; padding:.8rem; border:1px solid var(--morning-line); border-radius:10px; background:var(--morning-deep); }}
  .morning-play {{ display:grid; width:38px; height:38px; flex:0 0 38px; place-items:center; border:0; border-radius:50%; background:var(--morning); color:#151006; cursor:pointer; font-size:.72rem; transition:transform .18s ease,filter .18s ease; }}
  .morning-play:hover {{ transform:translateY(-1px); filter:brightness(1.08); }}
  .morning-progress {{ position:relative; height:7px; min-width:90px; flex:1; overflow:hidden; border-radius:999px; background:#493b21; cursor:pointer; }}
  .morning-progress span {{ display:block; width:0; height:100%; border-radius:inherit; background:var(--morning); transition:width .1s linear; }}
  .morning-time {{ color:#c8b98f; font-family:'DM Mono',monospace; font-size:.58rem; white-space:nowrap; }}
  .morning-download {{ display:grid; width:28px; height:28px; place-items:center; color:var(--morning); border:1px solid var(--morning-line); border-radius:7px; text-decoration:none; }}
  .morning-history {{ display:flex; align-items:stretch; gap:.45rem; margin-top:1rem; overflow-x:auto; scrollbar-width:thin; }}
  .morning-history-label {{ display:flex; align-items:center; padding-right:.45rem; color:var(--muted); font-size:.58rem; font-weight:600; letter-spacing:.12em; text-transform:uppercase; }}
  .morning-episode {{ display:flex; min-width:max-content; align-items:center; gap:.55rem; padding:.45rem .65rem; border:1px solid var(--border); border-radius:7px; background:transparent; color:var(--muted); cursor:pointer; font:inherit; font-size:.64rem; transition:border-color .2s ease,color .2s ease,background .2s ease; }}
  .morning-episode small {{ color:var(--faint); font-size:.56rem; }}
  .morning-episode:hover,.morning-episode.is-active {{ border-color:var(--morning-line); background:rgba(244,185,66,.06); color:var(--morning); }}
  .morning-program.visible {{ animation:fadeSlideUp .5s ease both; }}
  .morning-program {{ position:relative; }}
  .morning-program::before {{ content:""; position:absolute; inset:0; background-size:cover; background-position:center; opacity:0.14; pointer-events:none; z-index:0; }}
  .morning-program#manha-conectada::before {{ background-image:url("/manha-conectada/assets/manha-conectada-cover.png"); }}
  .morning-program#fechamento::before {{ background-image:url("/fechamento/assets/fechamento-cover.png"); }}
  .morning-program .morning-intro, .morning-program .morning-listen {{ position:relative; z-index:1; }}
  /* Fechamento — identidade própria noite petróleo, distinta de Manhã âmbar */
  .fechamento-program {{ border-color:var(--fechamento-line) !important; background:var(--fechamento-deep) !important; }}
  .fechamento-program::before {{ opacity:0.12 !important; }}
  .fechamento-intro {{ background:rgba(10,26,43,0.90) !important; border-right-color:var(--fechamento-line) !important; }}
  .fechamento-intro::after {{ content:'17' !important; -webkit-text-stroke:1px rgba(14,165,233,.18) !important; }}
  .fechamento-kicker {{ color:var(--fechamento) !important; }}
  .fechamento-sun, .fechamento-dot {{ background:var(--fechamento) !important; box-shadow:0 0 0 4px rgba(14,165,233,.12) !important; }}
  .fechamento-program h2 strong {{ color:var(--fechamento) !important; }}
  .fechamento-program .morning-player {{ background:rgba(14,165,233,0.08) !important; border-color:var(--fechamento-line) !important; }}
  .fechamento-program .morning-progress {{ background:#0f2a3d !important; }}
  .fechamento-program .morning-progress span {{ background:var(--fechamento) !important; }}
  .fechamento-program .morning-time {{ color:#7dd3fc !important; }}
  .fechamento-program .morning-download {{ border-color:var(--fechamento-line) !important; color:var(--fechamento) !important; }}
  .fechamento-program .morning-play {{ background:var(--fechamento) !important; color:#052030 !important; }}
  .fechamento-episode.is-active {{ border-color:var(--fechamento-line) !important; background:rgba(14,165,233,.10) !important; color:var(--fechamento) !important; }}
  .fechamento-episode:hover {{ border-color:var(--fechamento-line) !important; }}
  /* Manhã fica com cover 0.10 quente, D5N 0.06 sutil já */
  .morning-program#manha-conectada::before {{ opacity:0.10; }}

  @media (max-width:700px) {{
    .morning-program, .d5n-program {{ grid-template-columns:1fr; margin:2rem 0; }}
    .morning-intro {{ padding:1.5rem; border-right:0; border-bottom:1px solid var(--border); }}
    .morning-intro::after {{ font-size:7rem; }}
    .morning-listen {{ padding:1.5rem; }}
  }}
  @media (max-width:600px) {{
    .header-program-link {{ display:none; }}
    .morning-player {{ flex-wrap:wrap; }}
    .morning-progress {{ order:5; flex-basis:100%; height:9px; }}
    .morning-summary {{ min-height:0; }}
  }}
  @media (max-width:600px) {{
    .hero {{ padding:3rem 0 2rem; }} .hero::after {{ font-size:5rem; top:1rem; }}
    .hero-sub {{ gap:.8rem; flex-wrap:wrap; }} .divider-v {{ display:none; }}
    .player-bar {{ padding:1rem; }} .player-track {{ flex-wrap:wrap; }}
    .player-progress {{ order:5; flex-basis:100%; margin-top:.4rem; height:12px; }}
    .player-meta {{ align-items:flex-start; flex-direction:column; gap:.2rem; }}
    .chapter-current {{ text-align:left; }}
    .player-title {{ font-size:.72rem; }} .edition-badge {{ display:none; }}
  }}

  @media (max-width:600px) {{
    header {{ padding-left:1rem; padding-right:1rem; }} .container {{ padding-left:1rem; padding-right:1rem; }}
    .header-meta {{ display:none; }} .hero {{ padding:2rem 0 1.5rem; }}
    .news-item {{ grid-template-columns:2rem 1fr; }} .news-source {{ display:none; }}
    .footer-inner {{ flex-direction:column; align-items:flex-start; }}
  }}
</style>
<script defer src="https://cloud.umami.is/script.js" data-website-id="e0919f78-6147-42e0-a382-d3792662ea3a"></script>
</head>
<body>
<a class="skip-link" href="#conteudo">Ir para o conteúdo</a>

<header>
  <a class="logo" href="/" aria-label="Drop Five News — página inicial">
    <img class="brand-mark" src="/favicon.svg" alt="" width="30" height="30">
    <span class="logo-wordmark">Drop <strong>Five</strong> News</span>
  </a>
  <span class="header-meta">{data_br}</span>
  <div class="header-right">
    {morning_nav}{fechamento_nav}
    <span class="edition-badge">#{podcast["num"] if podcast else "---"}</span>
    <div class="tech-bar">
      <span class="tech-item">IBOV <span class="tech-value">—</span></span>
      <span class="tech-item">USD <span class="tech-value">—</span></span>
      <span class="tech-item">BTC <span class="tech-value">—</span></span>
      <span class="tech-item">PETR4 <span class="tech-value">—</span></span>
    </div>
  </div>
</header>

<div class="ticker-wrap">
  <span class="ticker-label">hoje</span>
  <div class="ticker-track" id="ticker">
    {ticker_items}
    {ticker_dup}
  </div>
</div>

<main id="conteudo" class="container">

  <div class="hero">
    <p class="hero-eyebrow">Podcast diário · Curadoria editorial</p>
    <h1 class="hero-title">As notícias<br>que <em>importam</em> hoje.</h1>
    <p class="hero-lead">Brasil, mundo e tecnologia com contexto, clareza e uma edição em áudio para você começar o dia bem informado.</p>
    <div class="hero-sub">
      <div class="hero-stat"><strong>{n}</strong><span>notícias</span></div>
      <div class="divider-v"></div>
      <div class="hero-stat"><strong>{n_pilares}</strong><span>pilares</span></div>
      <div class="divider-v"></div>
      <div class="hero-stat"><strong>{pod_dur}</strong><span>podcast</span></div>{qs_stat}
    </div>
  </div>

  {player_html}

{morning_html}
{premium_block}

  <div class="search-bar">
    <input type="search" id="searchInput" placeholder="Buscar notícias..." aria-label="Buscar notícias">
  </div>

  <div class="filter-buttons">
    <button class="filter-btn active" data-filter="all">Todas</button>
    <button class="filter-btn" data-filter="global">🌍 Global</button>
    <button class="filter-btn" data-filter="tech">🤖 Tech</button>
    <button class="filter-btn" data-filter="econ">💰 Economia</button>
    <button class="filter-btn" data-filter="brasil">🇧🇷 Brasil</button>
  </div>

  {sections_html}

  <section class="section" style="border-bottom:none;padding-bottom:0">
    <div class="section-header">
      <span class="section-icon">📅</span>
      <span class="section-name" style="color:var(--muted)">Episódios</span>
    </div>
    {archive_html if archive_html else '<p style="font-size:0.82rem;color:var(--muted);padding:1rem 0">Nenhum episódio anterior.</p>'}
  </section>

  <!-- Banner discreto IG Clip -->
  <div class="igclip-banner" data-animate>
    <div class="igclip-banner-inner">
      <div class="igclip-banner-icon">⬇</div>
      <div class="igclip-banner-text">
        <strong>IG Clip</strong>
        <span>Baixe reels, fotos e vídeos do Instagram em qualidade original — sem anúncios, sem limites.</span>
      </div>
      <a class="igclip-banner-link" href="https://igclip.netlify.app" target="_blank" rel="noopener">Experimentar →</a>
    </div>
  </div>

</main>

<footer>
  <div class="container">
    <div class="footer-inner">
      <div class="footer-brand">
        <strong>Drop Five News</strong> · Curadoria por <a href="https://www.instagram.com/jeanbraga.ai" style="color:var(--accent);text-decoration:none">@jeanbraga.ai</a><br>
        <span style="font-size:0.65rem">Atualizado em {data_br.lower()}</span>
      </div>
      <div class="footer-links">
        <a href="/privacidade">Privacidade</a>
        <a href="/feed.json">JSON Feed</a>
        <a href="/d5n-feed.xml">RSS</a>
        <a href="/manha-conectada.xml">RSS Manhã Conectada</a>
        <a href="/fechamento.xml">RSS Fechamento</a>
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

  // ── Player segmentado com capítulos reais ──
  const audio = document.getElementById('audioEl');
  const playIcon = document.getElementById('playIcon');
  const pauseIcon = document.getElementById('pauseIcon');
  const timeEl = document.getElementById('playerTime');
  const currentChapterEl = document.getElementById('currentChapter');
  const chaptersContainer = document.getElementById('chaptersContainer');
  const bar = document.getElementById('progressBar');
  const morningAudio = document.getElementById('morningAudio');
  const morningPlayGlyph = document.getElementById('morningPlayGlyph');
  const morningPlayBtn = document.getElementById('morningPlayBtn');
  const morningProgress = document.getElementById('morningProgress');
  const morningProgressFill = document.getElementById('morningProgressFill');
  const morningTime = document.getElementById('morningTime');

  let chapters = [];
  let currentChapterIdx = -1;
  try {{ if (chaptersContainer) chapters = JSON.parse(chaptersContainer.dataset.chapters || '[]'); }} catch(e) {{}}

  function makeChapterSegment(chapter, index) {{
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'chapter-segment';
    button.dataset.chapterIndex = String(index);
    button.dataset.chapterStart = String(chapter.start || 0);
    const duration = Math.max(.001, Number(chapter.duration) || (Number(chapter.end) - Number(chapter.start)) || 1);
    button.style.setProperty('--chapter-weight', duration.toFixed(3));
    button.setAttribute('aria-label', `Ir para o capítulo ${{chapter.label}}, em ${{fmt(chapter.start)}}`);

    const track = document.createElement('span');
    track.className = 'chapter-segment-track';
    const chapterFill = document.createElement('span');
    chapterFill.className = 'chapter-segment-fill';
    track.appendChild(chapterFill);

    const tooltip = document.createElement('span');
    tooltip.className = 'chapter-tooltip';
    tooltip.textContent = chapter.label;
    const time = document.createElement('small');
    time.textContent = fmt(chapter.start);
    tooltip.appendChild(time);
    button.append(track, tooltip);
    return button;
  }}

  function bindChapterSegments() {{
    if (!chaptersContainer) return;
    chaptersContainer.querySelectorAll('.chapter-segment').forEach((segment, index) => {{
      segment.addEventListener('click', event => {{
        event.stopPropagation();
        if (!audio) return;
        audio.currentTime = Number(chapters[index]?.start || 0);
        updateChapterProgress();
      }});
    }});
  }}

  function renderChapters(nextChapters) {{
    chapters = Array.isArray(nextChapters) ? nextChapters : [];
    currentChapterIdx = -1;
    if (!chaptersContainer) return;
    chaptersContainer.replaceChildren(...chapters.map(makeChapterSegment));
    chaptersContainer.dataset.chapters = JSON.stringify(chapters);
    bindChapterSegments();
    updateChapterProgress();
  }}

  function updateChapterProgress() {{
    if (!audio || !chapters.length) return;
    const current = Number(audio.currentTime || 0);
    let activeIdx = 0;
    chapters.forEach((chapter, index) => {{
      const start = Number(chapter.start || 0);
      const end = Number(chapter.end || audio.duration || start + 1);
      const progress = current <= start ? 0 : current >= end ? 100 : ((current - start) / Math.max(.001, end - start)) * 100;
      const segment = chaptersContainer?.querySelector(`[data-chapter-index="${{index}}"]`);
      const segmentFill = segment?.querySelector('.chapter-segment-fill');
      if (segmentFill) segmentFill.style.width = `${{Math.max(0, Math.min(100, progress))}}%`;
      if (current >= start) activeIdx = index;
      segment?.classList.toggle('is-active', index === activeIdx);
    }});
    chaptersContainer?.querySelectorAll('.chapter-segment').forEach((segment, index) => {{
      segment.classList.toggle('is-active', index === activeIdx);
    }});
    if (currentChapterEl && activeIdx !== currentChapterIdx) {{
      currentChapterIdx = activeIdx;
      currentChapterEl.textContent = chapters.length === 1
        ? chapters[0].label
        : `Capítulo ${{activeIdx + 1}} de ${{chapters.length}} · ${{chapters[activeIdx].label}}`;
    }}
    if (bar) bar.setAttribute('aria-valuenow', String(Math.floor(current)));
  }}

  bindChapterSegments();
  updateChapterProgress();

  function togglePlay() {{
    if (!audio) return;
    if (audio.paused) {{
      if (morningAudio && !morningAudio.paused) morningAudio.pause();
      audio.play();
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    }} else {{
      audio.pause();
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
    }}
  }}
  const speeds=[0.75,1,1.25,1.5,2]; let speedIdx=1;
  function cycleSpeed() {{
    if (!audio) return;
    speedIdx=(speedIdx+1)%speeds.length;
    audio.playbackRate=speeds[speedIdx];
    document.getElementById('speedBtn').textContent=speeds[speedIdx]+'×';
  }}

  if (audio) {{
    audio.addEventListener('timeupdate', () => {{
      if (!audio.duration) return;
      timeEl.textContent = fmt(audio.currentTime) + ' / ' + fmt(audio.duration);
      updateChapterProgress();
    }});
    audio.addEventListener('loadedmetadata', () => {{
      if (bar) bar.setAttribute('aria-valuemax', String(Math.floor(audio.duration || 0)));
      timeEl.textContent = fmt(audio.currentTime) + ' / ' + fmt(audio.duration);
      updateChapterProgress();
    }});
    audio.addEventListener('ended', () => {{
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
      updateChapterProgress();
    }});
  }}

  // ── Player independente da Manhã Conectada ──
  function updateMorningPlayer() {{
    if (!morningAudio) return;
    const current = Number(morningAudio.currentTime || 0);
    const fallbackDuration = Number(morningProgress?.getAttribute('aria-valuemax') || 0);
    const duration = Number(morningAudio.duration || fallbackDuration);
    const pct = duration ? Math.min(100, Math.max(0, current / duration * 100)) : 0;
    if (morningProgressFill) morningProgressFill.style.width = `${{pct}}%`;
    if (morningTime) morningTime.textContent = `${{fmt(current)}} / ${{fmt(duration)}}`;
    if (morningProgress) {{
      morningProgress.setAttribute('aria-valuenow', String(Math.floor(current)));
      if (duration) morningProgress.setAttribute('aria-valuemax', String(Math.floor(duration)));
    }}
  }}

  function setMorningPlayState(playing) {{
    if (morningPlayGlyph) morningPlayGlyph.textContent = playing ? 'Ⅱ' : '▶';
    if (morningPlayBtn) morningPlayBtn.setAttribute('aria-label', playing ? 'Pausar Manhã Conectada' : 'Reproduzir Manhã Conectada');
  }}

  function toggleMorningPlay() {{
    if (!morningAudio) return;
    if (morningAudio.paused) {{
      if (audio && !audio.paused) audio.pause();
      morningAudio.play().then(() => setMorningPlayState(true)).catch(error => console.warn('Play failed:', error));
    }} else {{
      morningAudio.pause();
    }}
  }}

  function selectMorningEpisode(button) {{
    if (!morningAudio || !button?.dataset.audio) return;
    morningAudio.pause();
    morningAudio.src = button.dataset.audio;
    morningAudio.load();
    document.querySelectorAll('.morning-episode').forEach(item => item.classList.toggle('is-active', item === button));
    const date = document.getElementById('morningDate');
    const summary = document.getElementById('morningSummary');
    const download = document.getElementById('morningDownload');
    if (date) date.textContent = button.dataset.date || '';
    if (summary) summary.textContent = button.dataset.summary || '';
    if (download) download.href = button.dataset.audio;
    if (morningProgress) morningProgress.setAttribute('aria-valuemax', button.dataset.duration || '0');
    updateMorningPlayer();
    morningAudio.play().then(() => setMorningPlayState(true)).catch(error => console.warn('Play failed:', error));
  }}

  // ── Fechamento do Mercado player (espelho MC) ──
  const fechamentoAudio = document.getElementById('fechamentoAudio');
  const fechamentoProgress = document.getElementById('fechamentoProgress');
  const fechamentoProgressFill = document.getElementById('fechamentoProgressFill');
  const fechamentoTime = document.getElementById('fechamentoTime');
  const fechamentoPlayBtn = document.getElementById('fechamentoPlayBtn');
  const fechamentoPlayGlyph = document.getElementById('fechamentoPlayGlyph');
  function updateFechamentoPlayer() {{
    if (!fechamentoAudio) return;
    const cur = fechamentoAudio.currentTime || 0;
    const dur = fechamentoAudio.duration || parseInt(fechamentoProgress?.dataset.duration || fechamentoProgress?.getAttribute('aria-valuemax') || '0', 10) || 0;
    if (fechamentoProgressFill) fechamentoProgressFill.style.width = dur ? (cur/dur*100)+'%' : '0';
    if (fechamentoTime) fechamentoTime.textContent = fmt(cur) + ' / ' + fmt(dur);
    if (fechamentoProgress) fechamentoProgress.setAttribute('aria-valuenow', String(Math.floor(cur)));
    if (dur) fechamentoProgress.setAttribute('aria-valuemax', String(Math.floor(dur)));
  }}
  function setFechamentoPlayState(playing) {{
    if (fechamentoPlayGlyph) fechamentoPlayGlyph.textContent = playing ? 'Ⅱ' : '▶';
    if (fechamentoPlayBtn) fechamentoPlayBtn.setAttribute('aria-label', playing ? 'Pausar Fechamento' : 'Reproduzir Fechamento');
  }}
  function toggleFechamentoPlay() {{
    if (!fechamentoAudio) return;
    if (fechamentoAudio.paused) {{
      if (typeof audio !== 'undefined' && audio && !audio.paused) audio.pause();
      if (morningAudio && !morningAudio.paused) morningAudio.pause();
      fechamentoAudio.play().then(() => setFechamentoPlayState(true)).catch(e => console.warn('Play failed:', e));
    }} else {{
      fechamentoAudio.pause();
    }}
  }}
  function selectFechamentoEpisode(button) {{
    if (!fechamentoAudio || !button?.dataset.audio) return;
    fechamentoAudio.pause();
    fechamentoAudio.src = button.dataset.audio;
    fechamentoAudio.load();
    document.querySelectorAll('.fechamento-episode').forEach(item => item.classList.toggle('is-active', item === button));
    const date = document.getElementById('fechamentoDate');
    const summary = document.getElementById('fechamentoSummary');
    const download = document.getElementById('fechamentoDownload');
    if (date) date.textContent = button.dataset.date || '';
    if (summary) summary.textContent = button.dataset.summary || '';
    if (download) download.href = button.dataset.audio;
    if (fechamentoProgress) fechamentoProgress.setAttribute('aria-valuemax', button.dataset.duration || '0');
    updateFechamentoPlayer();
    fechamentoAudio.play().then(() => setFechamentoPlayState(true)).catch(e => console.warn('Play failed:', e));
  }}
  if (fechamentoAudio) {{
    fechamentoAudio.addEventListener('timeupdate', updateFechamentoPlayer);
    fechamentoAudio.addEventListener('loadedmetadata', updateFechamentoPlayer);
    fechamentoAudio.addEventListener('play', () => setFechamentoPlayState(true));
    fechamentoAudio.addEventListener('pause', () => setFechamentoPlayState(false));
    fechamentoAudio.addEventListener('ended', () => {{ setFechamentoPlayState(false); updateFechamentoPlayer(); }});
  }}
  if (fechamentoProgress) {{
    fechamentoProgress.addEventListener('click', event => {{
      if (!fechamentoAudio?.duration) return;
      const rect = fechamentoProgress.getBoundingClientRect();
      fechamentoAudio.currentTime = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * fechamentoAudio.duration;
    }});
    fechamentoProgress.addEventListener('keydown', event => {{
      if (!fechamentoAudio?.duration || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'Home') fechamentoAudio.currentTime = 0;
      else if (event.key === 'End') fechamentoAudio.currentTime = fechamentoAudio.duration;
      else fechamentoAudio.currentTime = Math.max(0, Math.min(fechamentoAudio.duration, fechamentoAudio.currentTime + (event.key === 'ArrowRight' ? 5 : -5)));
    }});
  }}

  if (morningAudio) {{
    morningAudio.addEventListener('timeupdate', updateMorningPlayer);
    morningAudio.addEventListener('loadedmetadata', updateMorningPlayer);
    morningAudio.addEventListener('play', () => setMorningPlayState(true));
    morningAudio.addEventListener('pause', () => setMorningPlayState(false));
    morningAudio.addEventListener('ended', () => {{ setMorningPlayState(false); updateMorningPlayer(); }});
  }}
  if (morningProgress) {{
    morningProgress.addEventListener('click', event => {{
      if (!morningAudio?.duration) return;
      const rect = morningProgress.getBoundingClientRect();
      morningAudio.currentTime = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * morningAudio.duration;
    }});
    morningProgress.addEventListener('keydown', event => {{
      if (!morningAudio?.duration || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'Home') morningAudio.currentTime = 0;
      else if (event.key === 'End') morningAudio.currentTime = morningAudio.duration;
      else morningAudio.currentTime = Math.max(0, Math.min(morningAudio.duration, morningAudio.currentTime + (event.key === 'ArrowRight' ? 5 : -5)));
    }});
  }}

  function seekAudio(e) {{
    if (!audio?.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audio.currentTime = pct * audio.duration;
    updateChapterProgress();
  }}
  if (bar) bar.addEventListener('keydown', event => {{
    if (!audio?.duration || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    if (event.key === 'Home') audio.currentTime = 0;
    else if (event.key === 'End') audio.currentTime = audio.duration;
    else audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + (event.key === 'ArrowRight' ? 5 : -5)));
    updateChapterProgress();
  }});
  function fmt(s) {{ const safe=Number.isFinite(Number(s))?Number(s):0; const m=Math.floor(safe/60); const sec=Math.floor(safe%60).toString().padStart(2,'0'); return m+':'+sec; }}
  
  // Copiar link do audio
  function copyAudioLink() {{
    const src = audio ? audio.src : '';
    if (!src) return;
    const btn = event.currentTarget;
    navigator.clipboard.writeText(src).then(() => {{
      btn.classList.add('copied');
      btn.textContent = '\u2713';
      setTimeout(() => {{ btn.classList.remove('copied'); btn.innerHTML = '🔗'; }}, 2000);
    }}).catch(() => {{
      // fallback
      const ta = document.createElement('textarea');
      ta.value = src; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      btn.classList.add('copied');
      btn.textContent = '\u2713';
      setTimeout(() => {{ btn.classList.remove('copied'); btn.innerHTML = '🔗'; }}, 2000);
    }});
  }}

  // Archive dropdown toggle (episódios anteriores)
  const archiveEl = document.querySelector('.archive-archive');
  const toggleBtn = document.querySelector('.archive-toggle');
  const hiddenCount = {archive_count - 3};
  if (archiveEl && toggleBtn) {{
    toggleBtn.addEventListener('click', () => {{
      const expanded = archiveEl.classList.toggle('expanded');
      toggleBtn.setAttribute('aria-expanded', expanded);
      const label = toggleBtn.querySelector('.archive-toggle-label');
      if (label) label.textContent = expanded ? 'Ver menos' : `Ver episódios anteriores (${{hiddenCount}})`;
    }});
  }}

  // Reproduz episódio do arquivo mantendo capítulos corretos
  function playArchive(el) {{
    const src = el.dataset.audio;
    if (!src || !audio) return;
    if (!audio.paused) audio.pause();

    let nextChapters = [];
    try {{ nextChapters = JSON.parse(el.dataset.chapters || '[]'); }} catch(e) {{}}
    renderChapters(nextChapters);
    audio.src = src;
    audio.load();

    const titleEl = document.querySelector('.player-title');
    if (titleEl) titleEl.textContent = `Hoje no Drop Five News — Episódio #${{el.dataset.episode}} — ${{el.dataset.date}}`;
    const download = document.querySelector('.player-download');
    if (download) download.href = src;
    document.querySelectorAll('.archive-link').forEach(link => link.classList.toggle('is-playing', link === el));

    audio.play().then(() => {{
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    }}).catch(e => console.warn('Play failed:', e));
  }}

  // Busca e filtro
  const searchInput = document.getElementById('searchInput');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const newsItems = document.querySelectorAll('.news-item');
  const sections = document.querySelectorAll('.section');

  let currentFilter = 'all';
  let currentSearch = '';

  function updateVisibility() {{
    sections.forEach(section => {{
      const pilar = section.dataset.pilar;
      const matchesFilter = currentFilter === 'all' || pilar === currentFilter;
      
      const items = section.querySelectorAll('.news-item');
      let visibleCount = 0;
      
      items.forEach(item => {{
        const text = item.querySelector('.news-headline').textContent.toLowerCase();
        const matchesSearch = text.includes(currentSearch);
        const visible = matchesFilter && matchesSearch;
        item.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
      }});
      
      section.style.display = visibleCount > 0 ? '' : 'none';
    }});
  }}

  searchInput.addEventListener('input', (e) => {{
    currentSearch = e.target.value.toLowerCase();
    updateVisibility();
  }});

  filterBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      updateVisibility();
    }});
  }});

  // Buscar dados de mercado em tempo real
  async function fetchMarketData() {{
    try {{
      // Buscar IBOV, USD, BTC, PETR4 via APIs públicas
      const [ibovRes, usdRes, btcRes, petr4Res] = await Promise.all([
        fetch('https://api.exchangerate-api.com/v4/latest/USD').catch(() => null),
        fetch('https://api.exchangerate-api.com/v4/latest/USD').catch(() => null),
        fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd').catch(() => null),
        fetch('https://brapi.dev/api/quote/PETR4').catch(() => null)
      ]);

      // USD para BRL
      if (usdRes && usdRes.ok) {{
        const usdData = await usdRes.json();
        const usdBrl = usdData.rates?.BRL;
        if (usdBrl) {{
          const usdEl = document.querySelector('.tech-item:nth-child(2) .tech-value');
          if (usdEl) usdEl.textContent = `R$ ${{usdBrl.toFixed(2)}}`;
        }}
      }}

      // BTC
      if (btcRes && btcRes.ok) {{
        const btcData = await btcRes.json();
        const btcUsd = btcData.bitcoin?.usd;
        if (btcUsd) {{
          const btcEl = document.querySelector('.tech-item:nth-child(3) .tech-value');
          if (btcEl) btcEl.textContent = `$${{(btcUsd/1000).toFixed(1)}}k`;
        }}
      }}

      // PETR4 (se API estiver disponível)
      if (petr4Res && petr4Res.ok) {{
        const petr4Data = await petr4Res.json();
        const petr4Price = petr4Data.results?.[0]?.regularMarketPrice;
        if (petr4Price) {{
          const petr4El = document.querySelector('.tech-item:nth-child(4) .tech-value');
          if (petr4El) petr4El.textContent = `R$ ${{petr4Price.toFixed(2)}}`;
        }}
      }}

      // IBOV (placeholder - API requer autenticação)
      const ibovEl = document.querySelector('.tech-item:nth-child(1) .tech-value');
      if (ibovEl) ibovEl.textContent = '—';

    }} catch (e) {{
      console.log('Erro ao buscar dados de mercado:', e);
    }}
  }}

  // Buscar dados ao carregar a página
  fetchMarketData();

  // Atualizar a cada 5 minutos
  setInterval(fetchMarketData, 300000);
</script>
</body>
</html>'''
    return html

def gerar_source_md(date, data_br, noticias, voice=None):
    if not noticias: return None

    # Determinar personalidade do dia
    if not voice:
        voice = get_voice_of_day(date) or {
            "name": "Drop Five News",
            "tone": "formal",
            "tagline": "Boletim Drop Five News",
        }
    name = voice.get("name", "Thalita")
    tone = voice.get("tone", "formal")
    tagline = voice.get("tagline", "Boletim Drop Five News")

    # Personas com tom, vocabulario e estilo proprios
    personas = {
        "formal": {
            "intro": f"Bom dia. {tagline}. Sejam bem-vindos ao boletim desta {data_br}. "
                     f"Vamos aos principais acontecimentos do dia, organizados em quatro blocos.",
            "transitions": {
                "Global": "Comecamos pelos acontecimentos de repercussao global.",
                "Brasil": "Voltamos o olhar agora para o Brasil.",
                "Tech": "No bloco de tecnologia e inteligencia artificial.",
                "Economia": "Para fechar, as noticias de economia e criptomoedas.",
                "": "Agora as demais noticias.",
            },
            "outro": f"E assim encerramos o boletim de hoje. Eu sou Thalita, e este foi o Drop Five News. "
                     f"Ate amanha.",
            "instruction_extra": "- Tom: formal, claro, jornalistico. Frases completas, vocabulario preciso.\n"
                                 "- Voce e a Thalita: apresentadora de boletim. NUNCA diga o nome do produtor ou criador.\n"
                                 "- NUNCA diga 'eu sou Jean' ou mencione o nome Jean, Jean Braga, ou qualquer pessoa real.\n"
        },
        "casual": {
            "intro": f"E ai galera, {tagline}. Bem-vindos ao D5N de {data_br}. "
                     f"Bora pro resumo do dia, direto ao ponto, como sempre.",
            "transitions": {
                "Global": "Primeiro, o que ta bombando no mundo.",
                "Brasil": "Agora, o que ta rolando aqui no Brasil.",
                "Tech": "Bora falar de tech e IA, que ta uma loucura.",
                "Economia": "Pra fechar, mercado e crypto. Presta atencao nessa.",
                "": "Mais noticias pra voces agora.",
            },
            "outro": f"E isso e o D5N de hoje. Eu sou a Francisca, ate o proximo boletim. "
                     f"Voces sao demais, valeu.",
            "instruction_extra": "- Tom: casual, envolvente, direto. Use gírias naturais brasileiras sem exagerar.\n"
                                 "- Voce e a Francisca: comunicadora popular. NUNCA diga o nome do produtor ou criador.\n"
                                 "- NUNCA diga 'eu sou Jean' ou mencione o nome Jean, Jean Braga, ou qualquer pessoa real.\n"
        },
        "dual": {
            "intro": f"Hoje e especial! {tagline}. Vamos alternar os blocos entre nos duas "
                     f"para trazer o melhor de cada estilo. Boletim D5N, {data_br}.",
            "transitions": {
                "Global": "Thalita inicia: os principais fatos do mundo.",
                "Brasil": "Francisca assume: e no Brasil a coisa ta quente.",
                "Tech": "Thalita de volta: tecnologia e inteligencia artificial.",
                "Economia": "Francisca fecha: economia e criptomoedas.",
                "": "Continuando o boletim.",
            },
            "outro": f"E assim fechamos mais uma edicao. Thalita e Francisca, Drop Five News. "
                     f"Bom dia, ate amanha.",
            "instruction_extra": "- Tom: dual. Thalita e formal e precisa; Francisca e casual e envolvente.\n"
                                 "- Alternar a voz entre as duas em blocos pares/impares.\n"
                                 "- NUNCA diga o nome do produtor ou criador. NUNCA mencione Jean, Jean Braga ou qualquer pessoa real.\n"
        },
    }

    persona = personas.get(tone, personas["formal"])

    pilares_labels = {'Global':'GLOBAL','Brasil':'BRASIL','Tech':'TECH & IA','Economia':'ECONOMIA & CRYPTO','':'GERAL'}

    md = f"# DROP FIVE NEWS - Boletim Diario\n## {data_br}\n\n"
    md += f"INSTRUCOES PARA APRESENTACAO (LEIA ANTES DE GRAVAR):\n"
    md += f"- Idioma: portugues brasileiro (NAO use portugues de Portugal).\n"
    md += f"- Contexto: Voce e {name}, apresentadora do boletim Drop Five News.\n"
    md += f"- NUNCA diga o nome do produtor, criador, proprietario ou qualquer pessoa real envolvida no projeto.\n"
    md += f"- NUNCA diga 'Jean', 'Jean Braga', 'ojeanbraga' ou qualquer variacao.\n"
    md += f"- Apresente APENAS as noticias abaixo.\n"
    md += f"- NAO analise, avalie ou comente sobre o site, o projeto, a curadoria ou as fontes.\n"
    md += f"- NAO mencione NotebookLM, GitHub, feeds, JSON, RSS ou qualquer estrutura tecnica.\n"
    md += f"- Organize por blocos tematicos na ordem abaixo.\n"
    md += f"- Use linguagem natural, coloquial brasileira, como um locutor de radio.\n"
    md += f"- Apresente-se pelo seu nome ({name}) no inicio e no encerramento.\n"
    md += f"- {persona['instruction_extra']}\n\n"

    md += f"INTRO:\n{persona['intro']}\n\n"

    md += "---\n\n"

    cur = ''; idx = 1
    for n in noticias:
        p = n.get('pilar','')
        if p != cur:
            cur = p
            label = pilares_labels.get(p, p.upper() or 'GERAL')
            md += f"\n### {label}\n"
            transition = persona['transitions'].get(p, '')
            if transition:
                md += f"[TRANSICAO] {transition}\n\n"
        md += f'{idx}. {n["titulo"]}\n\n'
        idx += 1

    md += "---\n\n"
    md += f"ENCERRAMENTO:\n{persona['outro']}\n"

    return md

def gerar_feeds_json(date, data_br, noticias):
    items = [{"id":date,"title":f"D5N • {data_br}","url":f"https://d5n-daily.netlify.app/","date_published":date,"summary":f"{len(noticias)} notícias","tags":["notícias","D5N"],"content_text":"\n".join(f"[{n.get('pilar','')}] {n['titulo']}" for n in noticias)}]
    return json.dumps({"version":"https://jsonfeed.org/version/1","title":"Hoje no Drop Five News","home_page_url":"https://d5n-daily.netlify.app","feed_url":"https://d5n-daily.netlify.app/feed.json","description":"Curadoria diária de notícias","author":{"name":"Jean Braga","url":"https://instagram.com/ojeanbraga.s"},"items":items},ensure_ascii=False,indent=2)

def gerar_feed_rss(date, data_br, noticias):
    import xml.sax.saxutils as saxutils
    desc = saxutils.escape(f"{len(noticias)} notícias: "+". ".join(n['titulo'] for n in noticias[:3]))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Hoje no Drop Five News</title>
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
    parser.add_argument('--site-only', action='store_true', help='Atualiza somente index.html usando a última edição D5N disponível')
    args = parser.parse_args()
    date = args.data
    if args.site_only:
        latest_podcast = find_latest_podcast()
        if latest_podcast:
            date = latest_podcast['date']
    data_br = format_data_br(date)
    data_curta = format_data_curta(date)
    noticias = load_today_news(date)
    
    # Carrega dados do Coverage Ledger (usado para badges, quality score e fallback)
    coverage_data = load_coverage_for_date(date)

    # Fallback: se não achou trends, tentar coverage ledger primeiro
    if noticias:
        print(f"📄 {len(noticias)} notícias dos trends do dia")
    else:
        # Coverage Fallback: se não tem trends, usar dados do Coverage Ledger
        noticias = []
        if coverage_data and coverage_data.get("scores"):
            db_path = os.environ.get("D5N_COVERAGE_DB", os.path.join(BASE, ".coverage-ledger", "coverage.db"))
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cur = conn.execute(
                    "SELECT title, pillar, source_name FROM coverage WHERE covered_date = ? AND episode_num IS NOT NULL ORDER BY score DESC",
                    (date,)
                )
                for row in cur.fetchall():
                    noticias.append({'pilar': row[1] or 'Global', 'titulo': row[0][:120], 'fonte': row[2] or 'D5N'})
                conn.close()
            except Exception as e:
                print(f"⚠️  Erro ao carregar do coverage: {e}")
        
        # Último fallback: source.md existente
        if not noticias:
            src_path = f"{BASE}/source.md"
            if os.path.exists(src_path):
                with open(src_path) as f:
                    cur_pillar = ''
                    for line in f:
                        line = line.strip()
                        # Capturar headers de pilar
                        pm = re.match(r'^###\s+(.+)$', line)
                        if pm:
                            raw = pm.group(1).upper().strip()
                            for k, v in [('GLOBAL', 'Global'), ('BRASIL', 'Brasil'),
                                         ('TECH', 'Tech'), ('ECONOMIA', 'Economia')]:
                                if k in raw:
                                    cur_pillar = v
                                    break
                            continue
                        # Capturar itens numerados, removendo numeração duplicada
                        m = re.match(r'^\d+\.\s+(.+)$', line)
                        if m:
                            titulo = m.group(1).strip()[:120]
                            # Strip leading numeração interna (ex: "1. Congresso..." -> "Congresso...")
                            titulo = re.sub(r'^\d+\.\s+', '', titulo)
                            noticias.append({'pilar': cur_pillar, 'titulo': titulo, 'fonte': 'D5N'})
        
        if noticias:
            src = "Coverage Ledger" if not any(noticias[0].get('pilar') == '' for _ in [1]) else "source.md"
            print(f"📄 {len(noticias)} notícias via fallback ({src})")
    
    if not noticias:
        print("❌ ERRO: Nenhuma notícia disponível")
        sys.exit(1)
    # O site mantém o último player e o histórico visíveis todos os dias.
    # Domingo apenas impede a geração de um novo episódio; não oculta o acervo.
    podcast = None if args.no_podcast else find_latest_podcast()
    episodios = [] if args.no_podcast else list_episodes()
    
    voice = get_voice_of_day(date)
    if coverage_data.get("quality_score"):
        print(f"📊 Coverage Ledger: quality_score={coverage_data['quality_score']}, {len(coverage_data['scores'])} notícias com score")
    
    os.makedirs(ARQUIVO_DIR, exist_ok=True)

    html = gerar_html(date, data_br, data_curta, noticias, podcast, episodios, coverage_data=coverage_data, voice=voice)
    with open(f"{BASE}/index.html",'w') as f: f.write(html)
    print(f"✅ index.html — {len(html)} bytes, {len(noticias)} notícias")

    if args.site_only:
        print("✅ site-only — fontes, feeds e arquivo D5N preservados")
        return

    md = gerar_source_md(date, data_br, noticias, voice=voice)
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

    # Gera feed RSS de podcast para players externos (Apple Podcasts, Spotify)
    subprocess.run(
        [sys.executable, f"{BASE}/scripts/gerar_podcast_feed.py"],
        timeout=60, cwd=BASE, env={**os.environ, "D5N_BASE": BASE}
    )

    print(f"\n📊 {len(noticias)} notícias, {len(episodios)} episódios")
    print(f"🌐 https://d5n-daily.netlify.app/")

if __name__ == '__main__':
    main()
