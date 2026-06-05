#!/usr/bin/env python3
"""
validate_mp3.py — Validação multi-camada de MP3 para o site D5N.

Uso:  validate_mp3.py <caminho_do_mp3>

Saída (exit code):
  0 → VÁLIDO — é um episódio do Drop Five News
  1 → INVÁLIDO — stdout explica o motivo
  2 → ERRO — não foi possível analisar o arquivo

Camadas de validação (ordem crescente de custo):
  1. Nome do arquivo — precisa começar com "d5n-podcast-"
  2. Tamanho mínimo — > 5MB (corujão tem ~500KB)
  3. Duração mínima — > 3 minutos (corujão tem ~70s)
  4. Integridade — não é um arquivo vazio/null
  5. Header MP3 — primeiros bytes confirmam áudio válido
"""

import os, sys, struct, json

MIN_SIZE_BYTES = 5_000_000      # 5MB
MIN_DURATION_SEC = 180          # 3 minutos
VALID_PREFIXES = ("d5n-podcast-",)

def check_name(path):
    fname = os.path.basename(path)
    ok = any(fname.startswith(p) for p in VALID_PREFIXES)
    if not ok:
        print(f"INVÁLIDO — nome '{fname}' não começa com prefixo válido {VALID_PREFIXES}")
        return False
    return True

def check_size(path):
    size = os.path.getsize(path)
    if size < MIN_SIZE_BYTES:
        print(f"INVÁLIDO — tamanho {size:,} bytes < mínimo {MIN_SIZE_BYTES:,} bytes (muito pequeno)")
        return False
    return True

def check_duration(path):
    """Usa ffprobe para obter duração."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            print(f"ERRO — ffprobe falhou: {r.stderr.strip()}")
            return None
        dur = float(r.stdout.strip())
        if dur < MIN_DURATION_SEC:
            print(f"INVÁLIDO — duração {dur:.1f}s < mínimo {MIN_DURATION_SEC}s")
            return False
        return True
    except Exception as e:
        print(f"ERRO — ffprobe exception: {e}")
        return None

def check_integrity(path):
    """Verifica que o MP3 não é um arquivo vazio ou corrompido."""
    with open(path, "rb") as f:
        header = f.read(4)
    if len(header) < 4:
        print(f"INVÁLIDO — arquivo com menos de 4 bytes (vazio)")
        return False
    # MP3 frames começam com 0xFF (sync word) ou 0x49 ('ID3' tag)
    if header[:3] == b'ID3' or header[0] == 0xFF:
        return True
    # Verifica se é todo null bytes (falso positivo do ffprobe)
    with open(path, "rb") as f:
        sample = f.read(1024)
    if all(b == 0 for b in sample):
        print(f"INVÁLIDO — arquivo contém apenas null bytes (corrompido)")
        return False
    print(f"INVÁLIDO — header não reconhecido: {header.hex()}")
    return False

def main():
    if len(sys.argv) < 2:
        print("Uso: validate_mp3.py <caminho_do_mp3>")
        sys.exit(2)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"ERRO — arquivo não encontrado: {path}")
        sys.exit(2)

    # Camada 1: Nome
    if not check_name(path):
        sys.exit(1)

    # Camada 2: Tamanho
    if not check_size(path):
        sys.exit(1)

    # Camada 3: Integridade (rápido — só lê 1KB)
    integrity_ok = check_integrity(path)
    if integrity_ok is False:
        sys.exit(1)
    if integrity_ok is None:
        sys.exit(2)

    # Camada 4: Duração (mais caro — ffprobe)
    dur_ok = check_duration(path)
    if dur_ok is False:
        sys.exit(1)
    if dur_ok is None:
        sys.exit(2)

    # Todas as camadas passaram
    size = os.path.getsize(path)
    print(f"VÁLIDO — {os.path.basename(path)} ({size:,} bytes)")
    sys.exit(0)

if __name__ == "__main__":
    main()
