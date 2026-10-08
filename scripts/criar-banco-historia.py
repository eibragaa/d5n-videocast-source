#!/usr/bin/env python3
"""Constroi assets/historia-das-datas.json um dia por vez.

Um arquivo escrito de uma vez saiu com lixo CJK no meio do texto e nao passou
no parser JSON. Aqui cada dia entra sozinho e e validado antes de virar
arquivo, entao um erro de digitacao fica localizado no dia e nao invalida o
banco inteiro.

Uso:
    python3 scripts/criar-banco-historia.py          # mostra o que falta
    python3 scripts/criar-banco-historia.py --add 07-10 '{"ano":1959,...}'
"""
import json
import sys
from pathlib import Path

BANCO = Path(__file__).resolve().parent.parent / "assets" / "historia-das-datas.json"
MESES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")

# Caracteres que a TTS nao deve receber: CJK, circled, fullwidth.
def texto_suspeito(s: str) -> list:
    ruins = []
    for ch in s:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3040 <= o <= 0x30FF:
            ruins.append(ch)
        elif 0xFF00 <= o <= 0xFFEF:
            ruins.append(ch)
    return ruins


def valida_entrada(chave: str, e: dict) -> list:
    erros = []
    if not (len(chave) == 5 and chave[2] == "-" and chave[:2].isdigit()
            and chave[3:].isdigit()):
        return [f"chave invalida: {chave!r} (esperado DD-MM)"]
    dia, mes = int(chave[:2]), int(chave[3:])
    if not 1 <= dia <= 31 or not 1 <= mes <= 12:
        erros.append(f"data fora de range: {chave}")
    for campo in ("ano", "titulo", "detalhe", "fechamento", "fonte", "wikidata"):
        if campo not in e or not str(e[campo]).strip():
            erros.append(f"campo ausente ou vazio: {campo}")
    ano = e.get("ano")
    if isinstance(ano, int) and not 1000 <= ano <= 2026:
        erros.append(f"ano implausivel: {ano}")
    for campo in ("titulo", "detalhe", "fechamento"):
        v = str(e.get(campo, ""))
        cjk = texto_suspeito(v)
        if cjk:
            erros.append(f"{campo} tem caractere invalido {cjk!r}: {v[:60]}")
        if len(v) < 20:
            erros.append(f"{campo} curto demais ({len(v)} chars): {v!r}")
    if not str(e.get("fonte", "")).startswith("http"):
        erros.append("fonte precisa ser URL http(s)")
    if not str(e.get("wikidata", "")).startswith("Q"):
        erros.append("wikidata precisa ser um QID (ex: Q11589)")
    return erros


def carregar() -> dict:
    if not BANCO.exists():
        return {}
    try:
        return json.loads(BANCO.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"banco invalido ({e}); apague {BANCO} e recomece")


def salvar(b: dict) -> None:
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    BANCO.write_text(
        json.dumps(b, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def main() -> int:
    args = sys.argv[1:]
    if not args:
        b = carregar()
        print(f"banco: {len(b)} dias")
        for k in sorted(b):
            e = b[k]
            print(f"  {k}  {e['ano']}  {e['titulo'][:58]}")
        return 0

    if args[0] == "--add":
        if len(args) < 3:
            print(__doc__)
            return 2
        chave = args[1]
        try:
            entrada = json.loads(args[2])
        except json.JSONDecodeError as e:
            print(f"JSON do dia invalido: {e}")
            return 1
        erros = valida_entrada(chave, entrada)
        if erros:
            print(f"REJEITADO {chave}:")
            for e in erros:
                print(f"  - {e}")
            return 1
        b = carregar()
        b[chave] = entrada
        salvar(b)
        print(f"OK {chave} ({MESES[int(chave[3:]) - 1][:3]}) "
              f"-> {entrada['ano']}: {entrada['titulo'][:56]}")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())