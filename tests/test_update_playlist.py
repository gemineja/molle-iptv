"""Offline checks for the playlist build. No network: every request is faked.

Run with:  python -m unittest discover -s tests
"""

import io
import os
import sys
import unittest
from unittest import mock

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import update_playlist as up  # noqa: E402


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"#EXTM3U\n", url="https://cdn.example/a.m3u8"):
        self.status_code = status
        self.headers = headers if headers is not None else {"Access-Control-Allow-Origin": "*"}
        self.url = url
        self.raw = io.BytesIO(body)
        self.raw.read = lambda n, decode_content=True, _r=self.raw.read: _r(n)

    def close(self):
        pass


def answering(response=None, raises=None):
    """A session whose get() returns `response` or raises `raises`."""
    s = mock.Mock()
    if raises:
        s.get.side_effect = raises
    else:
        s.get.return_value = response
    return mock.patch.object(up, "session", return_value=s)


class StreamStatus(unittest.TestCase):
    URL = "https://cdn.example/a.m3u8"

    def status(self, **kw):
        with answering(**kw):
            return up.stream_status(self.URL)

    def test_plain_http_is_dead_without_asking(self):
        self.assertEqual(up.stream_status("http://cdn.example/a.m3u8"), "dead")

    def test_open_cors_is_ok(self):
        self.assertEqual(self.status(response=FakeResponse()), "ok")

    def test_echoed_origin_is_ok(self):
        r = FakeResponse(headers={"Access-Control-Allow-Origin": "https://molle-iptv.example"})
        self.assertEqual(self.status(response=r), "ok")

    def test_cors_pinned_elsewhere_is_dead(self):
        r = FakeResponse(headers={"Access-Control-Allow-Origin": "http://pluto.tv"})
        self.assertEqual(self.status(response=r), "dead")

    def test_http_inside_the_manifest_is_dead(self):
        r = FakeResponse(body=b"#EXTM3U\nhttp://cdn.example/low.m3u8\n")
        self.assertEqual(self.status(response=r), "dead")

    def test_refusal_is_restricted_not_dead(self):
        for code in (401, 403, 451):
            self.assertEqual(self.status(response=FakeResponse(status=code)), "restricted")

    def test_busy_server_is_flaky(self):
        for code in (429, 503, 504):
            self.assertEqual(self.status(response=FakeResponse(status=code)), "flaky")

    def test_missing_stream_is_dead(self):
        self.assertEqual(self.status(response=FakeResponse(status=404)), "dead")

    def test_timeout_and_reset_are_flaky(self):
        self.assertEqual(self.status(raises=requests.ReadTimeout()), "flaky")
        self.assertEqual(self.status(raises=requests.ConnectionError()), "flaky")

    def test_bad_certificate_is_dead(self):
        self.assertEqual(self.status(raises=requests.exceptions.SSLError()), "dead")


class Validate(unittest.TestCase):
    def run_validate(self, first, second, previous):
        entries = [(f"#EXTINF:-1,{u}", u) for u in first]
        calls = []

        def fake(batch, timeout):
            calls.append(([u for _, u in batch], timeout))
            source = first if len(calls) == 1 else second
            return [source[u] for _, u in batch]

        with mock.patch.object(up, "check_all", side_effect=fake):
            kept = up.validate(entries, previous)
        return kept, calls

    def test_only_previously_published_soft_failures_are_retried(self):
        first = {"https://a": "ok", "https://b": "flaky", "https://c": "flaky",
                 "https://d": "dead"}
        second = {"https://b": "ok"}
        kept, calls = self.run_validate(first, second, previous={"https://b", "https://d"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], (["https://b"], up.RETRY_TIMEOUT))
        self.assertEqual([u for _, u in kept], ["https://a", "https://b"])
        self.assertEqual(up.STATS["rescued"], 1)

    def test_still_flaky_after_retry_is_dropped(self):
        first = {"https://a": "flaky"}
        kept, calls = self.run_validate(first, {"https://a": "flaky"}, previous={"https://a"})
        self.assertEqual(kept, [])
        self.assertEqual(up.STATS["dead"], 1)

    def test_no_second_pass_without_history(self):
        _, calls = self.run_validate({"https://a": "flaky"}, {}, previous=set())
        self.assertEqual(len(calls), 1)

    def test_restricted_is_kept_and_marked(self):
        kept, _ = self.run_validate({"https://a": "restricted"}, {}, previous=set())
        self.assertIn('tvg-geo="restricted"', kept[0][0])


class Names(unittest.TestCase):
    def test_name_ignores_commas_inside_attributes(self):
        extinf = '#EXTINF:-1 http-user-agent="Mozilla/5.0 (X11, Linux)" tvg-id="x",DR1 (1080p)'
        self.assertEqual(up.channel_name(extinf), "DR1 (1080p)")

    def test_dedupe_keeps_best_resolution_in_first_position(self):
        entries = [
            ('#EXTINF:-1,DR1 (720p)', "https://a"),
            ('#EXTINF:-1,TV2', "https://b"),
            ('#EXTINF:-1,DR1 Ⓖ (1080p) [Geo-blocked]', "https://c"),
        ]
        self.assertEqual([u for _, u in up.dedupe(entries)], ["https://c", "https://b"])


class Enrich(unittest.TestCase):
    def test_fills_country_region_and_restates_group(self):
        meta = {"DR1.dk": {"category": "News", "country": "Denmark", "region": "Europe"}}
        out = up.enrich('#EXTINF:-1 tvg-id="DR1.dk@SD" group-title="Undefined",DR1',
                        meta, {"DR1.dk@SD": "Danish"}, set(), {"DK": "Denmark"},
                        {"DK": "Europe"})
        for attr in ('tvg-country="Denmark"', 'tvg-region="Europe"',
                     'tvg-language="Danish"', 'group-title="News"'):
            self.assertIn(attr, out)

    def test_expands_a_bare_country_code(self):
        out = up.enrich('#EXTINF:-1 tvg-id="Unknown.it" tvg-country="IT",Rai X',
                        {}, {}, set(), {"IT": "Italy"}, {"IT": "Europe"})
        self.assertIn('tvg-country="Italy"', out)
        self.assertIn('tvg-region="Europe"', out)
        self.assertIn('group-title="General"', out)


if __name__ == "__main__":
    unittest.main()
