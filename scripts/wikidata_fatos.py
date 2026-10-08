#!/usr/bin/env python3
"""Consulta a Wikidata e devolve o QID + a data real (P585) de um termo.

Usei QIDs chutados na primeira versao e todos estavam errados (Luna 3 e
Q942814, nao Q11589). Este script existe para nao repetir isso: o gerador de
roteiro tem que consumir o QID e a data que a Wikidata devolve, nunca o que a
minha memoria inventar.

A Wikidata devolve 429 rapido em busca repetida, entao ha backoff com jitter e
cache em disco. `wbgetentities` aceita ate 50 ids por chamada, entao a data de
varios termos sai em uma so requisicao.
"""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "d5n-historia/1.0 (podcast D5N; contato local)"}
CACHE = Path.home() / ".cache" / "d5n" / "wikidata.json"
ENDPOINT = "https://www.wikidata.org/w/api.php"
DELAY = 1.5


def _cache_ler() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _cache_gravar(c: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")


def _chamar(params: dict, tentativas: int = 4) -> dict:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tentativas - 1:
                espera = (DELAY * (2 ** i)) + random.uniform(0, 0.7)
                print(f"  HTTP {e.code}, aguardando {espera:.1f}s", file=sys.stderr)
                time.sleep(espera)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if i < tentativas - 1:
                espera = DELAY * (2 ** i) + random.uniform(0, 0.7)
                print(f"  {type(e).__name__}, aguardando {espera:.1f}s", file=sys.stderr)
                time.sleep(espera)
                continue
            raise
    raise RuntimeError("sem tentativas restantes")


def buscar(termo: str) -> list[dict]:
    """Busca por rotulo. Retorna lista de {qid, label, description}."""
    dados = _chamar({
        "action": "wbsearchentities", "search": termo, "language": "pt",
        "uselang": "pt", "format": "json", "limit": 5, "type": "item",
    })
    return [{"qid": r["id"], "label": r.get("label", ""),
             "description": r.get("description", "")} for r in dados.get("search", [])]


def facts(qids: list[str]) -> dict:
    """P585 (inception/date) e P571, em lote de 50."""
    saida: dict[str, dict] = {}
    for i in range(0, len(qids), 50):
        bloco = qids[i:i + 50]
        dados = _chamar({
            "action": "wbgetentities", "ids": "|".join(bloco),
            "props": "claims|labels", "languages": "pt|en", "format": "json",
        })
        for qid, e in dados.get("entities", {}).items():
            datas = []
            for prop in ("P585", "P571", "P577", "P1191"):
                for c in e.get("claims", {}).get(prop, []):
                    v = c.get("mainsnak", {}).get("datavalue", {})
                    if "time" in v:
                        t = v["time"]  # +1959-10-07T00:00:00Z
                        data = t.lstrip("+").split("T")[0]
                        if data.count("-") == 2 and len(data) >= 8:
                            datas.append({"data": data, "prop": prop})
            label = ""
            for lg in ("pt", "en"):
                lab = e.get("labels", {}).get(lg)
                if lab:
                    label = lab["value"]
                    break
            saida[qid] = {"datas": datas, "label": label}
        time.sleep(DELAY)
    return saida


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cache = _cache_ler()
    terms = sys.argv[1:]

    print(f"== busca ({len(terms)} termos) ==")
    for t in terms:
        chave = f"search:{t}"
        if chave not in cache:
            try:
                cache[chave] = buscar(t)
            except Exception as e:
                print(f"  {t}: FALHOU {type(e).__name__} {e}")
                continue
            time.sleep(DELAY)
        print(f"  {t}")
        for r in cache[chave][:3]:
            print(f"    {r['qid']:12} {r['label'][:36]:36} {r['description'][:52]}")

    qids = []
    for t in terms:
        for r in cache.get(f"search:{t}", [])[:2]:
            qids.append(r["qid"])
    if not qids:
        print("nenhum QID encontrado")
        _cache_gravar(cache)
        return 1

    print(f"\n== datas ({len(set(qids))} QIDs) ==")
    faltando = [q for q in set(qids) if f"facts:{q}" not in cache]
    if faltando:
        try:
            for qid, v in facts(faltando).items():
                cache[f"facts:{qid}"] = v
        except Exception as e:
            print(f"  FALHOU: {type(e).__name__} {e}")
    for q in sorted(set(qids)):
        v = cache.get(f"facts:{q}")
        if not v:
            continue
        ds = ", ".join(f"{x['data']}({x['prop']})" for x in v["datas"]) or "sem data"
        print(f"  {q:12} {ds:44} {v['label'][:40]}")
    _cache_gravar(cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())