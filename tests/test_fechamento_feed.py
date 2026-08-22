import hashlib
import importlib.util
import json
import sys
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).parents[1]
SCRIPT = REPO / "fechamento" / "scripts" / "gerar_fechamento_feed.py"


def load_module():
    spec = importlib.util.spec_from_file_location("gerar_fechamento_feed", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"não foi possível carregar {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FechamentoConectadaFeedTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "audio").mkdir()
        (self.repo / "manifests").mkdir(parents=True)

    def add_episode(self, editorial_date="2026-07-31", *, prototype=False):
        audio_name = f"fechamento-{editorial_date}.mp3"
        audio = self.repo / "audio" / audio_name
        audio.write_bytes(b"valid-mp3-fixture" * 40_000)
        manifest = {
            "program": "FECHAMENTO DO MERCADO",
            "date": editorial_date,
            "prototype": prototype,
            "output": str(audio),
            "sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            "audio": {"duration": 297.2, "size": audio.stat().st_size},
            "sources": [
                {"title": "Notícia principal do Brasil"},
                {"title": "Mercados acompanham novos indicadores"},
            ],
        }
        path = self.repo / "manifests" / f"{editorial_date}.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return audio, path

    def test_builds_separate_podcast_feed_with_stable_guid_and_enclosure(self):
        self.add_episode()

        rss, episodes = self.module.build_feed(self.repo)
        root = ET.fromstring(rss)
        item = root.find("./channel/item")
        self.assertIsNotNone(item)
        assert item is not None
        enclosure = item.find("enclosure")
        self.assertIsNotNone(enclosure)
        assert enclosure is not None

        self.assertEqual(len(episodes), 1)
        self.assertEqual(root.findtext("./channel/title"), "Fechamento do Mercado")
        self.assertEqual(
            self.module.IMAGE_URL,
            "https://d5n-daily.netlify.app/fechamento-cover.png",
        )
        self.assertEqual(item.findtext("guid"), "fechamento-2026-07-31")
        self.assertEqual(
            enclosure.get("url"),
            "https://d5n-daily.netlify.app/audio/fechamento-2026-07-31.mp3",
        )
        self.assertEqual(enclosure.get("type"), "audio/mpeg")
        self.assertIn("-0300", item.findtext("pubDate", ""))
        self.assertTrue(self.module.feed_has_episode(rss, "2026-07-31"))
        self.assertFalse(self.module.feed_has_episode(rss, "2026-07-30"))

    def test_rejects_tampered_audio(self):
        audio, _ = self.add_episode()
        audio.write_bytes(audio.read_bytes() + b"tampered")

        with self.assertRaisesRegex(ValueError, "sha256 divergente"):
            self.module.build_feed(self.repo)

    def test_prototype_manifest_is_not_published(self):
        self.add_episode("2026-07-30")
        self.add_episode("2026-07-31", prototype=True)

        rss, episodes = self.module.build_feed(self.repo)

        self.assertEqual([item.editorial_date.isoformat() for item in episodes], ["2026-07-30"])
        self.assertNotIn("fechamento-2026-07-31", rss)


class FechamentoPublisherContractTests(unittest.TestCase):
    def test_netlify_preserves_public_feed_cover_and_audio_urls(self):
        with (REPO / "netlify.toml").open("rb") as stream:
            redirects = tomllib.load(stream)["redirects"]
        rules = {rule["from"]: (rule["to"], rule["status"]) for rule in redirects}

        self.assertEqual(
            rules["/fechamento.xml"],
            ("/fechamento/feeds/fechamento.xml", 200),
        )
        self.assertEqual(
            rules["/fechamento-cover.png"],
            ("/fechamento/assets/fechamento-cover.png", 200),
        )
        self.assertEqual(
            rules["/audio/fechamento-*"],
            ("/fechamento/audio/fechamento-:splat", 200),
        )

    def test_publisher_generates_validates_and_commits_the_feed(self):
        publisher = (REPO / "fechamento" / "scripts" / "publish-fechamento-site.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("gerar_fechamento_feed.py", publisher)
        self.assertIn('--check-date "$RELEASE_DATE"', publisher)
        self.assertIn('index.html "$FEED"', publisher)
        self.assertNotIn("git diff --cached --quiet --exit-code", publisher)


if __name__ == "__main__":
    unittest.main()
