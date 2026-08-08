"""Unit tests for run.py error handling and human-signal guard rails.

Run: python tests/test_run.py
"""
import os
import sys
import json
import tempfile
import urllib.error
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import run as run_mod  # noqa: E402


def _call_main(payload):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        path = f.name
    saved = dict(os.environ)
    os.environ.update(
        {
            "GITHUB_TOKEN": "test-token",
            "GITHUB_EVENT_PATH": path,
            "GITHUB_REPOSITORY": "o/r",
            "AI_SLOP_API": "http://127.0.0.1:9999",
            "SIGNALS_PATH": "",
            "THRESHOLD": "0.6",
        }
    )
    try:
        with mock.patch.object(run_mod, "github_api") as g:
            run_mod._main()
            return g
    finally:
        os.unlink(path)
        os.environ.clear()
        os.environ.update(saved)


def _http_error(code, retry_after=None):
    hdrs = {}
    if retry_after is not None:
        hdrs["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError("http://x", code, "err", hdrs, None)


class TestShortBodySkip(unittest.TestCase):
    def test_short_body_skipped_no_api_calls(self):
        g = _call_main(
            {"action": "opened", "issue": {
                "number": 1, "body": "tiny", "author_association": "NONE",
                "user": {"login": "x"}}}
        )
        g.assert_not_called()

    def test_empty_body_skipped_no_api_calls(self):
        g = _call_main(
            {"action": "opened", "issue": {
                "number": 2, "body": None, "author_association": "NONE",
                "user": {"login": "x"}}}
        )
        g.assert_not_called()


class TestHumanGuard(unittest.TestCase):
    def test_human_issue_referencing_number_not_flagged(self):
        g = _call_main(
            {"action": "opened", "issue": {
                "number": 3, "body": "just a typo fix, see #42",
                "author_association": "NONE", "user": {"login": "x"}}}
        )
        g.assert_not_called()

    def test_ai_style_body_is_flagged(self):
        g = _call_main(
            {"action": "opened", "issue": {
                "number": 4,
                "body": "## Summary\nAdd feature\n\n## Testing\n- ✅ done",
                "author_association": "NONE", "user": {"login": "x"}}}
        )
        g.assert_called()


class TestApiRetry(unittest.TestCase):
    def test_429_waits_and_retries(self):
        calls = []

        def fake_urlopen(req, timeout=20):
            calls.append(1)
            if len(calls) < 3:
                raise _http_error(429, retry_after=0)
            m = mock.MagicMock()
            m.read.return_value = b"{}"
            m.__enter__.return_value = m
            return m

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with mock.patch("time.sleep") as slp:
                out = run_mod.github_api("GET", "http://x", "t")
        self.assertEqual(out, {})
        self.assertEqual(len(calls), 3)  # 2 failures + 1 success
        slp.assert_called()

    def test_5xx_retries(self):
        calls = []

        def fake_urlopen(req, timeout=20):
            calls.append(1)
            if len(calls) < 2:
                raise _http_error(500)
            m = mock.MagicMock()
            m.read.return_value = b"{}"
            m.__enter__.return_value = m
            return m

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with mock.patch("time.sleep"):
                run_mod.github_api("GET", "http://x", "t")
        self.assertEqual(len(calls), 2)

    def test_4xx_does_not_retry(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(404)):
            with self.assertRaises(urllib.error.HTTPError):
                run_mod.github_api("GET", "http://x", "t")

    def test_exhausts_retries_raises_runtime_error(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=_http_error(500)
        ):
            with mock.patch("time.sleep"):
                with self.assertRaises(RuntimeError):
                    run_mod.github_api("GET", "http://x", "t")


if __name__ == "__main__":
    unittest.main()
