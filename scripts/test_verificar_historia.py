#!/usr/bin/env python3
"""Testa verificar_data_historia nos dois sentidos.

Regra: a pagina precisa citar DIA, MES e ANO do fato. Corre uma verificacao que
so checava dia e mes aceitaria "Luna 3 em 15 de outubro de 1959" — e o banco
declara o ano justamente para isso.

Este teste existe porque a verificacao ja errou nos dois sentidos: a primeira
versao barrava um fato real (pagina de data so tem a data no titulo, e os anos
no corpo com template `{{0}}`), a segunda aceitava data errada depois que a
limpeza de template engoliu as datas numericas.

Uso: python3 scripts/test_verificar_historia.py
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from verificar_data_historia import verificar  # noqa: E402

# (titulo, dia, mes, deve confirmar)
CASOS = [
    # banco tem 07-10 = 1959 (Luna 3) e 08-10 = 1974 (Franklin National)
    ("Luna 3", 7, 10, True),
    ("8 de outubro", 8, 10, True),
    ("4 de outubro", 4, 10, True),
    # datas que as paginas naouberem
    ("Sputnik I", 22, 10, False),
    ("Luna 3", 15, 10, False),
    ("Luna 3", 8, 10, False),
    ("Pagina Inexistente XYZ", 8, 10, False),
]


def main() -> int:
    print("verificar_data_historia — dia, mes E ano\n")
    falhas = 0
    for titulo, dia, mes, deve in CASOS:
        ok, evid = verificar(titulo, dia, mes)
        passou = ok == deve
        if not passou:
            falhas += 1
        print(f"  {'OK   ' if passou else 'FALHOU'} {titulo!r} "
              f"{dia:02d}/{mes:02d} -> {ok} (esperado {deve})")
        print(f"          {evid[:76]}")
    print()
    if falhas:
        print(f"FALHOU: {falhas} de {len(CASOS)} casos")
        return 1
    print(f"TODOS OS {len(CASOS)} CASOS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())