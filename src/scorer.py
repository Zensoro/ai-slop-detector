"""AI-slop scorer — pure-stdlib structural detector.

Validated signals (ClickHouse GH Archive back-test, 2025-07..08 PRs, body>50 chars):
  S1  ## Markdown section headers
      (Summary|Overview|Problem|Context|Root Cause|Tests?|Testing)
      Summary 82.4% AI vs 0% human; Test/Testing 78.3% AI vs 0.8% human (~98x).  PRIMARY
  S2  ✅ emoji
      17.9% of AI-signed PRs vs 0% of 3.64M human PRs  -> near-perfect clean signal
  Tested and DISCARDED (not discriminative):
      em-dash (—) 0.2% both groups; ## Checklist ~1.2x; ## What/Why/How ~1x.

Score = min(1.0, sum(weights of triggered signals)). Transparent, not a black box.
"""
import re

DEFAULT_SIGNALS = [
    {
        "name": "markdown_section_headers",
        "pattern": r"(?m)^##\s+(Summary|Overview|Problem|Context|Root Cause|Tests?|Testing)\b",
        "weight": 0.8,
    },
    {
        "name": "checkmark_emoji",
        "pattern": r"✅",
        "weight": 0.5,
    },
]

THRESHOLD = 0.6  # default; label only, never auto-close


def load_signals(path=None):
    """Load signals from a TOML file (stdlib tomllib, Python 3.11+).
    Falls back to embedded DEFAULT_SIGNALS if path missing or unparseable."""
    if not path:
        return list(DEFAULT_SIGNALS)
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
        sigs = data.get("signals", [])
        if sigs:
            return [
                {"name": s["name"], "pattern": s["pattern"], "weight": float(s["weight"])}
                for s in sigs
            ]
    except Exception:
        pass
    return list(DEFAULT_SIGNALS)


def score_text(text, signals=None):
    """Return (score in [0,1], list_of_triggered_signal_names)."""
    if not text:
        return 0.0, []
    signals = signals or DEFAULT_SIGNALS
    hits = []
    raw = 0.0
    for s in signals:
        if re.search(s["pattern"], text):
            hits.append(s["name"])
            raw += s["weight"]
    return min(1.0, raw), hits


def verdict(score, threshold=THRESHOLD):
    """Return label name if score crosses threshold, else None."""
    return "ai-slop:needs-review" if score >= threshold else None


def explain(score, hits, threshold=THRESHOLD):
    """Friendly, non-accusatory comment body for the maintainer + author."""
    if not verdict(score, threshold):
        return None
    sigs = ", ".join(hits) if hits else "structural patterns"
    return (
        f"🤖 **AI-slop sniffer** scored this at **{score:.2f}** "
        f"(threshold {threshold:.2f}).\n\n"
        f"Triggered signals: `{sigs}`.\n\n"
        "This is an *automated, probabilistic* flag — not an accusation. "
        "If you're a human contributor, just reply and a maintainer will clear it. "
        "Maintainers: tune or disable via `signals/default.toml`."
    )
