#!/usr/bin/env python3
"""Converte o trends TXT do dia no manifest JSON que o gerador de roteiro le.

O d5n-trends-diario.py grava as manchetes como texto legivel
(d5n-trends/drop5news-trends-YYYY-MM-DD.txt), mas o gerar_roteiro_d5n.py so
consome manha-conectada/manifests/<data>.json e fechamento/manifests/<data>.json.
Sem MC/FM do dia (eles pararam em 29/09), o gerador caia no fallback e o roteiro
saia com 3.4k chars, abaixo do minimo de 480s do mixer.

Este conversor le o TXT, classifica por palavra-chave e grava o JSON no formato
`{"sources": [{"title", "url", "source"}]}` — o mesmo que o load_mc_fm() espera.

NAO e uma fonte editorial: o texto das secoes ainda vem do gerador, e o
validar-manifests continua sendo o judge final. Serve para dar materia real de
noticia ao gerador quando MC/FM nao rodaram.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d5n_data_ptbr import hoje_editorial  # noqa: E402

REPO = Path(os.environ.get("D5N_REPO", "/root/repositorio/d5n-videocast-source")).resolve()
TRENDS = Path(os.environ.get("D5N_TRENDS", str(Path.home() / "d5n-trends")))

# Mesmo vocabulario do gerar_roteiro_d5n.py, estendido.
WORLDCAT = ["trump", "iran", "israel", "russia", "ucran", "ukraine", "global",
            "guerra", "conflito", "eua", "estados unidos", "china", "japao",
            "europa", "reuniao", "cupula", "onu", "nato", "missil", "putin",
            "zelensky", "gaza", "hamas", "hormuz", "petroleo", "opec"]
BRACAT = ["brasil", "brasilia", "congresso", "bolsonaro", "lula", "stf", "tc-",
          "brb", "eleicoes", "eleitoral", "flavio", "pt ", "psdb", "ministro",
          "presidente", "governo", "senado", "camara", "tribunal", "planalto",
          "saude", "inss", "mei", "imposto", "receita federal", "anac", "bndes",
          "petrobras", "ibovespa", "b3 ", "bovespa"]
TECHCAT = ["inteligencia artificial", "ia ", "ia,", "ia.", "tecnologia", "data center",
           "cripto", "bitcoin", "stablecoin", "galaxy", "nvidia", "openai", "google",
           "apple", "samsung", "meta", "spacex", "chip", "semiconductor", "cloud",
           "software", "app", "smartphone", "robot", "automacao", "telegram",
           "windows", "microsoft", "amazon", "tesla", "intel"]
ECOCAT = ["ibovespa", "bolsa", "dolar", "fechamento", "mercado", "acoes", "wpp",
          "investimento", "commodity", "renda", "juros", "selic", "inflacao",
          "exportacao", "importacao", "cambio", "tarifa", "economia", "pib",
          "banco central", "copom", "emprego", "inflacao"]


def classificar(title: str) -> str:
    t = f" {title.lower()} "
    for k in TECHCAT:
        if k in t:
            return "tech"
    for k in ECOCAT:
        if k in t:
            return "economia"
    for k in BRACAT:
        if k in t:
            return "brasil"
    for k in WORLDCAT:
        if k in t:
            return "mundo"
    return "mundo"


def parse_trends(txt: Path) -> list[dict]:
    """Extrai (titulo, fonte, url) do TXT do trends.

    Formato: linha **Titulo** seguida de "Fonte: Nome — https://url". Os pares
    sao montados por estado (aguardando Fonte) em vez de tentar reconciliar a
    lista a cada linha: na versao anterior o teste `"title" in items[-1]` era
    verdadeiro sempre que o item anterior era um titulo sem fonte, e o parser
    descartava 46 das 48 manchetes do arquivo.
    """
    if not txt.exists():
        return []
    itens: list[dict] = []
    titulo: str | None = None
    for raw in txt.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = raw.strip()
        if linha.startswith("**") and linha.endswith("**") and len(linha) > 4:
            titulo = linha.strip("*").strip()
        elif linha.startswith("Fonte:") and titulo:
            resto = linha[len("Fonte:"):].strip()
            url = ""
            m = re.search(r"(https?://\S+)", resto)
            if m:
                url = m.group(1)
                fonte = resto[:m.start()].strip(" —-–:")
            else:
                fonte = resto
            itens.append({"title": titulo, "source": fonte.strip() or "fonte",
                          "url": url})
            titulo = None
    if titulo:  # titulo sem linha Fonte (ultimo do arquivo)
        itens.append({"title": titulo, "source": "fonte", "url": ""})
    # limpa entradas sem titulo e normaliza encoding
    saida = []
    for it in itens:
        t = it.get("title", "").strip()
        if not t or len(t) < 12:
            continue
        # o trends grava em latin-1 quando o curl falha; normaliza
        if "�" in t or "Ã" in t:
            try:
                t = t.encode("latin-1").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                t = t.replace("�", "")
        it["title"] = t
        it.setdefault("source", "fonte")
        it["categoria"] = classificar(t)
        saida.append(it)
    return saida


def main() -> int:
    alvo = sys.argv[1] if len(sys.argv) > 1 else hoje_editorial().isoformat()
    txt = TRENDS / f"drop5news-trends-{alvo}.txt"
    if not txt.exists():
        ontem = (hoje_editorial() - timedelta(days=1)).isoformat()
        txt = TRENDS / f"drop5news-trends-{ontem}.txt"
        print(f"[aviso] sem trends de {alvo}; tentando {ontem}")
    items = parse_trends(txt)
    if not items:
        print(f"ERRO: nenhuma manchete extraida de {txt}")
        return 1

    por_cat: dict[str, list] = {}
    for it in items:
        por_cat.setdefault(it["categoria"], []).append(
            {"title": it["title"], "url": it.get("url", ""), "source": it["source"]})

    destino = REPO / "manifests" / "d5n" / "trends" / f"{alvo}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(
        {"date": alvo, "fontes": len(items), "sources": items,
         "por_categoria": {k: len(v) for k, v in por_cat.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{len(items)} manchetes de {txt.name}")
    for k, v in sorted(por_cat.items()):
        print(f"  {k:9} {len(v)}")
    print(f"-> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())