import importlib.util
import io
import contextlib
import unittest
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path


REPO = Path(__file__).parents[1]
MODULE_PATH = REPO / "scripts" / "d5n_public_feed_check.py"

DATE = "2026-09-29"
EPISODE = "075"
GUID = "d5n-2026-09-29-ep075"
FEED_URL = "https://d5n-daily.netlify.app/podcast.xml"
ENCLOSURE_URL = "https://d5n-daily.netlify.app/audio/d5n-ep075-2026-09-29.mp3"
LENGTH = "11579602"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_item(guid=GUID, pubdate="Tue, 29 Sep 2026 00:00:00 -0400", enclosure_url=ENCLOSURE_URL,
              length=LENGTH, enclosure_type="audio/mpeg"):
    enclosure = ""
    if enclosure_type is not None:
        enclosure = f'<enclosure url="{enclosure_url}" length="{length}" type="{enclosure_type}"/>'
    return (
        "    <item>\n"
        f"      <title>D5N · Episódio #{int(EPISODE)} — {DATE}</title>\n"
        f'      <guid isPermaLink="false">{guid}</guid>\n'
        f"      <pubDate>{pubdate}</pubDate>\n"
        f"      {enclosure}\n"
        "    </item>"
    )


def make_feed(items):
    body = "\n".join(items) if items else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>Hoje no Drop Five News</title>\n"
        f'    <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml"/>\n'
        "    <lastBuildDate>Tue, 29 Sep 2026 03:03:34 -0400</lastBuildDate>\n"
        f"{body}\n"
        "  </channel>\n"
        "</rss>"
    ).encode("utf-8")


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", status=200, headers=None):
        super().__init__(body)
        self._status = status
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value

    def getcode(self):
        return self._status

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class PublicFeedCheckTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(MODULE_PATH, "d5n_public_feed_check")
        self.original_urlopen = urllib.request.urlopen
        self.calls = []

    def tearDown(self):
        urllib.request.urlopen = self.original_urlopen

    def invoke(self, responder, retries=0):
        def fake_urlopen(request, timeout=None):
            url = request.full_url
            method = request.get_method()
            self.calls.append((url, method))
            outcome = responder(url, method)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        urllib.request.urlopen = fake_urlopen
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = self.module.main(
                ["--date", DATE, "--episode", EPISODE, "--retries", str(retries),
                 "--retry-delay", "0", "--timeout", "5"]
            )
        return code, buffer.getvalue()

    @staticmethod
    def ok_responder(feed_body, enclosure_length=LENGTH):
        def responder(url, method):
            if method == "GET":
                return FakeResponse(feed_body)
            return FakeResponse(
                b"",
                status=200,
                headers={"Content-Type": "audio/mpeg", "Content-Length": enclosure_length},
            )
        return responder

    def test_valid_feed_and_enclosure(self):
        feed = make_feed([make_item()])
        code, output = self.invoke(self.ok_responder(feed))
        self.assertEqual(code, 0, output)
        self.assertIn("OK guid", output)
        self.assertIn("OK enclosure_http", output)
        self.assertIn("OK content_length", output)
        self.assertIn("RESULTADO: OK", output)
        self.assertNotIn("ERRO", output)

    def test_missing_guid_fails(self):
        feed = make_feed([make_item(guid="d5n-2026-01-01-ep001")])
        code, output = self.invoke(self.ok_responder(feed))
        self.assertNotEqual(code, 0)
        self.assertIn("ERRO guid", output)

    def test_malformed_pubdate_fails(self):
        feed = make_feed([make_item(pubdate="29/09/2026")])
        code, output = self.invoke(self.ok_responder(feed))
        self.assertNotEqual(code, 0)
        self.assertIn("ERRO pubDate", output)

    def test_wrong_enclosure_type_or_http_url_fails(self):
        feed = make_feed([make_item(enclosure_type="text/html")])
        code, output = self.invoke(self.ok_responder(feed))
        self.assertNotEqual(code, 0)
        self.assertIn("ERRO enclosure", output)

        self.calls.clear()
        feed = make_feed([make_item(enclosure_url="http://d5n-daily.netlify.app/audio/x.mp3")])
        code, output = self.invoke(self.ok_responder(feed))
        self.assertNotEqual(code, 0)
        self.assertIn("ERRO enclosure", output)

    def test_feed_404_retries_and_fails(self):
        def responder(url, method):
            return urllib.error.HTTPError(FEED_URL, 404, "Not Found", {}, None)

        code, output = self.invoke(responder, retries=2)
        self.assertNotEqual(code, 0)
        self.assertIn("Tentativa 1/3", output)
        self.assertIn("Tentativa 3/3", output)
        self.assertEqual(len([c for c in self.calls if c == (FEED_URL, "GET")]), 3)
        self.assertIn("ERRO feed_http", output)

    def test_duplicate_guid_is_accepted(self):
        item = make_item()
        feed = make_feed([item, item])
        code, output = self.invoke(self.ok_responder(feed))
        self.assertEqual(code, 0, output)

    def test_enclosure_length_mismatch_fails(self):
        feed = make_feed([make_item()])
        code, output = self.invoke(self.ok_responder(feed, enclosure_length="999"))
        self.assertNotEqual(code, 0)
        self.assertIn("ERRO content_length", output)


if __name__ == "__main__":
    unittest.main()
