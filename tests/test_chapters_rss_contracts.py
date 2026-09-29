"""Contrato do RSS de capítulos dos três programas.

Um feed pode parsear como XML e ainda assim ser rejeitado pelo player. Foi
exatamente isso que aconteceu duas vezes: podcast:chapters com filhos (mistura
de namespace) e psc:chapter sem start (o Podlove exige). Nos dois casos o feed
inteiro parava de carregar no leitor, e nada na validação existente acusava —
ela só checava parse e presença da tag.

Estes testes existem para reprovar no CI, não para documentar o formato.
"""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PODCAST_NS = "https://podcastindex.org/namespace/1.0"
PSC_NS = "http://podlove.org/simple-chapters"

FEEDS = (
    ("D5N", REPO / "podcast.xml"),
    ("MC", REPO / "manha-conectada.xml"),
    ("FM", REPO / "fechamento.xml"),
)


def _items(feed: Path) -> list[ET.Element]:
    return ET.parse(feed).getroot().findall(".//item")


class ChaptersRssContractTests(unittest.TestCase):
    def test_podcast_chapters_is_empty_element(self):
        """podcast:chapters leva APENAS src. Filhos reprovam leitor estrito.

        O padrão só admite filhos quando o src é o próprio áudio com atoms ID3
        CHAP/ctoc. Nossos mixers não os escrevem, então qualquer filho aqui é
        estrutura inválida — e o sintoma é o feed inteiro parando de carregar,
        não só os capítulos sumindo.
        """
        for nome, feed in FEEDS:
            if not feed.is_file():
                self.skipTest(f"{nome}: feed ausente")
            root = ET.parse(feed).getroot()
            for tag in root.iter(f"{{{PODCAST_NS}}}chapters"):
                self.assertEqual(
                    len(list(tag)),
                    0,
                    f"{nome}: podcast:chapters tem {len(list(tag))} filho(s); "
                    "deve ser elemento vazio com apenas src",
                )
                self.assertTrue(
                    tag.get("src"),
                    f"{nome}: podcast:chapters sem atributo src",
                )

    def test_psc_chapter_always_has_start(self):
        """psc:chapter sem start não navega: o player ignora ou joga no lugar errado."""
        for nome, feed in FEEDS:
            if not feed.is_file():
                self.skipTest(f"{nome}: feed ausente")
            root = ET.parse(feed).getroot()
            for chapter in root.iter(f"{{{PSC_NS}}}chapter"):
                self.assertIsNotNone(
                    chapter.get("start"),
                    f"{nome}: psc:chapter sem start — "
                    f"title={chapter.get('title')!r}",
                )
                self.assertTrue(
                    chapter.get("title"),
                    f"{nome}: psc:chapter sem title — start={chapter.get('start')}",
                )

    def test_chapter_starts_are_monotonic_within_item(self):
        """Capítulos fora de ordem fazem o player navegar para trás."""
        for nome, feed in FEEDS:
            if not feed.is_file():
                self.skipTest(f"{nome}: feed ausente")
            for item in _items(feed):
                starts = []
                for psc in item.iter(f"{{{PSC_NS}}}chapters"):
                    for chapter in psc.findall(f"{{{PSC_NS}}}chapter"):
                        raw = chapter.get("start", "0")
                        parts = [int(p) for p in re.split(r"[:]", raw) if p.isdigit()]
                        seconds = 0
                        for part in parts:
                            seconds = seconds * 60 + part
                        starts.append(seconds)
                self.assertEqual(
                    starts, sorted(starts),
                    f"{nome}: capítulos fora de ordem em "
                    f"{item.findtext('guid', '?')}",
                )

    def test_podcast_chapters_src_is_a_chapters_document(self):
        """src aponta para JSON de capítulos, nunca para o .mp3.

        O .mp3 só resolveria com atoms ID3 CHAP/ctoc embutidos. Sem eles o link
        não abre nada, e era o que acontecia.
        """
        for nome, feed in FEEDS:
            if not feed.is_file():
                self.skipTest(f"{nome}: feed ausente")
            root = ET.parse(feed).getroot()
            for tag in root.iter(f"{{{PODCAST_NS}}}chapters"):
                src = tag.get("src", "")
                self.assertNotIn(
                    ".mp3", src,
                    f"{nome}: podcast:chapters src aponta para MP3 ({src})",
                )
                self.assertTrue(
                    src.endswith(".json"),
                    f"{nome}: podcast:chapters src não é JSON de capítulos: {src}",
                )


if __name__ == "__main__":
    unittest.main()
