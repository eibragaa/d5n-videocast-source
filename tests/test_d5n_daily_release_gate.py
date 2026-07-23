import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "d5n_daily_release_gate.py"
spec = importlib.util.spec_from_file_location("d5n_daily_release_gate", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Não foi possível carregar {SCRIPT}")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_trends_accepts_all_four_editorial_pillars(self):
        trends = self.base / "trends-valid.txt"
        text = "\n\n".join(
            f"=== {pillar} ===\nTITLE: notícia 1\nSUMMARY: contexto factual " + ("detalhado " * 20)
            for pillar in ("GLOBAL", "BRASIL", "TECH", "ECONOMIA")
        )
        trends.write_text(text, encoding="utf-8")

        self.assertEqual(gate.validate_trends(trends), [])

    def test_trends_requires_all_four_editorial_pillars(self):
        trends = self.base / "trends.txt"
        trends.write_text("=== GLOBAL ===\nUma notícia\n=== BRASIL ===\nOutra\n=== TECH ===\nIA\n", encoding="utf-8")

        errors = gate.validate_trends(trends)

        self.assertTrue(any("ECONOMIA" in error for error in errors))

    def test_manifest_rejects_stale_date_and_cta_before_news(self):
        manifest = self.base / "manifest.json"
        manifest.write_text(
            json.dumps({
                "editorial_date": "2026-07-21",
                "sections": ["intro", "mundo", "cta", "brasil", "tecnologia", "economia", "ofertas", "frase", "outro"],
                "section_voice_map": {name: "voice" for name in gate.SECTION_ORDER},
            }),
            encoding="utf-8",
        )

        errors = gate.validate_manifest(manifest, date(2026, 7, 22))

        self.assertTrue(any("data editorial" in error for error in errors))
        self.assertTrue(any("CTA" in error for error in errors))

    def test_audio_rejects_episode_shorter_than_five_minutes(self):
        errors = gate.validate_audio_metadata(
            {"duration": 299.9, "bit_rate": 192000, "codec_name": "mp3", "sample_rate": 44100}
        )

        self.assertTrue(any("300" in error for error in errors))

    def test_script_accepts_non_spoken_metadata_header_before_intro(self):
        fill = "Notícia confirmada, com contexto e impacto prático para o dia. " * 12
        segments = {
            "intro": "Bom dia! Quarta-feira, 22 de julho de 2026. " + fill,
            "mundo": fill,
            "brasil": fill,
            "tecnologia": fill,
            "economia": fill,
            "ofertas": fill,
            "frase": fill,
            "cta": fill,
            "outro": fill + " Até a próxima e bom dia!",
        }
        segments["intro"] = (
            "Drop Five News — Episódio de 22 de julho de 2026\n"
            "Data: quarta-feira, 22 de julho de 2026\n"
            "Voz: Thalita\n\n" + segments["intro"]
        )
        segments["outro"] = (
            "Drop Five News — Encerramento\n"
            "Data: quarta-feira, 22 de julho de 2026\n"
            "Voz: Thalita\n\n" + segments["outro"]
        )
        audio_dir = self.base / "audio-with-headers"
        audio_dir.mkdir()
        for name, content in segments.items():
            (audio_dir / f"{name}.txt").write_text(content, encoding="utf-8")
        errors, _ = gate.validate_script(audio_dir, date(2026, 7, 22), self.base / "history")
        self.assertEqual(errors, [])

    def test_script_requires_date_core_sections_and_bom_dia_at_both_ends(self):
        audio_dir = self.base / "audio"
        audio_dir.mkdir()
        (audio_dir / "intro.txt").write_text("Olá, começamos agora.", encoding="utf-8")
        for name in ("mundo", "brasil", "tecnologia", "economia", "outro"):
            (audio_dir / f"{name}.txt").write_text("Texto curto.", encoding="utf-8")

        errors, _ = gate.validate_script(audio_dir, date(2026, 7, 22), history_dir=self.base / "history")

        self.assertTrue(any("9 seções" in error for error in errors))
        self.assertTrue(any("data editorial" in error for error in errors))
        self.assertTrue(any("Bom dia" in error for error in errors))

    def test_script_rejects_repeated_opening_from_recent_history(self):
        audio_dir = self.base / "audio"
        history_dir = self.base / "history"
        audio_dir.mkdir()
        history_dir.mkdir()
        opening = "Bom dia! Quarta-feira, 22 de julho de 2026. Hoje tem notícia grande e eu começo pelo impacto direto."
        sections = self._valid_sections(opening=opening)
        for name, text in sections.items():
            (audio_dir / f"{name}.txt").write_text(text, encoding="utf-8")
        (history_dir / "2026-07-21.json").write_text(
            json.dumps({"date": "2026-07-21", "segments": {"intro": opening, "outro": "Encerramento diferente. Bom dia!"}}),
            encoding="utf-8",
        )

        errors, _ = gate.validate_script(audio_dir, date(2026, 7, 22), history_dir=history_dir)

        self.assertTrue(any("abertura repete" in error for error in errors))

    def test_valid_script_and_audio_metadata_pass(self):
        audio_dir = self.base / "audio"
        audio_dir.mkdir()
        sections = self._valid_sections()
        for name, text in sections.items():
            (audio_dir / f"{name}.txt").write_text(text, encoding="utf-8")

        script_errors, snapshot = gate.validate_script(audio_dir, date(2026, 7, 22), history_dir=self.base / "history")
        audio_errors = gate.validate_audio_metadata(
            {"duration": 480.0, "bit_rate": 192000, "codec_name": "mp3", "sample_rate": 44100}
        )

        self.assertEqual(script_errors, [])
        self.assertEqual(audio_errors, [])
        self.assertEqual(snapshot["date"], "2026-07-22")
        self.assertEqual(len(snapshot["segments"]), 9)

    @staticmethod
    def _valid_sections(opening=None):
        return {
            "intro": opening or "Bom dia! Quarta-feira, 22 de julho de 2026. Uma mudança silenciosa virou a notícia mais importante da manhã.",
            "mundo": "No mundo, o primeiro fato muda relações entre países e pede contexto. " * 25,
            "cta": "Fica comigo porque os próximos blocos completam esse cenário. " * 10,
            "brasil": "No Brasil, a decisão afeta serviços, empresas e cidadãos de formas diferentes. " * 25,
            "saude": "Na saúde, o avanço abre possibilidades, mas ainda exige cautela. " * 15,
            "tecnologia": "Em tecnologia, a inteligência artificial deixa o laboratório e entra na rotina. " * 25,
            "economia": "Na economia, os números alteram decisões de famílias e negócios. " * 25,
            "ofertas": "A mensagem de hoje é simples: contexto antes da pressa melhora escolhas. " * 15,
            "outro": "Esses foram os fatos que ajudam a entender o dia. Amanhã tem uma nova conversa. Bom dia!",
        }


if __name__ == "__main__":
    unittest.main()
