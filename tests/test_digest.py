import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from digest import build_digest


def _item(n, body, is_pr=False, author="someuser"):
    it = {
        "number": n,
        "title": f"Sample item {n}",
        "body": body,
        "html_url": f"https://github.com/o/r/issues/{n}",
        "user": {"login": author},
        "created_at": "2026-08-04T00:00:00Z",
    }
    if is_pr:
        it["pull_request"] = {"url": "x"}
    return it


AI_BODY = "## Summary\nDid a thing.\n\n## Test\nAdded tests. ✅"
HUMAN_BODY = "fixes a typo in the readme"


def test_build_digest_counts_and_scores():
    items = [
        _item(1, AI_BODY, is_pr=True, author="alice"),
        _item(2, HUMAN_BODY, author="bob"),
        _item(3, AI_BODY, author="carol"),
    ]
    md, stats = build_digest(items, "o/r", days=7)
    assert stats["total"] == 3
    assert stats["pr_n"] == 1
    assert stats["issue_n"] == 2
    assert stats["avg"] > 0.5  # two AI bodies dominate
    # signal breakdown present
    assert "markdown_section_headers" in stats["signals"]
    assert "checkmark_emoji" in stats["signals"]
    # markdown structure: header + table + rows
    assert "# 🛡️ AI-Slop Weekly Digest" in md
    assert "| # | type | score | signals | author |" in md
    assert "[1](https://github.com/o/r/issues/1)" in md
    # sorted highest first -> #1 or #3 (both AI) before #2 (human)
    assert md.index("[1]") < md.index("[2]") or md.index("[3]") < md.index("[2]")


def test_build_digest_empty():
    md, stats = build_digest([], "o/r", days=7)
    assert stats["total"] == 0
    assert stats["avg"] == 0.0
    assert "_(none)_" in md
    assert "| — | — | — | — | — |" in md


if __name__ == "__main__":
    test_build_digest_counts_and_scores()
    test_build_digest_empty()
    print("ALL DIGEST TESTS PASSED")
