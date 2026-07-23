import importlib.util
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).parents[1]
GENERATOR = REPO / "gerar_pagina_d5n.py"
MIXER = Path("/root/.hermes/profiles/d5n/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py")
DEPLOY = REPO / "deploy_d5n_site.sh"
VERIFIER = Path("/root/.hermes/scripts/d5n-verify-site.py")
EXPECTED_IDS = [
    "intro",
    "mundo",
    "brasil",
    "tecnologia",
    "economia",
    "ofertas",
    "frase",
    "cta",
    "outro",
]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ChapterPlayerContractTests(unittest.TestCase):
    def test_mixer_emits_exact_nine_section_timeline(self):
        mixer = load_module(MIXER, "d5n_mixer_chapters")
        starts = [(section_id, index * 10_000) for index, section_id in enumerate(EXPECTED_IDS)]

        chapters = mixer.finalize_chapters(starts, total_ms=90_000)

        self.assertEqual([chapter["id"] for chapter in chapters], EXPECTED_IDS)
        self.assertEqual(chapters[0]["start"], 0)
        self.assertEqual(chapters[-1]["end"], 90)
        for current, following in zip(chapters, chapters[1:]):
            self.assertEqual(current["end"], following["start"])
            self.assertGreater(current["duration"], 0)

    def test_generator_rejects_generic_or_incomplete_chapters(self):
        generator = load_module(GENERATOR, "d5n_generator_chapters_invalid")
        generic = [
            {"id": "intro", "label": "Abertura", "start": 0},
            {"id": "noticias", "label": "Notícias", "start": 30},
            {"id": "outro", "label": "Encerramento", "start": 330},
        ]

        self.assertEqual(generator.validate_chapters(generic, duration=360), [])

    def test_generator_renders_nine_clickable_youtube_style_segments(self):
        generator = load_module(GENERATOR, "d5n_generator_chapters_render")
        chapters = [
            {
                "id": section_id,
                "label": section_id.title(),
                "start": index * 10,
                "end": (index + 1) * 10,
                "duration": 10,
            }
            for index, section_id in enumerate(EXPECTED_IDS)
        ]

        rendered = generator.render_chapter_segments(chapters)

        self.assertEqual(rendered.count('class="chapter-segment"'), 9)
        self.assertEqual(rendered.count('class="chapter-segment-fill"'), 9)
        self.assertIn('data-chapter-start="0"', rendered)
        self.assertIn('aria-label="Ir para o capítulo Abertura', rendered)

    def test_deploy_versions_chapter_manifest_as_release_artifact(self):
        deploy = DEPLOY.read_text(encoding="utf-8")

        self.assertIn('CHAPTER_MANIFEST="/tmp/d5n_audio/manifest.json"', deploy)
        self.assertIn('CHAPTER_DEST="chapters/${DATE}.json"', deploy)
        self.assertIn('git add -- "$CHAPTER_DEST"', deploy)

    def test_site_verifier_requires_nine_real_chapters(self):
        verifier = VERIFIER.read_text(encoding="utf-8")

        self.assertIn("Tem 9 capítulos reais", verifier)
        self.assertIn("chapter-segment", verifier)
        self.assertIn("chapter-current", verifier)


if __name__ == "__main__":
    unittest.main()
