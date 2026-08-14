#!/usr/bin/env python3
"""Gate diário bloqueante do D5N antes de copiar áudio ou publicar o site."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, time
from difflib import SequenceMatcher
from pathlib import Path

PILLARS = ("GLOBAL", "BRASIL", "TECH", "ECONOMIA")
SECTION_ORDER = (
    "coldopen", "intro", "mundo", "brasil", "tecnologia", "economia",
    "interacao", "ofertas", "frase", "recomendacoes", "historia", "outro",
)
REQUIRED_SECTIONS = {"coldopen", "intro", "mundo", "brasil", "tecnologia", "economia", "outro"}
MIN_SECTIONS = 8
MIN_WORDS = 1100
MAX_WORDS = 1900
MIN_DURATION = 480.0
MAX_DURATION = 720.0

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


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())


def _date_phrase(editorial_date: date) -> str:
    return f"{editorial_date.day} de {MONTHS_PT[editorial_date.month]} de {editorial_date.year}"


def _without_date(text: str) -> str:
    folded = _fold(text)
    folded = re.sub(
        r"\b(?:segunda-feira|terca-feira|quarta-feira|quinta-feira|sexta-feira|sabado|domingo),?\s*",
        "", folded,
    )
    folded = re.sub(r"\b\d{1,2} de [a-z]+ de \d{4}\b", "", folded)
    return " ".join(folded.split())


def _opening_formula(text: str) -> str:
    """Resume a arquitetura inicial, ignorando data e nome da apresentadora."""
    normalized = _without_date(text)
    normalized = re.sub(r"\b(?:thalita|francisca)\b", "", normalized)
    words = re.findall(r"[a-z0-9]+", normalized)
    return " ".join(words[:10])


def _spoken_body(text: str) -> str:
    """Remove o cabeçalho técnico Programa/Data/Voz antes de validar a fala."""
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return text.strip()
    first = _fold(lines[0])
    second = _fold(lines[1])
    if not first.startswith("drop five news") or not second.startswith("data:"):
        return text.strip()
    index = 2
    if index < len(lines) and _fold(lines[index]).startswith("voz:"):
        index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    return "\n".join(lines[index:]).strip()


def validate_trends(path: Path) -> list[str]:
    if not path.is_file():
        return [f"trends ausente: {path}"]
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = "".join(
        c for c in unicodedata.normalize("NFD", raw.upper())
        if unicodedata.category(c) != "Mn"
    )
    errors = []
    if path.stat().st_size < 100:
        errors.append(f"trends pequeno demais: {path}")
    headings = set(
        re.findall(r"(?m)^===\s*(GLOBAL|BRASIL|TECH|ECONOMIA)\s*===\s*$", text)
    )
    for pillar in PILLARS:
        if pillar not in headings:
            errors.append(f"trends sem pilar {pillar}")
    return errors


def validate_audio_metadata(metadata: dict) -> list[str]:
    errors = []
    duration = float(metadata.get("duration", 0) or 0)
    bitrate = int(metadata.get("bit_rate", 0) or 0)
    sample_rate = int(metadata.get("sample_rate", 0) or 0)
    if not MIN_DURATION <= duration <= MAX_DURATION:
        errors.append(
            f"duração deve ficar entre {MIN_DURATION:.0f} e {MAX_DURATION:.0f} segundos; "
            f"recebida {duration:.2f}s"
        )
    if bitrate < 128_000:
        errors.append(f"bitrate abaixo de 128 kbps: {bitrate}")
    if metadata.get("codec_name") != "mp3":
        errors.append(f"codec deve ser mp3: {metadata.get('codec_name')!r}")
    if sample_rate != 44_100:
        errors.append(f"sample rate deve ser 44100 Hz: {sample_rate}")
    return errors


def probe_audio(path: Path) -> tuple[dict, list[str]]:
    if not path.is_file() or path.stat().st_size < 100_000:
        return {}, [f"MP3 ausente ou pequeno: {path}"]
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,bit_rate:stream=codec_name,sample_rate,channels",
        "-of", "json", str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        return {}, [f"ffprobe falhou: {result.stderr.strip()}"]
    payload = json.loads(result.stdout)
    stream = (payload.get("streams") or [{}])[0]
    fmt = payload.get("format") or {}
    metadata = {
        "duration": float(fmt.get("duration", 0) or 0),
        "bit_rate": int(fmt.get("bit_rate", 0) or 0),
        "codec_name": stream.get("codec_name"),
        "sample_rate": int(stream.get("sample_rate", 0) or 0),
        "channels": int(stream.get("channels", 0) or 0),
    }
    return metadata, validate_audio_metadata(metadata)


def _recent_snapshots(history_dir: Path, editorial_date: date) -> list[dict]:
    snapshots = []
    if not history_dir.is_dir():
        return snapshots
    for path in sorted(history_dir.glob("*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            snapshot_date = date.fromisoformat(payload["date"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if snapshot_date < editorial_date:
            snapshots.append(payload)
        if len(snapshots) == 7:
            break
    return snapshots


def validate_script(audio_dir: Path, editorial_date: date, history_dir: Path) -> tuple[list[str], dict]:
    segments = {}
    for name in SECTION_ORDER:
        path = audio_dir / f"{name}.txt"
        if path.is_file() and path.stat().st_size:
            segments[name] = path.read_text(encoding="utf-8", errors="replace").strip()

    errors = []
    if len(segments) < MIN_SECTIONS:
        errors.append(f"roteiro precisa de pelo menos {MIN_SECTIONS} seções; encontradas {len(segments)}")
    missing = sorted(REQUIRED_SECTIONS - set(segments))
    if missing:
        errors.append("seções essenciais ausentes: " + ", ".join(missing))

    spoken_segments = {name: _spoken_body(text) for name, text in segments.items()}
    intro = spoken_segments.get("intro", "")
    outro = spoken_segments.get("outro", "")
    expected_date = _fold(_date_phrase(editorial_date))
    expected_weekday = _fold(WEEKDAYS_PT[editorial_date.weekday()])
    folded_intro = _fold(intro)
    if expected_date not in folded_intro or expected_weekday not in folded_intro:
        errors.append(
            f"intro sem data editorial completa: {WEEKDAYS_PT[editorial_date.weekday()]}, {_date_phrase(editorial_date)}"
        )
    if not re.match(r"^bom dia\b", folded_intro):
        errors.append("intro deve começar com 'Bom dia!'")
    if not re.search(r"\bbom dia[!.]?\s*$", _fold(outro)):
        errors.append("encerramento deve terminar com 'Bom dia!'")

    all_text = "\n".join(spoken_segments.values())
    word_count = len(re.findall(r"\b[\wÀ-ÿ]+\b", all_text))
    if not MIN_WORDS <= word_count <= MAX_WORDS:
        errors.append(f"roteiro deve ter {MIN_WORDS}–{MAX_WORDS} palavras; recebeu {word_count}")
    folded_all = _fold(all_text)
    for phrase in BANNED_PHRASES:
        if _fold(phrase) in folded_all:
            errors.append(f"clichê proibido no roteiro: {phrase!r}")

    current_opening = _without_date(intro)
    current_opening_formula = _opening_formula(intro)
    current_outro = _without_date(outro)
    for previous in _recent_snapshots(history_dir, editorial_date):
        old_segments = previous.get("segments") or {}
        old_intro = str(old_segments.get("intro", ""))
        for label, current, old in (
            ("abertura", current_opening, _without_date(old_intro)),
            ("encerramento", current_outro, _without_date(str(old_segments.get("outro", "")))),
        ):
            if len(current) >= 40 and len(old) >= 40:
                similarity = SequenceMatcher(None, current, old).ratio()
                if similarity >= 0.86:
                    errors.append(
                        f"{label} repete roteiro de {previous.get('date')} ({similarity:.0%} de similaridade)"
                    )
        previous_formula = _opening_formula(old_intro)
        if (
            len(current_opening_formula.split()) >= 8
            and current_opening_formula == previous_formula
        ):
            errors.append(
                f"fórmula de abertura repete {previous.get('date')}: {current_opening_formula!r}"
            )

    snapshot = {
        "date": editorial_date.isoformat(),
        "word_count": word_count,
        "sections": list(segments),
        "segments": spoken_segments,
    }
    return errors, snapshot


def validate_manifest(path: Path, editorial_date: date) -> list[str]:
    if not path.is_file():
        return [f"manifesto ausente: {path}"]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"manifesto inválido: {exc}"]
    errors = []
    if manifest.get("editorial_date") != editorial_date.isoformat():
        errors.append(f"manifesto com data editorial incorreta; esperado {editorial_date.isoformat()}")
    sections = manifest.get("sections")
    if not isinstance(sections, list) or len(sections) < MIN_SECTIONS:
        errors.append(f"manifesto precisa registrar pelo menos {MIN_SECTIONS} seções")
    elif not REQUIRED_SECTIONS.issubset(set(sections)):
        errors.append("manifesto não registra todas as seções essenciais")
    else:
        expected_order = [name for name in SECTION_ORDER if name in sections]
        known_order = [name for name in sections if name in SECTION_ORDER]
        if known_order != expected_order or len(known_order) != len(sections):
            errors.append("ordem das seções no manifesto não segue o contrato D5N v3")
    voice_map = manifest.get("section_voice_map")
    if isinstance(sections, list) and (
        not isinstance(voice_map, dict) or not set(sections).issubset(voice_map)
    ):
        errors.append("manifesto sem mapa de voz para todas as seções")
    return errors


def _default_audio(editorial_date: date) -> Path:
    name = f"d5n-podcast-{editorial_date.isoformat()}.mp3"
    candidates = (
        Path("/root/.hermes/cron/output") / name,
        Path("/root/.hermes/profiles/d5n/cron/output") / name,
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--trends")
    parser.add_argument("--audio")
    parser.add_argument("--audio-dir", default="/tmp/d5n_audio")
    parser.add_argument("--history-dir", default="podcast-scripts")
    parser.add_argument("--manifest")
    parser.add_argument("--write-snapshot", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    editorial_date = date.fromisoformat(args.date)
    repo = Path(__file__).resolve().parents[1]
    trends = Path(args.trends) if args.trends else Path(f"/root/.hermes/cron/output/drop5news-trends-{args.date}.txt")
    if not trends.is_file():
        alternate = repo / f"drop5news-trends-{args.date}.txt"
        if alternate.is_file():
            trends = alternate
    audio = Path(args.audio) if args.audio else _default_audio(editorial_date)
    audio_dir = Path(args.audio_dir)
    history_dir = Path(args.history_dir)
    manifest = Path(args.manifest) if args.manifest else audio_dir / "manifest.json"

    errors = []
    errors.extend(validate_trends(trends))
    script_errors, snapshot = validate_script(audio_dir, editorial_date, history_dir)
    errors.extend(script_errors)
    errors.extend(validate_manifest(manifest, editorial_date))
    metadata, audio_errors = probe_audio(audio)
    errors.extend(audio_errors)
    if audio.is_file():
        day_start = datetime.combine(editorial_date, time.min).timestamp()
        if audio.stat().st_mtime < day_start:
            errors.append(f"MP3 é anterior à data editorial: {audio}")

    report = {
        "ok": not errors,
        "date": editorial_date.isoformat(),
        "trends": str(trends),
        "audio": str(audio),
        "audio_metadata": metadata,
        "script": {"word_count": snapshot["word_count"], "sections": snapshot["sections"]},
        "errors": errors,
    }
    if not errors and args.write_snapshot:
        history_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = history_dir / f"{editorial_date.isoformat()}.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["snapshot"] = str(snapshot_path)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif errors:
        print("BLOQUEADO: episódio diário fora do padrão")
        for error in errors:
            print(f"- {error}")
    else:
        print(
            f"OK: {editorial_date.isoformat()} · {snapshot['word_count']} palavras · "
            f"{len(snapshot['sections'])} seções · {metadata.get('duration', 0):.1f}s"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
