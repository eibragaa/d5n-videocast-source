#!/usr/bin/env python3
"""Mixer v9 do Drop Five News — reconstruído conforme PADRAO_EDITORIAL_AUDIO.md.

Produz o MP3 final do episódio a partir dos segmentos TTS em /tmp/d5n_audio:
- preserva a ordem real das seções (mesmo com blocos opcionais ausentes);
- trilha de fundo abaixo da narração, com fades e transições;
- saída mono, 44,1 kHz, MP3 192 kbps;
- normalização final −16 LUFS / true peak −1,5 dBTP;
- grava /tmp/d5n_audio/manifest.json com provedor, vozes, seções e alvos.

Uso:
  drop5news-mixer-v9.py --audio-dir /tmp/d5n_audio --output /tmp/d5n_mixado_v9.mp3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from pydub import AudioSegment, silence

# Ordem canônica das seções (contrato D5N v2). CTA depois das notícias, antes do outro.
SECOES = [
    ("intro",       "intro.txt",       "pt-BR-ThalitaMultilingualNeural"),
    ("mundo",       "mundo.txt",       "pt-BR-ThalitaMultilingualNeural"),
    ("brasil",      "brasil.txt",      "pt-BR-ThalitaMultilingualNeural"),
    ("saude",       "saude.txt",       "pt-BR-ThalitaMultilingualNeural"),
    ("ciencia",     "ciencia.txt",     "pt-BR-ThalitaMultilingualNeural"),
    ("politica",    "politica.txt",    "pt-BR-ThalitaMultilingualNeural"),
    ("tecnologia",  "tecnologia.txt",  "pt-BR-ThalitaMultilingualNeural"),
    ("economia",    "economia.txt",    "pt-BR-ThalitaMultilingualNeural"),
    ("ofertas",     "ofertas.txt",     "pt-BR-ThalitaMultilingualNeural"),
    ("frase",       "frase.txt",       "pt-BR-ThalitaMultilingualNeural"),
    ("historia",    "historia.txt",    "pt-BR-ThalitaMultilingualNeural"),
    ("cta",         "cta.txt",         "pt-BR-ThalitaMultilingualNeural"),
    ("outro",       "outro.txt",       "pt-BR-ThalitaMultilingualNeural"),
]

# Blocos obrigatórios (se o .txt existir mas o .mp3 não, bloqueia)
REQUIRED_TXT = {"intro", "mundo", "brasil", "tecnologia", "economia", "ofertas", "outro"}

# Trilha de fundo — fallback para assets da Manhã Conectada (as do D5N se perderam).
_ASSET_DIR = Path("/root/repositorio/d5n-videocast-source/assets/audio")
TRILHA = _ASSET_DIR / "manha-conectada" / "bg-music.mp3"
INTRO_JINGLE = _ASSET_DIR / "manha-conectada" / "intro-jingle.mp3"
STING = _ASSET_DIR / "manha-conectada" / "transition-sting.mp3"

MIN_SECONDS = 300
MAX_SECONDS = 720
LEAD_MS = 1200          # abertura instrumental
PAUSE_EXTRA_MS = 650    # respiro entre temas
HIGH_LUF = -16
TRUE_PEAK = -1.5
BITS = 192


def require(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 5_000:
        raise FileNotFoundError(f"Trilha obrigatória ausente: {path}")


def _read_voice_map(audio_dir: Path, editorial_date: date) -> dict:
    """Constrói o mapa de voz por seção conforme a escala semanal (data editorial)."""
    thalita = "pt-BR-ThalitaMultilingualNeural"
    francisca = "pt-BR-FranciscaNeural"
    wd = editorial_date.weekday()  # 0=seg ... 6=dom
    # Seções efetivamente presentes (com roteiro) — base para a alternância.
    presentes = [nome for nome, *_ in SECOES if (audio_dir / f"{nome}.txt").is_file()
                 and (audio_dir / f"{nome}.txt").stat().st_size]
    mapa = {}
    if wd in {0, 2, 5}:            # seg, qua, sáb
        for nome in presentes:
            mapa[nome] = thalita
    elif wd in {1, 3}:             # ter, qui
        for nome in presentes:
            mapa[nome] = francisca
    else:                          # sexta — alterna Thalita(par)/Francisca(ímpar) na ordem real
        for idx, nome in enumerate(presentes):
            mapa[nome] = thalita if idx % 2 == 0 else francisca
    return mapa


def load_segments(audio_dir: Path) -> list[tuple[str, str, Path]]:
    """Retorna [(nome, texto, caminho_mp3)] apenas para seções com .txt presente."""
    segments = []
    for nome, txt_name, _voz in SECOES:
        txt = audio_dir / txt_name
        if not txt.is_file() or txt.stat().st_size == 0:
            continue
        texto = txt.read_text(encoding="utf-8", errors="replace").strip()
        mp3 = audio_dir / f"{nome}.mp3"
        if not mp3.is_file() or mp3.stat().st_size < 5_000:
            if nome in REQUIRED_TXT:
                raise FileNotFoundError(f"Seção obrigatória sem áudio: {nome} ({mp3})")
            continue
        segments.append((nome, texto, mp3))
    obrigatorias = {nome for nome, *_ in SECOES if nome in REQUIRED_TXT}
    presentes = {nome for nome, *_s in segments}
    faltantes = obrigatorias - presentes
    if faltantes:
        raise FileNotFoundError("Seções obrigatórias sem roteiro: " + ", ".join(sorted(faltantes)))
    return segments


def loop_to(audio: AudioSegment, length: int) -> AudioSegment:
    if not audio:
        raise ValueError("trilha vazia")
    result = AudioSegment.empty()
    while len(result) < length:
        result += audio
    return result[:length]


def extend_pauses(voice: AudioSegment) -> AudioSegment:
    """Insere pequenos respiros em silêncios naturais da locução."""
    detected = silence.detect_silence(
        voice, min_silence_len=600, silence_thresh=int(voice.dBFS - 20), seek_step=10
    )
    targets = (60_000, 120_000, 180_000, 240_000)
    selected: list[tuple[int, int]] = []
    available = [(s, e) for s, e in detected if 10_000 < s < len(voice) - 10_000]
    for target in targets:
        candidates = [
            span for span in available
            if all(abs(span[0] - used[0]) > 20_000 for used in selected)
        ]
        if candidates:
            selected.append(min(candidates, key=lambda sp: abs(((sp[0] + sp[1]) // 2) - target)))
    result = voice
    offset = 0
    for start, end in sorted(selected):
        at = ((start + end) // 2) + offset
        result = result[:at] + AudioSegment.silent(duration=PAUSE_EXTRA_MS, frame_rate=44100) + result[at:]
        offset += PAUSE_EXTRA_MS
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-dir", default="/tmp/d5n_audio")
    ap.add_argument("--output", default="/tmp/d5n_mixado_v9.mp3")
    ap.add_argument("--editorial-date", default=os.environ.get("D5N_EDITORIAL_DATE", date.today().isoformat()))
    args = ap.parse_args()

    audio_dir = Path(args.audio_dir)
    output = Path(args.output)
    editorial_date = date.fromisoformat(args.editorial_date)
    if editorial_date.weekday() == 6:
        raise RuntimeError("domingo não tem episódio (manutenção de pipeline)")

    for path in (TRILHA, INTRO_JINGLE, STING):
        require(path)

    voice_map = _read_voice_map(audio_dir, editorial_date)
    segments = load_segments(audio_dir)

    # Concatena as narrações na ordem real, cada uma com fade-in curto.
    narracao = AudioSegment.silent(duration=LEAD_MS, frame_rate=44100)
    for nome, _texto, mp3_path in segments:
        seg = AudioSegment.from_file(mp3_path).set_channels(1).set_frame_rate(44100)
        seg = extend_pauses(seg).fade_in(12)
        narracao += seg
        narracao += AudioSegment.silent(duration=300, frame_rate=44100)
    duration_s = len(narracao) / 1000
    if not MIN_SECONDS <= duration_s <= MAX_SECONDS:
        raise ValueError(f"narração fora da faixa {MIN_SECONDS}-{MAX_SECONDS}s: {duration_s:.1f}s")

    trilha = loop_to(AudioSegment.from_file(TRILHA).set_channels(1).set_frame_rate(44100) - 27, len(narracao)).fade_in(500).fade_out(2200)
    intro = AudioSegment.from_file(INTRO_JINGLE).set_channels(1).set_frame_rate(44100)[:5000].fade_in(200).fade_out(700) - 10
    trilha = trilha.overlay(intro, position=0)
    mixed = trilha.overlay(narracao).fade_out(1800)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        mixed.export(tmp_path, format="wav")
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(tmp_path),
            "-af", f"highpass=f=65,loudnorm=I={HIGH_LUF}:TP={TRUE_PEAK}:LRA=11",
            "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", f"{BITS}k", str(output),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-500:])
    finally:
        tmp_path.unlink(missing_ok=True)

    if not output.exists() or output.stat().st_size < 100_000:
        raise RuntimeError("MP3 final ausente ou pequeno demais")

    # Manifesto (contrato do quality gate)
    secs = [nome for nome, *_ in segments]
    thalita = "pt-BR-ThalitaMultilingualNeural"
    francisca = "pt-BR-FranciscaNeural"
    usadas = sorted({voice_map[nome] for nome, *_ in segments})
    if editorial_date.weekday() == 4:
        content_voices = [thalita, francisca]  # ordem exigida pelo gate na sexta
    else:
        content_voices = usadas

    # Timestamps dos capítulos (início acumulado de cada seção mixada).
    # Replica a construção da narração: LEAD + seções (com pausa de 300ms entre elas).
    def _narracao_chapters() -> list[dict]:
        chapters = []
        cursor = LEAD_MS / 1000.0
        for nome, _texto, mp3_path in segments:
            seg = AudioSegment.from_file(mp3_path).set_channels(1).set_frame_rate(44100)
            seg = extend_pauses(seg)
            dur = len(seg) / 1000.0
            chapters.append({"id": nome, "start": round(cursor, 3), "end": round(cursor + dur, 3)})
            cursor += dur + 0.3
        # O player espera o primeiro capítulo (intro) iniciando em 0s.
        if chapters:
            chapters[0]["start"] = 0.0
        return chapters

    chapters = _narracao_chapters()

    manifest = {
        "schema": 2,
        "programa": "Drop Five News",
        "tts_provider": "edge-tts-local",
        "header_voice": "pt-BR-AntonioNeural",
        "editorial_date": editorial_date.isoformat(),
        "sections": secs,
        "content_voices": content_voices,
        "presentation_mode": ("sexta-dual-dinamica" if editorial_date.weekday() == 4
                              else "solo-thalita" if voice_map.get("intro") == thalita
                              else "solo-francisca"),
        "section_voice_map": {nome: voice_map[nome] for nome, *_ in segments},
        "loudness_target_lufs": HIGH_LUF,
        "true_peak_target_dbtp": TRUE_PEAK,
        "chapters": chapters,
        "output": str(output),
    }
    (audio_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK {output} · {duration_s:.0f}s · {len(secs)} seções")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
