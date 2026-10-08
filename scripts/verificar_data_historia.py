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
# Wikitexto da Wikipédia usa templates de alinhamento antes do ano: "== {{0}}[[1974]] ==".
# O template precisa virar ESPACO e nao sumir: a data da pagina ("8 de outubro")
# so aparece quando se le a data junto com o ano da linha, e "{{0}}[[1974]]"
# colado vira "1974" sem separador.
_RE_TEMPL = re.compile(r"\{\{[^{}]*\}\}")


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


def entrada_do_banco(dia: int, mes: int) -> dict | None:
    """Entrada de (dia, mes) em assets/historia-das-datas.json, se houver."""
    banco = Path(__file__).resolve().parent.parent / "assets" / "historia-das-datas.json"
    if not banco.exists():
        return None
    try:
        return json.loads(banco.read_text(encoding="utf-8")).get(f"{dia:02d}-{mes:02d}")
    except json.JSONDecodeError:
        return None


def wikitext_com_titulo(titulo: str) -> str:
    """Baixa o wikitext e prefixa o titulo da pagina.

    O titulo importa porque a data de uma pagina como "8 de outubro" so existe
    ali; o corpo traz apenas os anos, em listas como "== {{0}}[[1974]] ==".
    """
    texto = wikitext(titulo)
    if not texto:
        return ""
    return f"{titulo}\n{texto}"


def extrair_datas(texto: str) -> list[tuple[int, int, int]]:
    """Todas as datas (ano, mes, dia) que encontrar, deduplicadas.

    Tres formatos aparecem no wikitexto da Wikipédia e todos precisam ser lidos:

    1. "{{Dtlink|4|10|1959}}" — template de data das infoboxes. Substituido por
       " 4 de outubro de 1959 " antes das regexes, senão o Luna 3 (lancado em
       4/10/1959 e fotografado em 7/10/1959) não tinha nenhuma data extraida.
    2. "[[7 de Outubro]] de [[1959]]" — links internos. As chaves quebram o
       padrao "7 de outubro de 1959".
    3. "07/10/1959" e "7 de outubro de 1959" — texto corrido, ja coberto pelas
       regexes.
    """
    achadas: set[tuple[int, int, int]] = set()

    MES = "(?:" + "|".join(MESES_PT) + r")"

    # 1) {{Dtlink|D|M|Y}} e variantes com argumento nomeado
    def _dtlink(m: re.Match) -> str:
        nums = [int(x) for x in m.group(1).split("|") if x.strip().isdigit()]
        nums = [n for n in nums if 1000 <= n <= 2100] or nums
        if len(nums) >= 3:
            d, me, y = nums[0], nums[1], nums[2]
            if 1 <= d <= 31 and 1 <= me <= 12:
                return f" {d} de {MESES_PT[me-1]} de {y} "
        return " "

    limpo = re.sub(r"\{\{\s*[Dd]t(?:link|flex)\s*\|([^}]*)\}\}", _dtlink, texto)
    # 2) links internos: [[X]] vira X (mantendo o espaco)
    limpo = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", limpo)
    limpo = re.sub(r"\[\[([^\]]*)\]\]", r"\1", limpo)
    # 3) qualquer template restante vira espaco
    limpo = _RE_TEMPL.sub(" ", limpo)

    for m in _RE_EXTENSO.finditer(limpo):
        d = int(m.group(1))
        mes = MESES_PT.index(m.group(2).lower()) + 1
        achadas.add((int(m.group(3)), mes, d))
    for m in _RE_NUM.finditer(limpo):
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= a <= 31 and 1 <= b <= 12:
            achadas.add((y, b, a))
        elif 1 <= a <= 12 and 1 <= b <= 31:
            achadas.add((y, a, b))
    return sorted(achadas)


def _anos_no_corpo(texto: str) -> set[int]:
    """Anos de 4 digitos citados no corpo, sem ruido de template.

    Numa pagina de data ("8 de outubro") cada evento e "* [[1974]] — texto".
    extrair_datas() nao serve aqui: nao ha dia/mes para formar a data, so o ano.
    Filtra 1000-2100 e descarta o que veio de nome de arquivo/imagem, que tem
    anos que nao sao eventos.
    """
    # remove imagens e arquivos antes de procurar
    limpo = re.sub(r"\[\[(?:Imagem|Image|Arquivo|File):[^\]]*\]\]", " ", texto)
    limpo = re.sub(r"\{\{[^{}]*\}\}", " ", limpo)
    anos = set()
    for m in re.finditer(r"\b(1[0-9]{3}|20[0-2][0-9])\b", limpo):
        y = int(m.group(1))
        # um ano colado em numero maior (1959-008A, 1219) nao e evento
        ini, fim = m.start(), m.end()
        if ini > 0 and limpo[ini-1].isdigit():
            continue
        if fim < len(limpo) and limpo[fim].isdigit():
            continue
        anos.add(y)
    return anos


def verificar(titulo: str, dia: int, mes: int) -> tuple[bool, str]:
    """Confere se a pagina menciona a data esperada. Devolve (ok, evidencia).

    Uma pagina de data ("8 de outubro") tem a data so no TITULO, nunca no
    corpo: o corpo lista "== {{0}}[[1974]] ==" com o ano, e o dia/mes vem do
    titulo que o wikitexto traz na primeira linha. Checar so o corpo reprovava
    um fato real. Por isso a checagem tambem le o titulo da pagina.
    """
    c = _cache()
    chave = f"wt:{titulo}"
    if chave not in c:
        try:
            d = wikitext_com_titulo(titulo)
            c[chave] = d
        except Exception as e:
            return False, f"falha ao baixar {titulo!r}: {type(e).__name__} {e}"
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.8)
    texto = c[chave]
    if not texto:
        return False, f"pagina {titulo!r} nao existe em pt.wikipedia"

    # O banco declara o ANO do fato. Uma pagina de data ("8 de outubro") so
    # traz o ano; uma pagina do evento ("Luna 3") traz a data e o ano. Chegar os
    # tres e o que torna a verificacao de verdade: sem o ano, qualquer evento
    # poderia ser atribuido a qualquer ano.
    ano_esperado = None
    e = entrada_do_banco(dia, mes)
    if e:
        ano_esperado = e.get("ano")

    # 1) pagina de data: o titulo casa e o ano esta no corpo
    m = re.match(r"(\d{1,2})\s+de\s+(" + "|".join(MESES_PT) + r")", titulo, re.I)
    if m and int(m.group(1)) == dia and \
            MESES_PT.index(m.group(2).lower()) + 1 == mes:
        # Numa pagina de data o corpo lista so o ANO ("* [[1974]] — ..."), sem
        # dia e mes repetidos: dia e mes vem do titulo.Por isso a checagem aqui
        # e "o ano aparece na pagina", e nao "a data completa aparece".
        anos = _anos_no_corpo(texto)
        if ano_esperado is None:
            return True, f"{titulo}: pagina da data {dia:02d}/{mes:02d}"
        if ano_esperado in anos:
            return True, (f"{titulo}: pagina de {dia:02d}/{mes:02d} cita "
                          f"{ano_esperado}")
        return False, (f"{titulo}: a pagina e sobre {dia:02d}/{mes:02d} mas nao "
                       f"cita o ano {ano_esperado} (anos na pagina: "
                       f"{sorted(anos)[:6]})")

    # 2) o corpo cita a data por extenso ou em numeros
    # extrair_datas devolve (ano, mes, dia); o alvo e (dia, mes).
    for ano, m_, d_ in extrair_datas(texto):
        if d_ == dia and m_ == mes:
            if ano_esperado is None or ano == ano_esperado:
                return True, f"{titulo}: {d_:02d}/{m_:02d}/{ano} (ano {ano})"
            return False, (f"{titulo}: a data {d_:02d}/{m_:02d} aparece com o "
                           f"ano {ano}, mas o banco diz {ano_esperado}")
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