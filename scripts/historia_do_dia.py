#!/usr/bin/env python3
"""Historia do dia: um fato real que aconteceu NESTE dia do calendario.

Padrao de referencia (TecMundo, 07/10/2026, 14:05):
    "E nao aconteceu na historia da tecnologia. 7 de outubro de 1959. A sonda
     sovietica Luna 3 fotografa pela primeira vez o lado oculto da lua..."

A mecanica e a DATA, nao o tema: o fato tem que ter ocorrido em (dia, mes) de
algum ano. Um banco curado em vez de web porque:
  - a dataeditorial e fixa por episodio (07/10 usa sempre o entry de 7 de outubro);
  - o arquivo e versionado e revisto: um fato errado no banco e reaproveitado
    todo dia do mes, e nao da para deixar um LLM inventar citacao.

Verificacao: cada entrada declara `fonte` (Wikidata/Wikipedia). O
`verificar_historia.py` confere que o QID existe na Wikidata e que a data do
fato (P585) bate com (dia, mes) da entrada.
"""
import json
from pathlib import Path

BANCO = Path(__file__).resolve().parent.parent / "assets" / "historia-das-datas.json"

# Datas sem fato tecnologico notavel conhecido com confianca. Nesses dias o
# gerador NAO inventa: cai no texto de reserva e o quality gate barra o episodio
# para revisao humana. Melhor falhar alto que publicar historia falsa.
SEM_FATO = {1, 2, 31}


def carregar() -> dict:
    if not BANCO.exists():
        return {}
    return json.loads(BANCO.read_text(encoding="utf-8"))


def entrada_para(dia: int, mes: int) -> dict | None:
    """Retorna o fato registrado para (dia, mes) ou None."""
    b = carregar()
    return b.get(f"{dia:02d}-{mes:02d}")


def dias_cobertos() -> set:
    return {int(k.split("-")[0]) for k in carregar()}