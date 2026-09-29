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


def chapters_from_manifest(derived: list[dict], manifest_path: Path) -> list[dict]:
    """Usa os timings reais do manifesto, se existirem, mantendo os rótulos.

    O manifesto do mixer tem os tempos exatos de cada bloco (medidos do MP3),
    mas só o id — o rótulo editorial vem da derivação sobre o coldopen. O
    podcast:chapters apontava para o manifesto enquanto o psc:chapters inline
    saía sem `start`, porque `psc:chapter` exige start. Rótulo sem tempo não
    navega: o player ignora ou joga o ouvinte no lugar errado.

    Se os dois conjuntos tiverem o mesmo tamanho, casa por posição. Com
    quantidades diferentes, mantém a derivação: sincronizar 11 blocos reais
    com 6 rótulos por índice inventaria capítulos.
    """
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return derived
    real = data.get("chapters") or []
    if not real or not derived or len(real) != len(derived):
        return derived
    merged = []
    for index, chapter in enumerate(derived):
        merged.append({
            "id": chapter["id"],
            "label": chapter["label"],
            "start": float(real[index].get("start", chapter.get("start", 0.0))),
            "end": float(real[index].get("end", chapter.get("end", 0.0))),
        })
    return merged


def _fmt_dur(seconds: float) -> str:
    """HH:MM:SS ou MM:SS."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build_chapters_rss(chapters: list[dict], chapters_url: str, dur_sec: float, has_timing: bool = True) -> str:
    """podcast:chapters (só src) + psc:chapters (capítulos inline).

    O podcast:chapters do padrão Podcasting 2.0 leva APENAS o src, apontando
    para o documento de capítulos. Filhos só existem quando o src é o próprio
    MP3 com atoms ID3 CHAP/ctoc — nunca é o nosso caso. Emitir psrc:chapter ou
    psc:chapter dentro de podcast:chapters mistura namespaces e reprova em
    leitor estrito.

    Os capítulos que os players leem vão no psc:chapters (Podlove).

    has_timing=False: D5N coldopen.txt não tem timing real — omite startTime
    para não mostrar timestamps falsos nos players.
    """
    if not chapters:
        return ""
    if has_timing:
        inner = "\n".join(
            f'      <psc:chapter start="{_fmt_dur(float(ch["start"]))}" '
            f'title="{escape(ch["label"])}"/>'
            for ch in chapters
        )
    else:
        # Sem timing real: so o rotulo. Timestamp inventado e pior que nenhum —
        # o player pula para o ponto errado e o ouvinte perde o trecho.
        inner = "\n".join(
            f'      <psc:chapter title="{escape(ch["label"])}"/>'
            for ch in chapters
        )
    return f"""\
    <podcast:chapters version="1.2" src="{chapters_url}"/>
    <psc:chapters version="2.0">
{inner}
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
