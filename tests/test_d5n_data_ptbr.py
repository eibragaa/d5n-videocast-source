"""Datas em portugues e fuso editorial do D5N.

O defeito original: o intro usava strftime('%A, %d de %B de %Y'), que segue o
locale do processo. No cron o locale e C, entao a apresentadora anunciava
"Thursday, 28 de May de 2026" em um podcast inteiro em portugues.
"""
import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo


REPO = Path(__file__).parents[1]
HELPER = REPO / "scripts" / "d5n_data_ptbr.py"

DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DataPtBrTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(HELPER, "d5n_data_ptbr")

    def test_data_extenso_em_portugues(self):
        self.assertEqual(
            self.mod.data_extenso(date(2026, 9, 29)),
            "terça-feira, 29 de setembro de 2026",
        )
        self.assertEqual(
            self.mod.data_extenso(date(2026, 5, 28)),
            "quinta-feira, 28 de maio de 2026",
        )

    def test_data_extenso_nao_depende_de_locale(self):
        """O locale C do cron produz nomes em inglês; o helper não pode herdar isso."""
        for dia in (date(2026, 1, 1), date(2026, 7, 4), date(2026, 12, 31)):
            out = self.mod.data_extenso(dia)
            self.assertIn(DIAS[dia.weekday()], out)
            self.assertIn(MESES[dia.month - 1], out)
            for nome_en in ("January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November",
                            "December", "Monday", "Tuesday", "Wednesday", "Thursday",
                            "Friday", "Saturday", "Sunday"):
                self.assertNotIn(nome_en, out, f"saída contém inglês: {nome_en}")

    def test_todos_os_dias_da_semana(self):
        # 2026-09-28 é uma segunda-feira
        inicio = date(2026, 9, 28)
        for i, esperado in enumerate(DIAS):
            d = date.fromordinal(inicio.toordinal() + i)
            self.assertEqual(self.mod.data_extenso(d).split(",")[0], esperado)

    def test_data_curta(self):
        self.assertEqual(self.mod.data_curta(date(2026, 9, 29)), "29/09/2026")
        self.assertEqual(self.mod.data_curta(date(2026, 1, 5)), "05/01/2026")

    def test_hoje_editorial_usa_fuso_de_sao_paulo(self):
        hoje = self.mod.hoje_editorial()
        esperado = date(2026, 1, 1)  # qualquer valor; só validamos o tipo/fuso
        self.assertIsInstance(hoje, date)
        # O fuso editorial é -03:00; se o processo estiver em UTC, a data pode
        # diferir. Verifica que a data bate com o fuso, não com o sistema.
        from datetime import datetime
        pelo_fuso = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        self.assertEqual(hoje, esperado.__class__.fromordinal(pelo_fuso.toordinal()))

    def test_sigla_mes(self):
        self.assertEqual(self.mod.sigla_mes("Setembro"), "SET")
        self.assertEqual(self.mod.sigla_mes("maio"), "MAI")
        self.assertEqual(self.mod.sigla_mes("Dezembro"), "DEZ")


class IntroDoPodcastTests(unittest.TestCase):
    """O intro é o que a apresentadora fala em voz alta."""

    def test_gerador_do_roteiro_nao_usa_strftime_de_dia_ou_mes(self):
        src = (REPO / "scripts" / "gerar_roteiro_d5n.py").read_text(encoding="utf-8")
        for proibido in ("%A", "%B", "'%a", "'%b"):
            self.assertNotIn(
                proibido, src,
                f"strftime({proibido}) no roteiro volta a falar dia/mês em inglês",
            )

    def test_intro_gerado_esta_em_portugues(self):
        src = (REPO / "scripts" / "gerar_roteiro_d5n.py").read_text(encoding="utf-8")
        self.assertIn("data_extenso(TODAY_DATE)", src)
        self.assertIn("hoje_editorial()", src)


if __name__ == "__main__":
    unittest.main()
