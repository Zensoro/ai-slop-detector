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


if __name__ == "__main__":
    test_ai_flagged()
    test_human_not_flagged()
    test_human_headers_not_flagged()
    test_comment_explains()
    print("ALL TESTS PASSED")
