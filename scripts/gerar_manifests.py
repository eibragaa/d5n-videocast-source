#!/usr/bin/env python3
"""
gerar_manifests.py — Gera manifests vazios para um dia específico do programa D5N.
Uso: python3 gerar_manifests.py --data 2026-09-19
      python3 gerar_manifests.py --data 2026-09-19 --program d5n
"""

import argparse
import os
from datetime import datetime

MANIFESTS_DIR = "/root/repositorio/d5n-videocast-source/manifests"

# Seções padrão do D5N (12 seções do mixer v10)
SECCOES_D5N = [
    "coldopen", "intro", "mundo", "brasil", "tecnologia",
    "economia", "interacao", "ofertas", "frase", "recomendacoes",
    "historia", "outro"
]

SECCOES_MC = [
    "intro", "mundo", "brasil", "tecnologia",
    "economia", "interacao", "ofertas", "frase", "recomendacoes",
    "historia", "outro"
]

SECCOES_FM = [
    "intro", "mercado", "analise", "detalhes", "frase", "outro"
]

PROGRAMAS = {
    "d5n": SECCOES_D5N,
    "mc": SECCOES_MC,
    "fm": SECCOES_FM,
}

def gerar(data: str, programa: str = "d5n"):
    if programa not in PROGRAMAS:
        print(f"Programa desconhecido: {programa}. Escolha: {list(PROGRAMAS.keys())}")
        return False

    secoes = PROGRAMAS[programa]
    target_dir = os.path.join(MANIFESTS_DIR, programa, data)

    os.makedirs(target_dir, exist_ok=True)

    gerados = []
    for secao in secoes:
        path = os.path.join(target_dir, f"{secao}.txt")
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(f"# {secao.upper()} — {data}\n")
                f.write(f"# Programa: {programa.upper()}\n")
                f.write(f"# Gerado automaticamente em {datetime.now().isoformat()}\n")
                f.write(f"# Editar este arquivo para customizar o conteúdo da seção.\n\n")
            gerados.append(secao)

    if gerados:
        print(f"✔ {len(gerados)} manifests gerados em {target_dir}:")
        for s in gerados:
            print(f"   - {s}.txt")
    else:
        print(f"⚠ Nenhum manifest novo gerado (todos já existiam em {target_dir})")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera manifests para o programa D5N")
    parser.add_argument("--data", required=True, help="Data no formato YYYY-MM-DD")
    parser.add_argument("--programa", default="d5n", choices=list(PROGRAMAS.keys()),
                        help="Programa: d5n, mc, fm (default: d5n)")
    args = parser.parse_args()

    sucesso = gerar(args.data, args.programa)
    exit(0 if sucesso else 1)
