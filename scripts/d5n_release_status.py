#!/usr/bin/env python3
"""Verifica se o episódio de uma data foi publicado de forma íntegra.

O recibo é criado somente depois de um push Git bem-sucedido. O status também
confere o hash do áudio e a entrada correspondente no contador para tornar os
retries idempotentes e detectar artefatos alterados depois da publicação.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_REPO = Path("/root/repositorio/d5n-videocast-source")
DEFAULT_STATE_DIR = Path("/root/.hermes/logs/d5n-deploy")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _result(editorial_date: str, published: bool, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "editorial_date": editorial_date,
        "published": published,
        "reason": reason,
        **extra,
    }


def release_status(repo: Path, state_dir: Path, editorial_date: str) -> dict[str, Any]:
    repo = repo.resolve()
    state_dir = state_dir.resolve()

    if not DATE_RE.fullmatch(editorial_date):
        return _result(editorial_date, False, "invalid_date")

    receipt_path = state_dir / f"published-{editorial_date}.json"
    if not receipt_path.is_file():
        return _result(editorial_date, False, "missing_receipt")

    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _result(editorial_date, False, "invalid_receipt")

    if receipt.get("editorial_date") != editorial_date:
        return _result(editorial_date, False, "receipt_date_mismatch")

    episode = str(receipt.get("episode", ""))
    audio_value = receipt.get("audio")
    digest_expected = str(receipt.get("sha256", ""))
    commit = str(receipt.get("commit", ""))
    if not re.fullmatch(r"\d{3}", episode):
        return _result(editorial_date, False, "invalid_episode")
    if not isinstance(audio_value, str) or not audio_value:
        return _result(editorial_date, False, "invalid_audio_path")
    if not re.fullmatch(r"[0-9a-f]{64}", digest_expected):
        return _result(editorial_date, False, "invalid_audio_sha256")
    if not COMMIT_RE.fullmatch(commit):
        return _result(editorial_date, False, "invalid_commit")

    audio_rel = Path(audio_value)
    if audio_rel.is_absolute():
        return _result(editorial_date, False, "invalid_audio_path")
    audio_path = (repo / audio_rel).resolve()
    try:
        audio_path.relative_to(repo)
    except ValueError:
        return _result(editorial_date, False, "invalid_audio_path")
    if not audio_path.is_file():
        return _result(editorial_date, False, "missing_audio")

    digest_actual = hashlib.sha256(audio_path.read_bytes()).hexdigest()
    if digest_actual != digest_expected:
        return _result(editorial_date, False, "audio_sha256_mismatch")

    counter_path = repo / "episode-counter.json"
    try:
        counter = json.loads(counter_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _result(editorial_date, False, "invalid_counter")

    expected_file = audio_path.name
    matching = [
        item
        for item in counter.get("history", [])
        if str(item.get("num", "")) == episode
        and item.get("date") == editorial_date
        and item.get("file") == expected_file
        and item.get("exists") is True
    ]
    if not matching:
        return _result(editorial_date, False, "counter_missing_episode")

    return _result(
        editorial_date,
        True,
        "published",
        episode=episode,
        audio=str(audio_rel),
        sha256=digest_actual,
        commit=commit,
        receipt=str(receipt_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument(
        "--date",
        default=datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat(),
    )
    args = parser.parse_args()

    result = release_status(args.repo, args.state_dir, args.date)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["published"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
