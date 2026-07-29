#!/usr/bin/env python3
"""Pipeline editorial e de áudio da MANHÃ CONECTADA.

Coleta RSS, redige com LLM, valida o roteiro, sintetiza Antonio pt-BR,
mixa, mede e publica artefatos locais. O envio é responsabilidade do cron Hermes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path("/root/repositorio/d5n-videocast-source")
AUDIO_DIR = REPO / "audio"
REPORTS_DIR = REPO / "reports" / "manha-conectada"
MANIFEST_DIR = REPO / "manifests" / "manha-conectada"
VOICE = "pt-BR-AntonioNeural"
TZ = ZoneInfo("America/Sao_Paulo")
MIN_WORDS, MAX_WORDS = 540, 820
MIN_SECONDS, MAX_SECONDS = 225, 390
FORBIDDEN = (
    "e aí, pessoal", "se liga", "vale lembrar", "em um mundo", "não é apenas",
    "mais do que nunca", "mergulhar", "jornada", "revolucionar", "game changer",
    "vale destacar", "fica a dica", "bombou", "galera",
)
RSS_QUERIES = (
    "Brasil últimas notícias",
    "mundo últimas notícias",
    "tecnologia inteligência artificial",
    "economia Brasil",
    "agenda Brasil hoje",
)


ACENTO_EN = {
    # Tech / Business → pronúncia amigável pt-BR
    "CEO": "chief executive officer",
    "startup": "startap",
    "marketing": "márquétin",
    "branding": "bréndin",
    "influencer": "influensér",
    "crypto": "cripto",
    "blockchain": "bloquecain",
    "bitcoin": "bitcain",
    "token": "tôquen",
    "NFT": "n-éfe-tê",
    "cloud": "nuvem",
    "cyber": "cibér",
    "machine learning": "aprendizado de máquina",
    "deep learning": "aprendizado profundo",
    "big data": "bigadáta",
    "software": "softuér",
    "hardware": "rardiúér",
    "firmware": "firmuér",
    "data center": "dátacenter",
    "hacker": "ráquer",
    "malware": "máuér",
    "ransomware": "ransomuér",
    "phishing": "fíchin",
    "growth": "grôt",
    "scale": "escala",
    "framework": "frameduérqui",
    "deadline": "dédlaine",
    "performance": "performánce",
    "delivery": "delivérí",
    "e-commerce": "e-comércio",
    "online": "ônlaine",
    "login": "lóguin",
    "logout": "lógaute",
    "feedback": "fídebaque",
    "workshop": "uórquichope",
    "mindset": "máindset",
    "venture capital": "vênture capital",
    "compliance": "compláiência",
    "accountability": "acontabílidade",
    "stakeholder": "stáquehólder",
    "disruptivo": "disruptivo",
    "resiliente": "re-zili-ente",
    "briefing": "brífin",
    "stand by": "stándbai",
    "benchmark": "bentchimarc",
    "margin call": "márjin cáll",
    "trading": "tréidin",
    "stock": "estóque",
    "funding": "fándin",
    "budget": "bádjet",
    "pipeline": "páipélaine",
    "roadmap": "ródimape",
    "CEO": "chief executive officer",
}


def normalizar_pt_br(texto: str) -> str:
    """Normaliza texto para TTS em português brasileiro.
    Substitui anglicismos, hispanismos e estrangeirismos por
    pronúncias amigáveis ao sintetizador pt-BR."""
    # 1. Substitui expressões multi-word antes das single-word
    # (mais específicas primeiro para evitar substituições parciais)
    for en, pt in sorted(ACENTO_EN.items(), key=lambda x: -len(x[0].split())):
        texto = re.sub(
            rf'(?<![a-zÀ-ÿ]){re.escape(en)}(?![a-zÀ-ÿ])',
            pt, texto, flags=re.I
        )

    # 2. Padrões de data em inglês → português
    texto = re.sub(r'\bMonday\b', 'segunda-feira', texto, flags=re.I)
    texto = re.sub(r'\bTuesday\b', 'terça-feira', texto, flags=re.I)
    texto = re.sub(r'\bWednesday\b', 'quarta-feira', texto, flags=re.I)
    texto = re.sub(r'\bThursday\b', 'quinta-feira', texto, flags=re.I)
    texto = re.sub(r'\bFriday\b', 'sexta-feira', texto, flags=re.I)
    texto = re.sub(r'\bSaturday\b', 'sábado', texto, flags=re.I)
    texto = re.sub(r'\bSunday\b', 'domingo', texto, flags=re.I)
    texto = re.sub(r'\bJanuary\b', 'janeiro', texto, flags=re.I)
    texto = re.sub(r'\bFebruary\b', 'fevereiro', texto, flags=re.I)
    texto = re.sub(r'\bMarch\b', 'março', texto, flags=re.I)
    texto = re.sub(r'\bApril\b', 'abril', texto, flags=re.I)
    texto = re.sub(r'\bMay\b', 'maio', texto, flags=re.I)
    texto = re.sub(r'\bJune\b', 'junho', texto, flags=re.I)
    texto = re.sub(r'\bJuly\b', 'julho', texto, flags=re.I)
    texto = re.sub(r'\bAugust\b', 'agosto', texto, flags=re.I)
    texto = re.sub(r'\bSeptember\b', 'setembro', texto, flags=re.I)
    texto = re.sub(r'\bOctober\b', 'outubro', texto, flags=re.I)
    texto = re.sub(r'\bNovember\b', 'novembro', texto, flags=re.I)
    texto = re.sub(r'\bDecember\b', 'dezembro', texto, flags=re.I)

    # 3. Meses em espanhol → português
    texto = re.sub(r'\benero\b', 'janeiro', texto, flags=re.I)
    texto = re.sub(r'\bfebrero\b', 'fevereiro', texto, flags=re.I)
    texto = re.sub(r'\bmarzo\b', 'março', texto, flags=re.I)
    texto = re.sub(r'\babril\b', 'abril', texto, flags=re.I)
    texto = re.sub(r'\bmayo\b', 'maio', texto, flags=re.I)
    texto = re.sub(r'\bjunio\b', 'junho', texto, flags=re.I)
    texto = re.sub(r'\bjulio\b', 'julho', texto, flags=re.I)
    texto = re.sub(r'\bagosto\b', 'agosto', texto, flags=re.I)
    texto = re.sub(r'\bseptiembre\b', 'setembro', texto, flags=re.I)
    texto = re.sub(r'\boctubre\b', 'outubro', texto, flags=re.I)
    texto = re.sub(r'\bnoviembre\b', 'novembro', texto, flags=re.I)
    texto = re.sub(r'\bdiciembre\b', 'dezembro', texto, flags=re.I)

    # 4. Palavras espanholas comuns → português
    texto = re.sub(r'\blunes\b', 'segunda-feira', texto, flags=re.I)
    texto = re.sub(r'\bmartes\b', 'terça-feira', texto, flags=re.I)
    texto = re.sub(r'\bmiércoles\b', 'quarta-feira', texto, flags=re.I)
    texto = re.sub(r'\bjueves\b', 'quinta-feira', texto, flags=re.I)
    texto = re.sub(r'\bviernes\b', 'sexta-feira', texto, flags=re.I)
    texto = re.sub(r'\bsábado\b', 'sábado', texto, flags=re.I)
    texto = re.sub(r'\bdomingo\b', 'domingo', texto, flags=re.I)

    # 5. Símbolos de moeda
    texto = texto.replace('$', ' dólares ')
    texto = texto.replace('€', ' euros ')
    texto = texto.replace('£', ' libras ')

    # 6. Siglas comuns que o TTS pronuncia errado
    texto = re.sub(r'\b(?:IA|ia)\b', 'inteligência artificial', texto)

    # 7. Limpa espaços duplicados
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def run(cmd: list[str], *, timeout: int = 300, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=capture, timeout=timeout, check=False)


def holiday_name(day: date) -> str | None:
    """Retorna feriado nacional; BrasilAPI é primária e fallback cobre datas fixas."""
    url = f"https://brasilapi.com.br/api/feriados/v1/{day.year}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DropFiveNews/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        for item in data:
            if item.get("date") == day.isoformat():
                return str(item.get("name") or "Feriado nacional")
    except Exception:
        fixed = {
            (1, 1): "Confraternização Universal", (4, 21): "Tiradentes",
            (5, 1): "Dia do Trabalho", (9, 7): "Independência do Brasil",
            (10, 12): "Nossa Senhora Aparecida", (11, 2): "Finados",
            (11, 15): "Proclamação da República", (11, 20): "Consciência Negra",
            (12, 25): "Natal",
        }
        return fixed.get((day.month, day.day))
    return None


def business_day(day: date) -> tuple[bool, str]:
    if day.weekday() >= 5:
        return False, "fim de semana"
    holiday = holiday_name(day)
    if holiday:
        return False, holiday
    return True, "dia útil"


def collect_news(day: date) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in RSS_QUERIES:
        params = urllib.parse.urlencode({"q": f"{query} when:1d", "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"})
        url = "https://news.google.com/rss/search?" + params
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DropFiveNews/1.0"})
            root = ET.fromstring(urllib.request.urlopen(req, timeout=25).read())
            for node in root.findall("./channel/item")[:5]:
                title = (node.findtext("title") or "").strip()
                link = (node.findtext("link") or "").strip()
                published = (node.findtext("pubDate") or "").strip()
                source_node = node.find("source")
                source = (source_node.text or "Google News").strip() if source_node is not None else "Google News"
                key = re.sub(r"\W+", " ", title.casefold()).strip()
                if title and link and key not in seen:
                    seen.add(key)
                    items.append({"query": query, "title": title, "url": link, "source": source, "published": published})
        except Exception as exc:
            print(f"AVISO coleta {query}: {exc}", file=sys.stderr)
    if len(items) < 10:
        raise RuntimeError(f"coleta insuficiente: {len(items)} itens")
    return items[:25]


def auth_token() -> str | None:
    """Tenta obter token opencode-go do ambiente, depois do auth.json."""
    env_key = os.environ.get("OPENCODE_GO_API_KEY")
    if env_key:
        return env_key
    for path in (Path("/root/.hermes/profiles/d5n/auth.json"), Path("/root/.hermes/auth.json")):
        try:
            data = json.loads(path.read_text())
            creds = data.get("credential_pool", {}).get("opencode-go", [])
            for cred in creds:
                token = cred.get("access_token") or cred.get("api_key") or os.environ.get(cred.get("label", "").removeprefix("OPENCODE_GO_API_KEY"))
                if token:
                    return token
        except Exception:
            continue
    return None


def generate_script(day: date, news: list[dict[str, str]]) -> str:
    weekdays = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    source_text = "\n".join(
        f"[{i}] {x['title']} | veículo: {x['source']} | publicado: {x['published']} | URL: {x['url']}"
        for i, x in enumerate(news, 1)
    )
    prompt = f"""Você é editor-chefe e roteirista da MANHÃ CONECTADA, programa em áudio do Drop Five News.
DATA EDITORIAL: {day.strftime('%d/%m/%Y')}, {weekdays[day.weekday()]}.

Escreva um roteiro jornalístico falável em português brasileiro, entre {MIN_WORDS} e {MAX_WORDS} palavras, para voz masculina. Entregue SOMENTE o texto falado, sem markdown, rubricas, emojis, listas ou URLs.

Arquitetura obrigatória, inspirada na eficiência de briefings modernos sem imitar apresentadores ou marcas:
1. Comece pela notícia mais forte já na primeira frase. Entregue três manchetes específicas em até 35 palavras; só então diga: “Eu sou Antonio e esta é a Manhã Conectada, do Drop Five News.”
2. Desenvolva cinco notícias em sequência fluida: agenda do dia; Brasil; mundo; tecnologia; economia. Se uma categoria estiver fraca, substitua por uma notícia mais relevante — nunca complete tabela por obrigação.
3. Cada notícia segue fato → contexto → efeito prático → próximo movimento. Mantenha ritmo alto, mas dê contexto suficiente para o ouvinte não depender de outro conteúdo.
4. Faça uma notícia puxar a seguinte por continuidade, contraste ou consequência. Evite anunciar “agora vamos falar de”.
5. Antes do encerramento, inclua o “Sinal 11”: escolha um único acontecimento verificável que ainda pode mudar o dia até o começo da tarde e diga objetivamente o que acompanhar. Não dê conselho financeiro.
6. Feche com uma síntese útil, convide a acompanhar o Drop Five News e termine exatamente com “Bom dia!”. Não faça despedidas antes do final.

Regras editoriais:
- Não invente números, declarações, causas ou consequências.
- Não diga “segundo especialistas” sem atribuição disponível.
- Não faça recomendação financeira nem peça comentários/compartilhamentos.
- Não use clichês, superlativos, perguntas retóricas ou entusiasmo artificial.
- Não use as expressões: {', '.join(FORBIDDEN)}.
- Diga “Drop Five News” por extenso.
- Não fale URLs, nomes de arquivos, emojis ou instruções de produção.
- O texto precisa soar escrito por uma redação brasileira, não traduzido.
- Não mencione The Brief, TecMundo ou Amanda Flaury no roteiro.
- NÃO use palavras em inglês: substitua "CEO" por "presidente", "startup" por "empresa de tecnologia", "crypto" por "criptomoedas", "AI/IA" por "inteligência artificial", "cloud" por "nuvem", "online" por "digital", "software" por "programa", "deadline" por "prazo", "feedback" por "retorno/avaliação", "marketing" por "propaganda/promoção", "branding" por "marca".
- NÃO use palavras em espanhol: datas, dias da semana, meses, saudações — tudo em português brasileiro.
- Se uma notícia tiver nome estrangeiro, escreva-o com pronúncia brasileira.

FONTES CANDIDATAS:
{source_text}
"""
    # Tenta chamada direta à API opencode-go (mais rápida, 0 tokens de overhead).
    token = auth_token()
    if token:
        try:
            payload = json.dumps({
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 12000,
                "temperature": 0.35,
            }).encode()
            req = urllib.request.Request(
                "https://opencode.ai/zen/go/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "DropFiveNews/1.0"},
            )
            response = json.loads(urllib.request.urlopen(req, timeout=240).read())
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as primary_exc:
            print(f"AVISO API direta indisponível: {primary_exc}; usando Hermes CLI", file=sys.stderr)
            content = None
    else:
        content = None
    if content is None:
        proc = run([
            "hermes", "-z", prompt, "--provider", "openai-codex", "-m", "gpt-5.6-sol",
            "--cli", "--ignore-rules", "--safe-mode",
        ], timeout=600)
        if proc.returncode != 0:
            raise RuntimeError("fallback Hermes falhou: " + (proc.stderr or proc.stdout)[-500:])
        content = proc.stdout.strip()
    if not content:
        raise RuntimeError("modelo retornou roteiro vazio")
    return re.sub(r"^```(?:text)?\s*|\s*```$", "", content, flags=re.I | re.S).strip()


def validate_text(text: str, day: date) -> dict[str, object]:
    errors: list[str] = []
    words = re.findall(r"\b[\wÀ-ÿ'-]+\b", text)
    lower = text.casefold()
    if not MIN_WORDS <= len(words) <= MAX_WORDS:
        errors.append(f"palavras fora da faixa: {len(words)}")
    if "manhã conectada" not in lower or "drop five news" not in lower:
        errors.append("marcas obrigatórias ausentes")
    if not text.rstrip().endswith("Bom dia!"):
        errors.append("encerramento obrigatório ausente")
    found = [term for term in FORBIDDEN if term in lower]
    if found:
        errors.append("expressões bloqueadas: " + ", ".join(found))
    if re.search(r"https?://|www\.", text, re.I):
        errors.append("URL no texto falado")
    if re.search(r"[😀-🙏🌀-🫿]", text):
        errors.append("emoji no texto falado")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {"words": len(words), "forbidden_hits": found, "ending_ok": True}


def synthesize(text: str, output: Path) -> None:
    clean = re.sub(r"\s+", " ", text).strip()
    clean = normalizar_pt_br(clean)
    proc = run(["edge-tts", "--voice", VOICE, "--rate=-2%", "--pitch=-2Hz", "--text", clean, "--write-media", str(output)], timeout=600)
    if proc.returncode != 0 or not output.exists() or output.stat().st_size < 50_000:
        raise RuntimeError("falha no TTS: " + (proc.stderr or proc.stdout)[-300:])


def probe(path: Path) -> dict[str, float | int | str]:
    proc = run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size,bit_rate", "-of", "json", str(path)])
    data = json.loads(proc.stdout)["format"]
    return {"duration": float(data["duration"]), "size": int(data["size"]), "bit_rate": int(data.get("bit_rate", 0))}


def loudness(path: Path) -> dict[str, float]:
    proc = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], timeout=300)
    match = re.search(r'\{\s*"input_i".*?\}', proc.stderr, re.S)
    if not match:
        raise RuntimeError("medição de loudness indisponível")
    data = json.loads(match.group(0))
    return {"lufs": float(data["input_i"]), "true_peak_dbtp": float(data["input_tp"]), "lra": float(data["input_lra"])}


def write_source(day: date, text: str, news: list[dict[str, str]], metrics: dict[str, float | int | str], output: Path) -> Path:
    path = REPO / f"source-manha-{day.isoformat()}.md"
    sources = "\n".join(f"- [{x['source']}]({x['url']}) — {x['title']}" for x in news)
    path.write_text(
        f"# MANHÃ CONECTADA — {day.strftime('%d/%m/%Y')}\n\n"
        f"## Roteiro aprovado\n\n{text}\n\n"
        f"## Fontes coletadas\n\n{sources}\n\n"
        f"## Áudio\n\n- Arquivo: `{output.name}`\n- Voz: `{VOICE}`\n"
        f"- Duração: {metrics['duration']:.2f}s\n- Loudness: {metrics['lufs']:.2f} LUFS\n"
        f"- True peak: {metrics['true_peak_dbtp']:.2f} dBTP\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Data editorial YYYY-MM-DD; padrão: hoje em São Paulo")
    parser.add_argument("--allow-nonbusiness-day", action="store_true", help="Permite protótipo em fim de semana/feriado")
    parser.add_argument("--prototype", action="store_true", help="Acrescenta sufixo prototipo ao arquivo")
    args = parser.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(TZ).date()
    ok, reason = business_day(day)
    if not ok and not args.allow_nonbusiness_day:
        print(json.dumps({"status": "skip", "date": day.isoformat(), "reason": reason}, ensure_ascii=False))
        return 0

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "-prototipo" if args.prototype else ""
    output = AUDIO_DIR / f"manha-conectada-{day.isoformat()}{suffix}.mp3"
    voice = Path(f"/tmp/manha-conectada-{day.isoformat()}-voice.mp3")

    news = collect_news(day)
    script = generate_script(day, news)
    text_gate = validate_text(script, day)
    synthesize(script, voice)
    voice_metrics = probe(voice)
    if not MIN_SECONDS <= float(voice_metrics["duration"]) <= MAX_SECONDS:
        raise RuntimeError(f"duração da voz fora da faixa: {voice_metrics['duration']:.1f}s")

    mixer = REPO / "scripts" / "amanha_conectada_mixer.py"
    proc = run([sys.executable, str(mixer), "--voz", str(voice), "--output", str(output)], timeout=600)
    if proc.returncode != 0:
        raise RuntimeError("Mixer falhou: " + (proc.stderr or proc.stdout)[-500:])

    metrics = probe(output)
    metrics.update(loudness(output))
    if not MIN_SECONDS <= float(metrics["duration"]) <= MAX_SECONDS:
        raise RuntimeError(f"duração final fora da faixa: {metrics['duration']:.1f}s")
    if not -17.5 <= float(metrics["lufs"]) <= -14.5:
        raise RuntimeError(f"loudness fora da faixa: {metrics['lufs']:.2f} LUFS")
    if float(metrics["true_peak_dbtp"]) > -1.0:
        raise RuntimeError(f"true peak inseguro: {metrics['true_peak_dbtp']:.2f} dBTP")

    source = write_source(day, script, news, metrics, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "program": "MANHÃ CONECTADA", "date": day.isoformat(), "timezone": "America/Sao_Paulo",
        "prototype": args.prototype, "business_day_override": bool(args.allow_nonbusiness_day and not ok),
        "voice": VOICE, "output": str(output), "source_file": str(source), "sha256": digest,
        "text_gate": text_gate, "audio": metrics, "sources": news,
        "generated_at": datetime.now(TZ).isoformat(),
    }
    manifest_path = MANIFEST_DIR / f"{day.isoformat()}{suffix}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "file": str(output), "source": str(source), "manifest": str(manifest_path), "audio": metrics, "words": text_gate["words"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
