#!/usr/bin/env python3
"""Testa as regras do validar-manifests nos dois sentidos.

Regra que se prova: dia da semana no texto so e ERRO quando o texto AFIRMA que
o dia de hoje e aquele. Noticia real ("Mega-Sena paga nesta quinta") e data
marcada ("o TSE julga nesta quinta") tem que passar; erro de editorial
("hoje e quinta-feira" em dia de quarta) tem que reprovar.

Este teste existe porque corrigi a regra duas vezes e nas duas introduzi
regressao silenciosa: a primeira versao barrava manchetinha de loteria, a
segunda deixava passar o erro mais comum. `python3 test_validador_datas.py`
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vm", AQUI / "validar-manifests.py")
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)

EDITORIAL = date(2026, 10, 7)   # quarta-feira
TMP = Path("/tmp/d5n-test-datas") / EDITORIAL.isoformat()
TMP.mkdir(parents=True, exist_ok=True)

CASOS = [
    # (nome, texto, deve passar)
    ("ERRO: 'hoje e quinta-feira'", "Bom dia! Hoje é quinta-feira, o seu panorama do dia.", False),
    ("ERRO: 'hoje e quinta' sem -feira", "Bom dia! Hoje é quinta, o seu panorama do dia.", False),
    ("ERRO: 'nesta quinta-feira'", "O foco desta quinta-feira, 7 de outubro, reúne a agenda em Brasília.", False),
    ("ERRO: 'ontem foi segunda-feira'", "Ontem foi segunda-feira e o mercado subiu.", False),
    ("ERRO: 'amanha e sexta'", "Amanhã é sexta-feira, o mercado abre em alta.", False),
    ("ERRO: 'desta quinta-feira' (bloco de abertura)", "O foco desta quinta-feira, 7 de outubro, reúne a agenda em Brasília.", False),
    ("NOTICIA: sorteio em outra data", "Mega-Sena pode pagar 100 milhões nesta quinta-feira, segundo G1.", True),
    ("NOTICIA: TST em outra data", "O TSE julga nesta quinta o recurso de Garotinho.", True),
    ("NOTICIA: STF nesta segunda", "Nesta segunda-feira o STF julga o caso do leader do partido.", True),
    ("NOTICIA: amanha no Bacen", "Amanhã o Banco Central divulga a Copom, segundo a agência.", True),
    ("CORRETO: dia editorial", "O foco desta quarta-feira, 7 de outubro, reúne a agenda.", True),
]


def main() -> int:
    print(f"editorial {EDITORIAL.isoformat()} = quarta-feira\n")
    alvo = TMP / "tecnologia.txt"
    falhas = 0
    for nome, texto, deve_passar in CASOS:
        alvo.write_text(texto, encoding="utf-8")
        errs = vm.check_dates(texto, alvo)
        passou = not errs
        ok = passou == deve_passar
        if not ok:
            falhas += 1
        print(f"  {'OK   ' if ok else 'FALHOU'} {nome}")
        if errs:
            print(f"          -> {errs}")
    print()
    if falhas:
        print(f"FALHOU: {falhas} de {len(CASOS)} casos")
        return 1
    print(f"TODOS OS {len(CASOS)} CASOS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())