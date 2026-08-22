import importlib.util
import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

REPO = Path(__file__).parents[1]
FECHAMENTO_PIPELINE = REPO / "fechamento" / "scripts" / "fechamento_pipeline.py"
FECHAMENTO_MIXER = REPO / "fechamento" / "scripts" / "fechamento_mixer.py"
FECHAMENTO_FEED = REPO / "fechamento" / "scripts" / "gerar_fechamento_feed.py"

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

class FechamentoContractTests(unittest.TestCase):
    def test_pipeline_constants(self):
        mod = load_module(FECHAMENTO_PIPELINE, "fechamento_pipeline_constants")
        self.assertEqual(mod.VOICE, "pt-BR-AntonioNeural")
        self.assertEqual(mod.MIN_WORDS, 1100)
        self.assertEqual(mod.MAX_WORDS, 1500)
        self.assertEqual(mod.MIN_SECONDS, 480)
        self.assertEqual(mod.MAX_SECONDS, 600)
        self.assertIn("fechamento do mercado", mod.RSS_CTA.lower())

    def test_mixer_exists_and_constants(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = load_module(FECHAMENTO_MIXER, "fechamento_mixer_constants")
        self.assertTrue(FECHAMENTO_MIXER.exists())
        self.assertGreaterEqual(mod.MIN_SECONDS, 480)

    def test_netlify_redirects_fechamento(self):
        content = (REPO / "netlify.toml").read_text(encoding="utf-8")
        self.assertIn("/fechamento.xml", content)
        self.assertIn("/fechamento/feeds/fechamento.xml", content)
        self.assertIn("/audio/fechamento-", content)

    def test_cron_prompt_fechamento(self):
        prompt = (REPO / "fechamento" / "cron-prompt.txt").read_text(encoding="utf-8")
        self.assertIn("FECHAMENTO DO MERCADO", prompt)
        self.assertIn("pt-BR-AntonioNeural", prompt)
        self.assertIn("17:30", prompt)

    def test_feed_module_loads(self):
        mod = load_module(FECHAMENTO_FEED, "gerar_fechamento_feed_test")
        self.assertTrue(hasattr(mod, "build_feed"))
