#!/usr/bin/env python3
"""Datas em portugues para o D5N, sem depender do locale do sistema.

`strftime('%A')` e `strftime('%B')` seguem o locale do processo. No cron o locale
e C, e a apresentadora anunciava "Tuesday, 29 de September de 2026" em um
podcast inteiro em portugues. Estas tabelas nao dependem de locale algum.

Uso:
    from d5n_data_ptbr import data_extenso, data_curta, data_extenso_curta
    data_extenso(date(2026, 9, 29))  # 'terça-feira, 29 de setembro de 2026'
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

# Fuso editorial. O cron roda no fuso do sistema (America/Manaus), e perto da
# meia-noite date.today() pode cair no dia errado para o conteudo editorial.
FUSO_EDITORIAL = ZoneInfo("America/Sao_Paulo")

DIAS_SEMANA = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)

# Sem acento inicial: a data ja vem precedida por "de" nos textos.
MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

MESES_CURTOS = {
    "janeiro": "JAN", "fevereiro": "FEV", "março": "MAR", "abril": "ABR",
    "maio": "MAI", "junho": "JUN", "julho": "JUL", "agosto": "AGO",
    "setembro": "SET", "outubro": "OUT", "novembro": "NOV", "dezembro": "DEZ",
}


def hoje_editorial() -> date:
    """Data no fuso America/Sao_Paulo, com fallback seguro."""
    try:
        return datetime.now(FUSO_EDITORIAL).date()
    except Exception:
        return date.today()


def data_extenso(d: date) -> str:
    """'terça-feira, 29 de setembro de 2026'."""
    return f"{DIAS_SEMANA[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def data_extenso_curta(d: date) -> str:
    """'terça, 29 de setembro' — sem o ano, para cards e manchetes."""
    return f"{DIAS_SEMANA[d.weekday()].split('-')[0]}, {d.day} de {MESES[d.month - 1]}"


def data_curta(d: date) -> str:
    """'29/09/2026'."""
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def sigla_mes(mes_pt: str) -> str:
    """'Setembro' ou 'setembro' -> 'SET'. Usado pelos cards."""
    return MESES_CURTOS.get(mes_pt.strip().lower(), mes_pt[:3].upper())
