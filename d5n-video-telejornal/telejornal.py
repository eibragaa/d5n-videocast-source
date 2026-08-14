#!/usr/bin/env python3
"""
telejornal.py — pipeline de vídeo estilo telejornal a partir de narração.

narração -> segmentos por frase (SentenceBoundary do Edge TTS) -> .ass legendas
-> fundo (gradiente temático OU stock video Pexels) -> ffmpeg (bg + legendas
+ cabeçalho/rodapé + áudio) -> MP4 9:16.

100% local no modo fallback (sem chave). Pexels ativa com PEXELS_API_KEY.
Sem ASR local: usa timing do próprio Edge TTS (não precisa de Whisper; esta CPU
sem AVX2 não roda ctranslate2/whisper — SIGILL).
"""
import argparse, asyncio, json, os, re, subprocess, tempfile, urllib.request, urllib.parse, urllib.error
from pathlib import Path

V = "pt-BR-ThalitaMultilingualNeural"
W, H = 720, 1280  # 9:16
STOP = set("de da do das o os a as e em para por com que no na num uma é são foi sobre mais ao à seu sua os as se um uma isso esta".split())

def heuristic_keywords(text):
    """Fallback: palavras de conteudo (>=4 letras, sem stopwords) em PT."""
    words = re.findall(r"\b\w{4,}\b", text.lower())
    content = [w for w in words if w not in STOP]
    return ", ".join(content[:3]) or "technology"

def llm_keywords(texts):
    """Keywords EN por frase via DeepSeek (OpenAI-compatible). Fallback: heuristic."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return [heuristic_keywords(t) for t in texts]
    try:
        lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        prompt = ("Para cada frase numerada abaixo, devolva UMA linha com EXATAMENTE 3 keywords "
                  "curtas em ingles, separadas por virgula, SEM numeracao e SEM explicacao, para buscar "
                  "video de stock (sujeito + acao; ex: 'artificial intelligence robot, future technology').\n"
                  + lines)
        body = json.dumps({"model": "deepseek-chat",
                           "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 160, "temperature": 0}).encode()
        req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                     headers={"Authorization": f"Bearer {key}",
                                              "Content-Type": "application/json",
                                              "User-Agent": "Mozilla/5.0 (d5n-telejornal)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        content = d["choices"][0]["message"]["content"]
        out = []
        for ln in content.splitlines():
            ln = re.sub(r"^\s*\d+[.)]?\s*", "", ln).strip()
            if ln:
                kws = [k.strip() for k in ln.split(",") if k.strip()]
                out.append(", ".join(kws[:3]))
        if len(out) == len(texts) and all(out):
            return out
    except Exception as e:
        print("[w] DeepSeek keywords falhou, usando heurística:", e)
    return [heuristic_keywords(t) for t in texts]

def p_src(t):
    # escapa caracteres especiais p/ dentro do filtergraph do ffmpeg (sem parênteses)
    return t.replace("\\", "\\\\").replace(":", "\\:").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")

async def synthesize(text, voice, rate, out_wav):
    """Gera áudio e devolve segmentos [(start_s, end_s, text)] via SentenceBoundary."""
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate)
    segs = []
    pending = []
    async for m in c.stream():
        if m["type"] == "SentenceBoundary":
            off = m["offset"] / 1e7; dur = m["duration"] / 1e7
            segs.append((off, off + dur, m["text"]))
        elif m["type"] == "audio":
            pending.append(m["data"])
    # escrever wav (pcm) — edge-tts entrega mp3 chunks; montamos mp3 p/ ffmpeg
    Path(out_wav).write_bytes(b"".join(pending))
    return segs

def build_ass(segs):
    """Converte segmentos em .ass (legenda baixa, quebra automática por libass)
    + cabeçalho/rodapé persistentes estilo telejornal."""
    total = max(b for _, b, _ in segs) + 0.3 if segs else 30
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Leg, Arial, 30, &H00F5F7F2, &H00FFFFFF, &H00160F0B, &H80000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 3, 0, 2, 40, 40, 260, 1
Style: Tag, Arial, 22, &H0072F6C5, &H00FFFFFF, &H00160F0B, &H80000000, 1, 0, 0, 0, 100, 100, 2, 0, 1, 2, 0, 7, 30, 30, 40, 1
Style: Foot, Arial, 19, &H00A8B3AE, &H00FFFFFF, &H00160F0B, &H80000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 2, 0, 2, 30, 30, 52, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def ts(s):
        h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
        return f"{h}:{m:02d}:{sec:05.2f}"
    lines = [
        f"Dialogue: 0,0:00:00.00,{ts(total)},Tag,,0,0,0,,NOTÍCIAS  ·  IA",
        f"Dialogue: 0,0:00:00.00,{ts(total)},Foot,,0,0,0,,@jeanbraga.ia   ·   SIGA",
    ]
    for i, (a, b, txt) in enumerate(segs):
        t = re.sub(r"\s+", " ", txt).strip()
        words = t.split()
        wrapped = []
        for j in range(0, len(words), 6):
            wrapped.append(" ".join(words[j:j + 6]))
        body = "\\N".join(wrapped)
        lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},Leg,,0,0,0,,{body}")
    return header + "\n".join(lines) + "\n"

def pexels_video(keyword, per=3):
    """Retorna 1ª URL de video 9:16 do Pexels p/ a keyword (None se falhar)."""
    q = urllib.parse.urlencode({"query": keyword, "per_page": per, "orientation": "portrait", "size": "small"})
    req = urllib.request.Request(f"https://api.pexels.com/videos/search?{q}",
                                 headers={"Authorization": os.environ["PEXELS_API_KEY"],
                                          "User-Agent": "Mozilla/5.0 (jeanbraga-telejornal)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    for v in d.get("videos", []):
        for f in v.get("video_files", []):
            if f.get("width", 0) <= 720 and f.get("file_type") in ("video/mp4", "video/webm"):
                return f["link"]
    return None

def build_video(segs, audio, out, ass, key, music, logo, dur_audio):
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats"]
    inputs = ["-i", os.path.abspath(audio)]
    vf = None
    if key:
        kw = llm_keywords([t for _, _, t in segs]) if key else None
        clips = []
        for i, (a, b, txt) in enumerate(segs):
            search = kw[i] if kw else heuristic_keywords(txt)
            url = pexels_video(search)
            d = b - a
            fp = None
            if url:
                fp = f"/tmp/tj_{int(a*100)}.mp4"
                subprocess.run(["curl", "-sL", "-o", fp, url], check=False)
                if not (os.path.exists(fp) and os.path.getsize(fp) > 10000):
                    fp = None
            if not fp:
                fp = f"/tmp/tj_grad_{int(a*100)}.mp4"
                _gradient(fp, d)
            clips.append((fp, d))
        filt = []
        for i, (fp, d) in enumerate(clips):
            inputs += ["-i", fp]
            filt.append(f"[{i+1}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,trim=duration={d:.2f},setpts=PTS-STARTPTS[v{i}]")
        concat = "".join(f"[v{i}]" for i in range(len(clips)))
        filt.append(f"{concat}concat=n={len(clips)}:v=1:a=0,ass={p_src(ass)},format=yuv420p,eq=brightness=-0.06:saturation=0.85[vout]")
        fc = ";".join(filt)
    else:
        bg = "/tmp/tj_bg.mp4"
        _gradient(bg, dur_audio)
        inputs += ["-i", bg]
        fc = None
        vf = f"ass={p_src(ass)},format=yuv420p,eq=brightness=-0.06:saturation=0.85"

    cmd += inputs
    if fc:
        cmd += ["-filter_complex", fc, "-map", "[vout]", "-map", "0:a"]
    else:
        cmd += ["-map", "1:v", "-map", "0:a"]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-af", "afade=t=in:st=0:d=0.5", "-movflags", "+faststart", out]
    print("ffmpeg:", " ".join(cmd[:18]), "...")
    subprocess.run(cmd, check=True)

def _gradient(out, dur):
    # gradiente obsidiana animado sutil (speed baixo) — barato p/ CPU
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i",
                    f"gradients=s={W}x{H}:c0=0x0d1211:c1=0x050707:x0=0:y0=0:x1={W}:y1={H}:speed=0.04:nb_colors=2",
                    "-t", f"{dur:.2f}", "-r", "30", "-pix_fmt", "yuv420p", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "24", out], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="texto da narração (ou --audio para áudio já pronto)")
    ap.add_argument("--audio", help="mp3 pronto (usará este áudio; timing por frase precisa do texto)")
    ap.add_argument("--voice", default=V)
    ap.add_argument("--rate", default="+12%")
    ap.add_argument("--out", default="telejornal.mp4")
    ap.add_argument("--music")
    ap.add_argument("--logo")
    ap.add_argument("--no-ass", action="store_true")
    a = ap.parse_args()

    if not a.text and not a.audio:
        ap.error("passe --text ou --audio")
    key = os.environ.get("PEXELS_API_KEY")
    if key:
        print("[i] Pexels key detectada -> modo stock videos")
    else:
        print("[i] Sem Pexels key -> modo fallback (gradiente temático)")

    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "nar.mp3")
        if a.text:
            segs = asyncio.run(synthesize(a.text, a.voice, a.rate, wav))
            if not segs:
                print("[x] nenhuma SentenceBoundary retornada"); return 1
            dur = max(b for _, b, _ in segs) + 0.3
            audio = wav
        else:
            audio = a.audio
            dur = float(subprocess.check_output(["ffprobe", "-v", "error",
                    "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", a.audio]).strip())
            # sem timing: segmento único = narração toda
            segs = [(0.0, dur, "Notícias IA")]
        ass = os.path.join(td, "leg.ass")
        Path(ass).write_text(build_ass(segs), encoding="utf-8")
        build_video(segs, audio, a.out, ass, key, a.music, a.logo, dur)
        print("OK ->", a.out)

if __name__ == "__main__":
    raise SystemExit(main())
