#!/usr/bin/env python3
"""Mensagem do dia: citacao de um pensador grego ou estudioso contemporaneo.

Risco especifico desta secao: atribuir a frase a uma pessoa famous. O gerador
antes escrevia motivacao generica no formato de citacao ("Quinta-feira. A
tecnologia continua transformando..."), sem autor nenhum — soava como frase de
pensador e nao era de ninguem. Pior ainda seria inventar uma citacao e colocar
o nome de um filosofo nela.

Por isso o texto NAO e gerado: vem do arquivo assets/frases.json, e cada entrada
declara autor, obra e fonte. As autorias incluidas sao de autores Classicos e
contemporaneos com obra publicada e traduzida, e a `fonte` aponta para o texto
de onde a citacao foi conferida.

Cada frase tem `temas`: as categorias do D5N. O gerador escolhe a frase cujo
tema casa com as noticias do dia, para a mensagemdialogar com o episodio.
"""
import json
from pathlib import Path

FRASES = Path(__file__).resolve().parent.parent / "assets" / "frases.json"


def carregar() -> list:
    if not FRASES.exists():
        return []
    d = json.loads(FRASES.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else d.get("frases", [])


def citacao_para(dia: int, mes: int, temas: set | None = None) -> dict | None:
    """Frase do dia, priorizando o tema que casa com as noticias do dia."""
    todas = carregar()
    if not todas:
        return None
    if temas:
        combinando = [f for f in todas if set(f.get("temas", [])) & set(temas)]
        if combinando:
            todas = combinando
    # indice estavel pelo dia: mesmo dia do mes sempre picks a mesma frase
    return todas[dia % len(todas)]


def listar() -> list:
    return carregar()