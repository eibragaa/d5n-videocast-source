#!/usr/bin/env python3
"""Check that the public D5N podcast feed and episode enclosure are available."""

import argparse
import email.utils
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date


DEFAULT_FEED_URL = "https://d5n-daily.netlify.app/podcast.xml"
ATOM_NS = "http://www.w3.org/2005/Atom"


class CheckFailure(Exception):
    def __init__(self, check, message):
        super().__init__(message)
        self.check = check


def _request(url, method, timeout):
    request = urllib.request.Request(url, method=method)
    return urllib.request.urlopen(request, timeout=timeout)


def _read_feed(url, timeout):
    with _request(url, "GET", timeout) as response:
        status = response.getcode()
        body = response.read()
    if status != 200:
        raise CheckFailure("feed_http", f"HTTP {status}")
    return body


def _run_attempt(feed_url, expected_guid, timeout):
    results = {}
    enclosure_url = None
    try:
        try:
            xml_data = _read_feed(feed_url, timeout)
            results["feed_http"] = ("OK", "HTTP 200")
        except Exception as exc:
            raise CheckFailure("feed_http", str(exc)) from exc

        try:
            root = ET.fromstring(xml_data)
            channel = root.find("channel")
            if channel is None:
                raise ValueError("canal RSS ausente")
        except Exception as exc:
            raise CheckFailure("xml", f"XML inválido: {exc}") from exc
        results["xml"] = ("OK", "XML parseado")

        atom_link = channel.find(f"{{{ATOM_NS}}}link")
        if atom_link is not None and atom_link.get("rel") == "self" and atom_link.get("href", "").endswith("/podcast.xml"):
            results["atom_self"] = ("OK", "link Atom rel=self aponta para podcast.xml")
        else:
            raise CheckFailure("atom_self", "link Atom rel=self para podcast.xml ausente")

        if channel.find("lastBuildDate") is None or not (channel.findtext("lastBuildDate") or "").strip():
            raise CheckFailure("lastBuildDate", "elemento ausente ou vazio")
        results["lastBuildDate"] = ("OK", "presente")

        items = channel.findall("item")
        matching = [item for item in items if (item.findtext("guid") or "").strip() == expected_guid]
        if not matching:
            raise CheckFailure("guid", f"item com guid {expected_guid} ausente")
        # GUIDs duplicados são tolerados: valida-se o primeiro item correspondente.
        item = matching[0]
        guid = item.find("guid")
        if guid.get("isPermaLink") != "false":
            raise CheckFailure("guid", 'atributo isPermaLink deve ser "false"')
        results["guid"] = ("OK", expected_guid)

        pub_date = (item.findtext("pubDate") or "").strip()
        try:
            if not pub_date:
                raise ValueError("ausente")
            email.utils.parsedate_to_datetime(pub_date)
        except Exception as exc:
            raise CheckFailure("pubDate", f"RFC 822 inválido: {exc}") from exc
        results["pubDate"] = ("OK", "RFC 822 válido")

        enclosure = item.find("enclosure")
        if enclosure is None:
            raise CheckFailure("enclosure", "elemento ausente")
        enclosure_url = enclosure.get("url")
        length = enclosure.get("length")
        if not enclosure_url or not length or enclosure.get("type") != "audio/mpeg":
            raise CheckFailure("enclosure", "url, length e type=audio/mpeg são obrigatórios")
        try:
            feed_length = int(length)
            if feed_length < 0:
                raise ValueError("length negativo")
        except ValueError as exc:
            raise CheckFailure("enclosure", f"length inválido: {length}") from exc
        if not enclosure_url.lower().startswith("https://"):
            raise CheckFailure("enclosure", "URL do enclosure deve usar HTTPS")
        results["enclosure"] = ("OK", "HTTPS, audio/mpeg e length presentes")

        try:
            with _request(enclosure_url, "HEAD", timeout) as response:
                status = response.getcode()
                headers = response.headers
            if status != 200:
                raise CheckFailure("enclosure_http", f"HTTP {status}")
        except CheckFailure:
            raise
        except Exception as exc:
            raise CheckFailure("enclosure_http", str(exc)) from exc
        results["enclosure_http"] = ("OK", "HTTP 200")
        content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "audio/mpeg":
            raise CheckFailure("content_type", f"esperado audio/mpeg, recebido {content_type or 'ausente'}")
        results["content_type"] = ("OK", "audio/mpeg")
        server_length = headers.get("Content-Length")
        if server_length is None:
            results["content_length"] = ("AVISO", "servidor não enviou Content-Length")
        else:
            try:
                actual_length = int(server_length)
            except ValueError as exc:
                raise CheckFailure("content_length", f"Content-Length inválido: {server_length}") from exc
            if abs(actual_length - feed_length) > 1024:
                raise CheckFailure("content_length", f"feed={feed_length}, servidor={actual_length} (diferença > 1024 bytes)")
            results["content_length"] = ("OK", f"feed={feed_length}, servidor={actual_length}")
        return results, enclosure_url, None
    except CheckFailure as exc:
        results[exc.check] = ("ERRO", str(exc))
        return results, enclosure_url, exc


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--base-url", default=DEFAULT_FEED_URL)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=20)
    args = parser.parse_args(argv)
    try:
        if date.fromisoformat(args.date).isoformat() != args.date:
            raise ValueError
    except ValueError:
        parser.error("--date deve estar no formato YYYY-MM-DD")
    if not re.fullmatch(r"\d{3}", args.episode):
        parser.error("--episode deve conter exatamente três dígitos")
    if args.timeout <= 0 or args.retries < 0 or args.retry_delay < 0:
        parser.error("timeout deve ser positivo; retries e retry-delay não podem ser negativos")
    if not args.base_url.lower().startswith(("https://", "http://")):
        parser.error("--base-url deve ser uma URL HTTP(S)")
    return args


def main(argv=None):
    args = _parse_args(argv)
    feed_url = args.base_url
    expected_guid = f"d5n-{args.date}-ep{args.episode}"
    final_results = {}
    enclosure_url = None
    success = False
    for attempt in range(1, args.retries + 2):
        print(f"Tentativa {attempt}/{args.retries + 1}: GET {feed_url}")
        results, found_enclosure, failure = _run_attempt(feed_url, expected_guid, args.timeout)
        if found_enclosure:
            enclosure_url = found_enclosure
        final_results = results
        if failure is None:
            success = True
            break
        if attempt <= args.retries:
            print(f"Tentativa {attempt} falhou em {failure.check}: {failure}; aguardando {args.retry_delay:g}s")
            time.sleep(args.retry_delay)
    print(f"URL do feed testado: {feed_url}")
    print(f"URL do enclosure testado: {enclosure_url or 'não identificada'}")
    ordered = ("feed_http", "xml", "atom_self", "lastBuildDate", "guid", "pubDate", "enclosure", "enclosure_http", "content_type", "content_length")
    for name in ordered:
        if name in final_results:
            status, message = final_results[name]
            print(f"{status} {name}" + (f": {message}" if status != "OK" else ""))
        elif not success:
            # Tentativa incompleta é falha verificada, nunca sucesso implícito.
            print(f"ERRO {name}: não verificado devido a falha anterior")
    print(f"RESULTADO: {'OK' if success else 'ERRO'} — data {args.date}, episódio {args.episode}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
