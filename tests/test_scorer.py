import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scorer import score_text, verdict, explain, THRESHOLD

AI_BODY = """## Summary
This PR adds a new feature.

## Problem
The old code was slow.

## Overview
We refactored everything. ✅
"""

HUMAN_BODY = "Fixes a bug in the parser where empty input crashed."

HUMAN_WITH_HEADERS = """## How to reproduce
1. run it
2. see crash
"""


def test_ai_flagged():
    score, hits = score_text(AI_BODY)
    assert score >= THRESHOLD, score
    assert "markdown_section_headers" in hits
    assert "checkmark_emoji" in hits
    assert verdict(score) == "ai-slop:needs-review"


def test_human_not_flagged():
    score, hits = score_text(HUMAN_BODY)
    assert score == 0.0
    assert verdict(score) is None


def test_human_headers_not_flagged():
    # '## How to reproduce' is not in our AI keyword set
    score, hits = score_text(HUMAN_WITH_HEADERS)
    assert verdict(score) is None


def test_comment_explains():
    score, hits = score_text(AI_BODY)
    c = explain(score, hits)
    assert c and "probabilistic" in c and "not an accusation" in c


def test_human_signal_subtracts():
    # A body with AI markers that ALSO references an issue: score drops below
    # threshold thanks to the human signal (0.8 - 0.3 = 0.5 < 0.6).
    body = "## Summary\nFixes the issue. references #42"
    score, hits = score_text(body)
    assert score < THRESHOLD, score
    assert verdict(score) is None
    # hits only contains positive signals, never the human signal
    assert "issue_reference" not in hits


def test_ai_with_reference_still_flagged():
    # AI-templated PR that cites an issue: 0.8 + 0.5 - 0.3 = 1.0 → still flagged.
    body = "## Summary\nAdd feature\n\n## Testing\n- ✅ done\n\nFixes #99"
    score, hits = score_text(body)
    assert score >= THRESHOLD, score
    assert verdict(score) == "ai-slop:needs-review"


if __name__ == "__main__":
    test_ai_flagged()
    test_human_not_flagged()
    test_human_headers_not_flagged()
    test_comment_explains()
    test_human_signal_subtracts()
    test_ai_with_reference_still_flagged()
    print("ALL TESTS PASSED")
