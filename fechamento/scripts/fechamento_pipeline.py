#!/usr/bin/env python3
"""Pipeline editorial e de áudio do FECHAMENTO DO MERCADO.

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

FC_ROOT = Path(__file__).resolve().parents[1]
MC_ROOT = FC_ROOT
REPO = FC_ROOT.parent
AUDIO_DIR = MC_ROOT / "audio"
REPORTS_DIR = MC_ROOT / "reports"
MANIFEST_DIR = MC_ROOT / "manifests"
SCRIPT_DIR = MC_ROOT / "scripts"
ROTEIROS_DIR = MC_ROOT / "roteiros"
VOICE = "pt-BR-AntonioNeural"
RSS_CTA = (
    "Agora você também pode assinar o Fechamento do Mercado no seu aplicativo de podcast. "
    "O RSS próprio está no site do Drop Five News."
)
TZ = ZoneInfo("America/Sao_Paulo")
MIN_WORDS, MAX_WORDS = 1100, 1500
MIN_SECONDS, MAX_SECONDS = 480, 600
FORBIDDEN = (
    "e aí, pessoal", "se liga", "vale lembrar", "em um mundo", "não é apenas",
    "mais do que nunca", "mergulhar", "revolucionar", "game changer",
    "vale destacar", "fica a dica", "bombou", "galera",
)
RSS_QUERIES = (
    "Ibovespa hoje fechamento",
    "dólar cotação Brasil",
    "Bolsa Brasil estrangeiro fluxo",
    "economia Brasil mercado financeiro",
    "varejo Brasil crise",
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


def deepseek_token() -> str | None:
    """Retorna a DEEPSEEK_API_KEY (provedor de IA da geração da MC)."""
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    if env_key:
        return env_key
    try:
        for line in Path("/root/.hermes/.env").read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None



def groq_token() -> str | None:
    """Retorna a GROQ_API_KEY (fallback gratuito para geracao do roteiro)."""
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        return env_key
    try:
        for line in Path("/root/.hermes/.env").read_text().splitlines():
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def generate_script_groq(prompt: str) -> str | None:
    """Gera o roteiro via Groq (gpt-oss-120b, camada gratuita). None em falha."""
    token = groq_token()
    if not token:
        return None
    try:
        payload = json.dumps({
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 16384,
            "temperature": 0.35,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "DropFiveNews/1.0",
            },
        )
        response = json.loads(urllib.request.urlopen(req, timeout=240).read())
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        # gpt-oss pode retornar raciocinio; mantem apenas o texto final
        if "</think>" in content:
            content = content.split("</think>", 1)[1].strip()
        return content or None
    except Exception as exc:
        print(f"AVISO Groq indisponivel: {exc}", file=sys.stderr)
        return None

def auth_token() -> str | None:
    """Fallback legado (opencode-go). Mantido para compatibilidade, mas o
    pipeline prefere DeepSeek direto em generate_script()."""
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


def generate_script(day: date, news: list[dict[str, str]], feedback: list[str] | None = None) -> str:
    weekdays = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    source_text = "\n".join(
        f"[{i}] {x['title']} | veículo: {x['source']} | publicado: {x['published']} | URL: {x['url']}"
        for i, x in enumerate(news, 1)
    )
    prompt = f"""Você é editor-chefe e roteirista da FECHAMENTO DO MERCADO, programa em áudio do Drop Five News.
DATA EDITORIAL: {day.strftime('%d/%m/%Y')}, {weekdays[day.weekday()]}.

Escreva um roteiro jornalístico falável em português brasileiro, com alvo de 1350 palavras e limite absoluto entre {MIN_WORDS} e {MAX_WORDS} palavras, para voz masculina. Faça uma contagem silenciosa antes de responder e enxugue repetições se ultrapassar o alvo. Entregue SOMENTE o texto falado, sem markdown, rubricas, emojis, listas ou URLs.
{'' if not feedback else chr(10) + 'CORREÇÕES OBRIGATÓRIAS DO CRÍTICO (versão anterior foi reprovada):' + chr(10) + chr(10).join('- ' + f for f in feedback) + chr(10)}

Arquitetura obrigatória (Sextouro — 6 blocos provocativos, dado→contexto→impacto):
1. Cold open 3-4 manchetes-tiro do pregão (Ibovespa, dólar, destaque), pela consequência. Máx 50 palavras, sem contexto; só então: “Boa noite! Eu sou Antonio e este é o Fechamento do Mercado, do Drop Five News.”
2. SEIS blocos numerados, cada um com título provocativo curto: [1] Ibovespa do dia | [2] Dólar e juros (Focus BCB) | [3] Destaque do dia | [4] Gringo e fluxo (Nasdaq) | [5] Setor em foco | [6] Radar amanhã. Se fraco, substitua — nunca preencha por obrigação.
3. Cada bloco: gancho → detalhe/contexto → consequência “o que muda pra você” → próximo movimento. Varie fechos.
4. Uma notícia puxa a seguinte (continuidade/contraste). Transições vivas, curtas. Uma vez no meio, fale com “você” (sem header).
5. “Radar amanhã”: um acontecimento verificável que pode mudar o dia seguinte.
6. Feche com síntese + CTA exato “{RSS_CTA}” + despedida + “Bom dia!”. Sem despedidas antes.

Regras editoriais:
- Não invente números, declarações, causas ou consequências.
- Não diga “segundo especialistas” sem atribuição disponível.
- Não faça recomendação financeira nem peça comentários.
- Não use clichês, superlativos, perguntas retóricas em série ou entusiasmo artificial.
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
    # Tenta chamada direta à API DeepSeek (mais rápida, 0 tokens de overhead).
    token = deepseek_token()
    if token:
        try:
            payload = json.dumps({
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 12000,
                "temperature": 0.35,
                "thinking": {"type": "disabled"},
            }).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "DropFiveNews/1.0"},
            )
            response = json.loads(urllib.request.urlopen(req, timeout=240).read())
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as primary_exc:
            print(f"AVISO API DeepSeek indisponível: {primary_exc}; tentando opencode-go", file=sys.stderr)
            content = None
    else:
        content = None
    if content is None:
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
            except Exception as fallback_exc:
                print(f"AVISO opencode-go indisponível: {fallback_exc}", file=sys.stderr)
                content = None
    if content is None:
        content = generate_script_groq(prompt)
        if content:
            return re.sub(r"^```(?:text)?\s*|\s*```$", "", content, flags=re.I | re.S).strip()
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
    if RSS_CTA.casefold() not in lower:
        errors.append("CTA do RSS próprio ausente")
    if not MIN_WORDS <= len(words) <= MAX_WORDS:
        errors.append(f"palavras fora da faixa: {len(words)}")
    if "fechamento do mercado" not in lower or "drop five news" not in lower:
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
    return {
        "words": len(words),
        "forbidden_hits": found,
        "ending_ok": True,
        "rss_cta_ok": True,
    }


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
    path = ROTEIROS_DIR / f"source-fechamento-{day.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    sources = "\n".join(f"- [{x['source']}]({x['url']}) — {x['title']}" for x in news)
    path.write_text(
        f"# FECHAMENTO DO MERCADO — {day.strftime('%d/%m/%Y')}\n\n"
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
    output = AUDIO_DIR / f"fechamento-{day.isoformat()}{suffix}.mp3"
    voice = Path(f"/tmp/fechamento-{day.isoformat()}-voice.mp3")

    news = collect_news(day)
    # Loop crítico-executor: o crítico (gates de texto/voz/mix) reprova com
    # feedback específico e o executor regenera incorporando a correção.
    MAX_ROUNDS = 4
    feedback: list[str] = []
    script = None
    for attempt in range(1, MAX_ROUNDS + 1):
        script = generate_script(day, news, feedback)
        try:
            text_gate = validate_text(script, day)
        except RuntimeError as exc:
            feedback.append(f"TEXTO reprovado no gate editorial: {exc}. Corrija e regenere.")
            print(f"AVISO crítico rodada {attempt}: {feedback[-1]}", file=sys.stderr)
            continue
        synthesize(script, voice)
        voice_metrics = probe(voice)
        vdur = float(voice_metrics["duration"])
        if 350 <= vdur <= 750:
            break  # aprovado pelo crítico
        if vdur < 350:
            feedback.append(f"ROTEIRO CURTO demais para a locução: {vdur:.0f}s de áudio (mínimo 420s). Expanda cada bloco com mais contexto e impacto até ~1350 palavras.")
        else:
            feedback.append(f"ROTEIRO LONGO demais para a locução: {vdur:.0f}s de áudio (máximo 650s). Enxugue repetições e resumos até ~1250 palavras.")
        print(f"AVISO crítico rodada {attempt}: {feedback[-1]}", file=sys.stderr)
    else:
        raise RuntimeError("crítico reprovou após " + str(MAX_ROUNDS) + " rodadas: última queixa — " + feedback[-1])

    mixer = SCRIPT_DIR / "fechamento_mixer.py"
    proc = run([sys.executable, str(mixer), "--voz", str(voice), "--output", str(output)], timeout=600)
    if proc.returncode != 0:
        raise RuntimeError("Mixer falhou: " + (proc.stderr or proc.stdout)[-500:])

    metrics = probe(output)
    metrics.update(loudness(output))
    if not 420 <= float(metrics["duration"]) <= 650:
        raise RuntimeError(f"duração final fora da faixa: {metrics['duration']:.1f}s")
    if not -17.5 <= float(metrics["lufs"]) <= -14.5:
        raise RuntimeError(f"loudness fora da faixa: {metrics['lufs']:.2f} LUFS")
    if float(metrics["true_peak_dbtp"]) > -1.0:
        raise RuntimeError(f"true peak inseguro: {metrics['true_peak_dbtp']:.2f} dBTP")

    source = write_source(day, script, news, metrics, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "program": "FECHAMENTO DO MERCADO", "date": day.isoformat(), "timezone": "America/Sao_Paulo",
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
