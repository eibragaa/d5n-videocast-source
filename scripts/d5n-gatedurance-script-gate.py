#!/usr/bin/env python3
"""GateDurance — gate de qualidade do ROTEIRO em texto (pré-TTS) do Drop Five News.

Valida os arquivos .txt de /tmp/d5n_audio ANTES de sintetizar áudio, aplicando
as mesmas regras dos validadores finais (d5n-podcast-quality-gate.py e
d5n_daily_release_gate.py) mais checagens extras de higiene. A ideia: pegar o
erro no texto, barato e rápido, antes de gastar tempo e tokens com Edge-TTS.

Regras cobertas:
  1. Estrutura: >=9 seções, seções essenciais presentes, Header no formato "Header X".
  2. Língua: texto falado 100% em PT-BR (detecta trechos em inglês — causa #1 de bloqueio).
  3. Data: intro com dia da semana + data por extenso em português; intro começa com
     "Bom dia!"; outro termina com "Bom dia!".
  4. Higiene de fala: sem (hum...), (pausa), (pensando), numeração por extenso
     "1 (um)", sem emoji/URL/markdown no texto falado, sem reticências espaçadas.
  5. Contagem: roteiro falado 850–1900 palavras.
  6. Proibições: clichês da lista BANNED_PHRASES, despedida intermediária, CTA fora
     do encerramento, expressões FORBIDDEN.

Saída: exit 0 = pronto para TTS; exit 1 = BLOQUEADO com lista de erros.
Uso: python3 d5n-gatedurance-script-gate.py [--audio-dir /tmp/d5n_audio] [--date 2026-08-06] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

PILLARS = ("GLOBAL", "BRASIL", "TECH", "ECONOMIA")
SECTION_ORDER = (
    "intro", "mundo", "brasil", "saude", "ciencia", "politica", "tecnologia",
    "economia", "ofertas", "frase", "historia", "cta", "outro",
)
REQUIRED_SECTIONS = {"intro", "mundo", "brasil", "tecnologia", "economia", "ofertas", "outro"}
MIN_SECTIONS = 9
MIN_WORDS = 850
MAX_WORDS = 1900

MONTHS_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}
WEEKDAYS_PT = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira", 3: "quinta-feira",
    4: "sexta-feira", 5: "sábado", 6: "domingo",
}
BANNED_PHRASES = (
    "ferramenta no cinto", "ferramenta a mais", "cada notícia é uma ferramenta",
    "turbilhão", "jornada", "informação de qualidade", "preparados para o que vem",
    "essa foi mais uma edição",
)
FORBIDDEN = ("cinto", "DropFiveNews", "Drop News")

ENGLISH_DATE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"January|February|March|April|May|June|July|August|September|October|November|December)\b",
    re.I,
)
# Palavras de alta frequência em inglês — usadas para flagar trecho não traduzido.
ENGLISH_FUNCTION_WORDS = re.compile(
    r"\b(?:the|and|for|with|was|said|are|have|has|had|from|that|this|his|her|"
    r"they|them|their|will|would|about|after|before|during|while|into|"
    r"could|should|would|there|these|those|which|when|where|because|not|"
    r"over|under|between|against|news|update|live|latest|today|yesterday)\b",
    re.I,
)
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
URL_OR_MARKDOWN = re.compile(r"https?://|\[[^]]+\]\([^)]+\)|[*_`#]{2,}")
GOODBYE = re.compile(r"\b(?:tchau|até amanhã|até mais|valeu|falou)\b", re.I)
# Marcações de leitura que o TTS lê literalmente (higiene).
HESITATION = re.compile(
    r"\(\s*(?:hum{1,6}\.?\s*\.{0,4}|hmm{1,4}\.?\s*\.{0,4}|pausa\.?\.{0,3}|"
    r"pensando?\.?\.{0,3}|hesita(?:ndo)?\.?\.{0,3}|respir(?:a|ando)\.?\.{0,3}|"
    r"tosse\.?\.{0,3}|riso?s?\.?\.{0,3}|sil[eê]ncio\.?\.{0,3}|"
    r"murmur[ao]\.?\.{0,3}|barulho\.?\.{0,3}|\b[ae]h[m]?\b\.?\.{0,3})\s*\)",
    re.I,
)
# Enumeração por extenso: "1 (um)", "2. (dois)", "3(três)".
NUMBER_BY_EXTENSION = re.compile(
    r"\b\d{1,3}\s*[.)]?\s*\(\s*(?:um|dois|tr[êe]s|quatro|cinco|seis|sete|oito|nove|"
    r"dez|onze|doze|treze|quatorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte)\s*\)",
    re.I,
)
SPACED_ELLIPSIS = re.compile(r"\s*\.\s*\.\s*\.")


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in normalized if not unicodedata.combining(c)).split())


def _date_phrase(d: date) -> str:
    return f"{d.day} de {MONTHS_PT[d.month]} de {d.year}"


def _spoken_body(text: str) -> str:
    """Remove o cabeçalho técnico Programa/Data/Voz (se presente) e o Header X da seção."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    first = _fold(lines[0])
    second = _fold(lines[1]) if len(lines) > 1 else ""
    index = 0
    if first.startswith("drop five news") or first.startswith("data:") or first.startswith("voz:"):
        index = 0
        while index < len(lines) and (
            _fold(lines[index]).startswith("drop five news")
            or _fold(lines[index]).startswith("data:")
            or _fold(lines[index]).startswith("voz:")
        ):
            index += 1
    # Remove "Header X" (1ª linha de conteúdo técnico da seção).
    if index < len(lines) and re.match(r"^header\s+", _fold(lines[index])):
        index += 1
    body = "\n".join(lines[index:]).strip()
    # O texto falado é o que vem ANTES do primeiro bloco de links (após linha em branco).
    # O validador final lê o arquivo inteiro; aqui preservamos tudo exceto cabeçalhos.
    return body


def _clean_links(text: str) -> str:
    """Remove blocos de links (linha com 🔗/[Fonte original]) para contar só fala."""
    lines = text.splitlines()
    kept = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if "fonte original" in _fold(s) or s.startswith("🔗") or re.match(r"^https?://", s):
            continue
        # Remove numerador/negrito de item de lista que acompanha a descrição.
        s = re.sub(r"^\d{1,3}[.)]\s*\*{1,2}\s*", "", s)
        s = re.sub(r"^\*{1,2}\s*", "", s)
        kept.append(s)
    return "\n".join(kept)


def validate_script(audio_dir: Path, editorial_date: date) -> tuple[list[str], dict]:
    segments: dict[str, str] = {}
    for name in SECTION_ORDER:
        path = audio_dir / f"{name}.txt"
        if path.is_file() and path.stat().st_size:
            segments[name] = path.read_text(encoding="utf-8", errors="replace").strip()

    errors: list[str] = []
    if len(segments) < MIN_SECTIONS:
        errors.append(f"roteiro precisa de pelo menos {MIN_SECTIONS} seções; encontradas {len(segments)}")
    missing = sorted(REQUIRED_SECTIONS - set(segments))
    if missing:
        errors.append("seções essenciais ausentes: " + ", ".join(missing))

    spoken = {name: _spoken_body(text) for name, text in segments.items()}
    intro = spoken.get("intro", "")
    outro = spoken.get("outro", "")

    # --- Data e abertura/encerramento ---
    expected_date = _fold(_date_phrase(editorial_date))
    expected_weekday = _fold(WEEKDAYS_PT[editorial_date.weekday()])
    folded_intro = _fold(intro)
    if expected_date not in folded_intro or expected_weekday not in folded_intro:
        errors.append(
            f"intro sem data editorial completa: {WEEKDAYS_PT[editorial_date.weekday()]}, "
            f"{_date_phrase(editorial_date)}"
        )
    if not re.match(r"^bom dia\b", folded_intro):
        errors.append("intro deve começar com 'Bom dia!'")
    if not re.search(r"\bbom dia[!.]?\s*$", _fold(outro)):
        errors.append("encerramento (outro.txt) deve terminar com 'Bom dia!'")

    # --- Língua (detecção de inglês) em todas as seções faladas ---
    all_spoken = {name: _clean_links(segments.get(name, "")) for name in segments}
    for name, text in all_spoken.items():
        if ENGLISH_DATE.search(text):
            errors.append(f"{name}.txt: dia ou mês em inglês no texto falado")
        hits = set(ENGLISH_FUNCTION_WORDS.findall(text))
        if len(hits) >= 4:
            preview = ", ".join(sorted(hits)[:6])
            errors.append(
                f"{name}.txt: trecho parece estar em inglês (palavras: {preview}). "
                f"O texto falado deve ser 100% português brasileiro."
            )
        for forbidden in FORBIDDEN:
            if forbidden.casefold() in _fold(text):
                errors.append(f"{name}.txt: expressão proibida {forbidden!r}")
        if EMOJI.search(text):
            errors.append(f"{name}.txt: emoji no texto falado")
        if URL_OR_MARKDOWN.search(text):
            errors.append(f"{name}.txt: URL ou markdown no texto falado")

    # --- Higiene de fala (marcações que o TTS lê literalmente) ---
    for name, text in all_spoken.items():
        m = HESITATION.search(text)
        if m:
            errors.append(f"{name}.txt: marcação de leitura {m.group(0)!r} (o TTS lê em voz alta)")
        m = NUMBER_BY_EXTENSION.search(text)
        if m:
            errors.append(f"{name}.txt: numeração por extenso {m.group(0)!r} (use só o numeral)")
        if SPACED_ELLIPSIS.search(text):
            errors.append(f"{name}.txt: reticências espaçadas (escreva '...' normal)")

    # --- Contagem de palavras do roteiro falado (sem links/cabeçalhos) ---
    all_text = "\n".join(_clean_links(segments.get(name, "")) for name in segments)
    all_text = re.sub(r"^header\s+\w+\s*$", "", all_text, flags=re.M | re.I)
    word_count = len(re.findall(r"\b[\wÀ-ÿ]+\b", all_text))
    if not MIN_WORDS <= word_count <= MAX_WORDS:
        errors.append(f"roteiro deve ter {MIN_WORDS}–{MAX_WORDS} palavras; recebeu {word_count}")

    # --- Clichês proibidos ---
    folded_all = _fold(all_text)
    for phrase in BANNED_PHRASES:
        if _fold(phrase) in folded_all:
            errors.append(f"clichê proibido no roteiro: {phrase!r}")

    # --- Despedida intermediária / CTA fora do lugar ---
    for name, text in all_spoken.items():
        stem = name
        if stem not in {"intro", "outro"} and GOODBYE.search(text):
            errors.append(f"{name}.txt: despedida intermediária")
        if stem not in {"cta", "outro"} and re.search(r"instagram|siga|segue a gente|me segue", text, re.I):
            errors.append(f"{name}.txt: CTA fora do encerramento")

    return errors, {"word_count": word_count, "sections": list(segments)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-dir", default="/tmp/d5n_audio")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    editorial_date = date.fromisoformat(args.date)
    audio_dir = Path(args.audio_dir)
    errors, snapshot = validate_script(audio_dir, editorial_date)

    report = {
        "ok": not errors,
        "date": editorial_date.isoformat(),
        "script": snapshot,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif errors:
        print("BLOQUEADO (gateDurance): roteiro precisa de correção antes do TTS")
        for error in errors:
            print(f"- {error}")
    else:
        print(
            f"OK (gateDurance): {editorial_date.isoformat()} · {snapshot['word_count']} palavras · "
            f"{len(snapshot['sections'])} seções · pronto para TTS"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
