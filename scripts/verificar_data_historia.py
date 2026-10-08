#!/usr/bin/env python3
"""Data de ocorrência de um evento, lida da Wikipédia (pt) e conferida.

Por que Wikipédia e não Wikidata: testei os itens de Luna 3 (Q942814), Sputnik I
(Q80811) e Explorer I (Q49901) e NENHUM tem P585/P571 — a Wikidata guarda
metadados de infraestrutura (identificadores externos), nao a data em que o
fato aconteceu. Qualquer gerador que dependesse de P585 publicaria "sem data".

A Wikipédia traz a data no infobox e no primeiro paragrafo. Este script:
  1. baixa o wikitext da versao em portugues;
  2. extrai a data do infobox (|data=) e/ou do primeiro paragrafo;
  3. compara com (dia, mes) esperado e devolve VERDICT.

Ele NAO decide o que e interessante — isso e do banco curado. Ele so impede
que um dia entre com a data errada: e a verificacao que o Jean pediu.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

UA = {"User-Agent": "d5n-historia/1.0 (podcast D5N)"}
CACHE = Path.home() / ".cache" / "d5n" / "wikipedia-datas.json"
MESES_PT = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")

# d|m|Y -> (ano, mes, dia); tambem aceita "7 de outubro de 1959"
_RE_NUM = re.compile(r"(\d{1,2})\s*(?:de\s+)?[|/]?\s*(\d{1,2})\s*(?:de\s+)?[|/]?\s*(\d{4})")
_RE_EXTENSO = re.compile(
    r"(\d{1,2})\s+de\s+(" + "|".join(MESES_PT) + r")\s+de\s+(\d{4})", re.IGNORECASE)


def _cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def wikitext(titulo: str) -> str:
    """Baixa o wikitext da pagina em portugues."""
    url = "https://pt.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "format": "json", "titles": titulo,
        "formatversion": "2", "redirects": "1",
    })
    req = urllib.request.Request(url, headers=UA)
    d = json.load(urllib.request.urlopen(req, timeout=60))
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return ""
    rev = pages[0].get("revisions") or [{}]
    return rev[0].get("slots", {}).get("main", {}).get("content", "")


def extrair_datas(texto: str) -> list[tuple[int, int, int]]:
    """Todas as datas (ano, mes, dia) que encontrar, deduplicadas."""
    achadas: set[tuple[int, int, int]] = set()
    for m in _RE_EXTENSO.finditer(texto):
        d = int(m.group(1))
        mes = MESES_PT.index(m.group(2).lower()) + 1
        achadas.add((int(m.group(3)), mes, d))
    for m in _RE_NUM.finditer(texto):
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # pt.wikipedia usa dd/mm/aaaa; se o primeiro numero nao serve como dia,
        # tenta mm/dd/aaaa
        if 1 <= a <= 31 and 1 <= b <= 12:
            achadas.add((y, b, a))
        elif 1 <= a <= 12 and 1 <= b <= 31:
            achadas.add((y, a, b))
    return sorted(achadas)


def verificar(titulo: str, dia: int, mes: int) -> tuple[bool, str]:
    """Confere se a pagina menciona a data esperada. Devolve (ok, evidencia)."""
    c = _cache()
    chave = f"wt:{titulo}"
    if chave not in c:
        try:
            c[chave] = wikitext(titulo)
        except Exception as e:
            return False, f"falha ao baixar {titulo!r}: {type(e).__name__} {e}"
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.8)
    texto = c[chave]
    if not texto:
        return False, f"pagina {titulo!r} nao existe em pt.wikipedia"

    # extrair_datas devolve (ano, mes, dia); o alvo e (dia, mes).
    for ano, m, d in extrair_datas(texto):
        if d == dia and m == mes:
            return True, f"{titulo}: {d:02d}/{m:02d}/{ano} (ano {ano})"
    return False, (f"{titulo}: nenhuma mencao a {dia:02d}/{mes:02d}; "
                   f"datas encontradas: {extrair_datas(texto)[:8]}")


def main() -> int:
    if len(sys.argv) < 4:
        print("uso: verificar_data.py DD MM 'Titulo da pagina' [...]")
        print("     verifica se a pagina da Wikipeia cita aquela data")
        return 2
    dia, mes = int(sys.argv[1]), int(sys.argv[2])
    banco = Path(__file__).resolve().parent.parent / "assets" / "historia-das-datas.json"
    entradas = json.loads(banco.read_text(encoding="utf-8")) if banco.exists() else {}
    chave = f"{dia:02d}-{mes:02d}"
    e = entradas.get(chave)
    if not e:
        print(f"sem entrada no banco para {chave}")
        return 1
    titulo = sys.argv[3] if len(sys.argv) > 3 else e.get("wikipedia", "")
    ok, evid = verificar(titulo, dia, mes)
    print(f"{'CONFIRMADO' if ok else 'DIVERGENTE'} {chave} {e.get('ano')}")
    print(f"  {evid}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())