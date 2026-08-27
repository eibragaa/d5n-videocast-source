"""
Funções compartilhadas de capítulos para os scripts de feed RSS.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

# ── Labels dos capítulos por programa ────────────────────────────────────────

D5N_CHAPTER_LABELS = [
    "Abertura", "Brasil & Política", "Economia", "Mundo",
    "Tecnologia & Inovações", "Encerramento",
]
MC_CHAPTER_LABELS = [
    "Abertura", "Agenda", "Clima & País", "Mundo", "Tecnologia",
    "Economia", "Sinal 11", "Encerramento",
]
FM_CHAPTER_LABELS = [
    "Abertura", "Bolsa", "Câmbio", "Fluxo estrangeiro",
    "Empresas & Radar Amanhã", "Encerramento",
]


def _paragraph_chapters(source_path: Path, labels: list[str], duration: float, lead: float = 1.8) -> list[dict]:
    """Deriva capítulos proporcionais do roteiro, dividido por parágrafos temáticos."""
    try:
        content = source_path.read_text(encoding="utf-8")
    except OSError:
        return []
    match = re.search(
        r"## Roteiro aprovado\s+(.+?)(?:\n\s*\n## |\Z)",
        content, flags=re.S
    )
    if not match:
        return []
    paragraphs = [
        re.sub(r"\s+", " ", block).strip()
        for block in match.group(1).split("\n\n")
        if len(block.strip()) > 80
    ]
    if not paragraphs:
        return []
    usable = paragraphs[:-1] if len(paragraphs) > 2 else paragraphs
    middle = max(0, len(labels) - 2)
    weights = [max(40, len(p)) for p in usable[:middle]] or [1]
    total_weight = sum(weights)
    speakable = max(10.0, duration - lead)
    chapters: list[dict] = [{"id": "intro", "label": labels[0], "start": 0.0}]
    cursor = lead
    for index, weight in enumerate(weights):
        span = speakable * 0.92 * weight / total_weight
        chapters.append({
            "id": f"seg{index}",
            "label": labels[1 + index] if 1 + index < len(labels) - 1 else labels[-2],
            "start": round(cursor, 3),
        })
        cursor += span
    last = labels[-1] if len(labels) > 1 else labels[0]
    chapters.append({"id": "outro", "label": last, "start": round(max(cursor, duration * 0.9), 3)})
    # Normaliza: end/duration coerentes e monotonia garantida.
    normalized: list[dict] = []
    for index, chapter in enumerate(chapters):
        start = min(float(chapter["start"]), duration - 1.0)
        end = float(chapters[index + 1]["start"]) if index + 1 < len(chapters) else duration
        end = min(end, duration)
        if index > 0 and end <= start:
            return []
        normalized.append({
            "id": chapter["id"],
            "label": chapter["label"],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
        })
    return normalized


def load_program_chapters(kind: str, date_str: str, duration: float) -> list[dict]:
    """Capítulos por programa: deriva do roteiro aprovado; retorna lista vazia se falhar."""
    if kind == "d5n":
        source_path = Path(__file__).parent / "manifests" / "d5n" / date_str / "coldopen.txt"
        labels = D5N_CHAPTER_LABELS
        # D5N coldopen é um texto corrido — divide em frases para weighting
        try:
            content = source_path.read_text(encoding="utf-8")
        except OSError:
            return []
        # Divide em frases (por pontuação forte)
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if not sentences:
            return []
        usable = sentences[:-1] if len(sentences) > 2 else sentences
        # Pesa por tamanho da frase
        middle = max(0, len(labels) - 2)
        weights = [max(40, len(p)) for p in usable[:middle]] or [1]
        total_weight = sum(weights)
        lead = 1.8
        speakable = max(10.0, duration - lead)
        chapters: list[dict] = [{"id": "intro", "label": labels[0], "start": 0.0}]
        cursor = lead
        for index, weight in enumerate(weights):
            span = speakable * 0.92 * weight / total_weight
            chapters.append({
                "id": f"seg{index}",
                "label": labels[1 + index] if 1 + index < len(labels) - 1 else labels[-2],
                "start": round(cursor, 3),
            })
            cursor += span
        last = labels[-1] if len(labels) > 1 else labels[0]
        chapters.append({"id": "outro", "label": last, "start": round(max(cursor, duration * 0.9), 3)})
        normalized: list[dict] = []
        for index, chapter in enumerate(chapters):
            start = min(float(chapter["start"]), duration - 1.0)
            end = float(chapters[index + 1]["start"]) if index + 1 < len(chapters) else duration
            end = min(end, duration)
            if index > 0 and end <= start:
                return []
            normalized.append({
                "id": chapter["id"],
                "label": chapter["label"],
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
            })
        return normalized
    elif kind == "manha-conectada":
        source_path = Path(__file__).parent / kind / "roteiros" / f"source-manha-{date_str}.md"
        labels = MC_CHAPTER_LABELS
    else:
        source_path = Path(__file__).parent / kind / "roteiros" / f"source-fechamento-{date_str}.md"
        labels = FM_CHAPTER_LABELS
    return _paragraph_chapters(source_path, labels, duration)


def _fmt_dur(seconds: float) -> str:
    """HH:MM:SS ou MM:SS."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build_chapters_rss(chapters: list[dict], ep_url: str, dur_sec: float) -> str:
    """Bloco podcast:chapters (PSRC) + psc:chapters (Podlove)."""
    if not chapters:
        return ""
    psrc_blocks = []
    for ch in chapters:
        start_ms = int(float(ch["start"]) * 1000)
        psrc_blocks.append(
            f'      <psrc:chapter startTime="{start_ms}" '
            f'title="{escape(ch["label"])}"/>'
        )
    psrc_inner = "\n".join(psrc_blocks)
    return f"""\
    <podcast:chapters version="1.2" src="{ep_url}">
      {psrc_inner}
    </podcast:chapters>
    <psc:chapters version="2.0">
      {psrc_inner.replace('psrc:', 'psc:')}
    </psc:chapters>"""


def build_chapters_description(chapters: list[dict], dur_sec: float) -> str:
    """Texto de capítulos para itunes:summary."""
    if not chapters:
        return ""
    lines = []
    for ch in chapters:
        t = _fmt_dur(float(ch["start"]))
        lines.append(f"⏱ {t} — {ch['label']}")
    return "\n".join(lines)
