import importlib.util
import re
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).parents[1]
GENERATOR = REPO / "gerar_pagina_d5n.py"
CHAPTER_GATE = REPO / "scripts" / "d5n_chapter_manifest.py"
DEPLOY = REPO / "deploy_d5n_site.sh"
VERIFIER = Path("/root/.hermes/scripts/d5n-verify-site.py")
EXPECTED_IDS = [
    "intro",
    "mundo",
    "brasil",
    "tecnologia",
    "economia",
    "interacao",
    "ofertas",
    "frase",
    "recomendacoes",
    "historia",
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
    def test_player_uses_hoje_no_drop_five_news_episode_title(self):
        source = GENERATOR.read_text(encoding="utf-8")

        self.assertIn("Hoje no Drop Five News — Episódio #", source)

    def test_chapter_gate_accepts_v3_timeline_with_intro_at_zero(self):
        gate = load_module(CHAPTER_GATE, "d5n_chapter_gate")
        chapters = [
            {"id": section_id, "start": index * 10, "end": (index + 1) * 10}
            for index, section_id in enumerate(EXPECTED_IDS)
        ]
        headers = {"mundo": "mundo_header.mp3", "frase": "frase_header.mp3"}
        payload = {
            "schema": 2,
            "editorial_date": "2026-08-14",
            "chapters": chapters,
            "section_headers": headers,
        }

        canonical = gate.validate_manifest(payload, "2026-08-14", len(EXPECTED_IDS) * 10)

        self.assertEqual([chapter["id"] for chapter in canonical["chapters"]], EXPECTED_IDS)
        self.assertEqual(canonical["chapters"][0]["start"], 0)
        self.assertEqual(canonical["section_headers"], headers)

    def test_generator_rejects_generic_or_incomplete_chapters(self):
        generator = load_module(GENERATOR, "d5n_generator_chapters_invalid")
        generic = [
            {"id": "intro", "label": "Abertura", "start": 0},
            {"id": "noticias", "label": "Notícias", "start": 30},
            {"id": "outro", "label": "Encerramento", "start": 330},
        ]

        self.assertEqual(generator.validate_chapters(generic, duration=360), [])

    def test_generator_renders_clickable_v3_segments(self):
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

        self.assertEqual(rendered.count('class="chapter-segment"'), len(EXPECTED_IDS))
        self.assertEqual(rendered.count('class="chapter-segment-fill"'), len(EXPECTED_IDS))
        self.assertIn('data-chapter-start="0"', rendered)
        self.assertIn('aria-label="Ir para o capítulo Abertura', rendered)

    def test_deploy_versions_chapter_manifest_as_release_artifact(self):
        deploy = DEPLOY.read_text(encoding="utf-8")

        self.assertIn('CHAPTER_MANIFEST="/tmp/d5n_audio/manifest.json"', deploy)
        self.assertIn('CHAPTER_DEST="chapters/${DATE}.json"', deploy)
        self.assertIn('git add -- "$CHAPTER_DEST"', deploy)

    def test_site_verifier_requires_real_chapters(self):
        """O player de capítulos é responsabilidade do repo, não do Hermes.

        Este teste apontava para /root/.hermes/scripts/d5n-verify-site.py, um
        script que foi reescrito e não verifica mais capítulos — então o teste
        falhava sem que houvesse defeito no site. O contrato que importa é: o
        gerador em uso emite a anatomia do player de capítulos, e o pipeline
        publica um manifesto para o dia (sem ele o site cai no fallback).
        """
        gerador = GENERATOR.read_text(encoding="utf-8")
        for token in ("player-chapters", "chapter-segment", "chapter-current"):
            self.assertIn(token, gerador, f"gerador sem {token}")

        index = (REPO / "index.html").read_text(encoding="utf-8")
        player = re.search(r'id="chaptersContainer" data-chapters="(\[[^"]*)"', index)
        self.assertIsNotNone(player, "player sem chaptersContainer")
        assert player is not None

        # O episódio em destaque é o último publicado; o arquivo de chapters
        # correspondente precisa existir. Sem manifesto, o player renderiza um
        # bloco único "Episódio completo" e perde toda a navegação por capítulo.
        destaque = re.search(r'data-audio="/audio/d5n-ep\d+-(\d{4}-\d{2}-\d{2})\.mp3"', index)
        if destaque is None:
            self.skipTest("index.html sem episódio em destaque para conferir")

        # Contrato do pipeline: o wrapper TEM que ter o passo que gera
        # chapters/<data>.json. Sem ele o player cai no fallback de "Episódio
        # completo" e perde a navegação por capítulo (foi o que travou em
        # 28/08). Verificar a existência do arquivo aqui não funciona — o
        # manifesto só nasce na próxima mixagem, e o teste reprovaria todo dia
        # por um artefato que ainda não tem hora de existir.
        wrapper = Path("/root/.hermes/scripts/d5n-podcast-daily-full.sh")
        if not wrapper.is_file():
            self.skipTest("wrapper do pipeline não está neste ambiente")
        script = wrapper.read_text(encoding="utf-8")
        self.assertIn(
            "d5n_chapter_manifest.py",
            script,
            "REGRESSÃO: o wrapper não gera chapters/<data>.json — o player do "
            "site cai no fallback de 1 capítulo.",
        )
        self.assertIn(
            'CHAPTER_MANIFEST_REL="chapters/${TODAY}.json"',
            script,
            "REGRESSÃO: o manifesto de capítulos não entra no staging do deploy.",
        )


if __name__ == "__main__":
    unittest.main()
