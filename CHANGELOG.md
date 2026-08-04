# Changelog

All notable changes to AI-Slop-Detector are documented here. This project
follows a lightweight versioning scheme: `v0.x` = pre-1.0, API may still shift.

---

## v0.1.0 — 2026-08-05

First publishable release. A zero-cost, zero-dependency GitHub Action that
flags probable AI-generated PRs / issues for open-source maintainers.

### Why this exists

~17 million AI-generated PRs per month are flooding open source. curl dropped
its bounty program and the Jazzband collective dissolved under the load.
Meanwhile, off-the-shelf "AI slop detectors" are essentially non-existent
(one 0-star repo at last count). This tool is the defense side of that gap.

### Features

**P0 — Label + comment funnel (the distribution mechanism)**
- On PR / Issue `opened`, scores the body with pure structural regex features.
- Flags `ai-slop:needs-review` + a comment that always shows the **score and
  the exact signals triggered** — probabilistic language, never an accusation.
- Members / owners / collaborators / bots are never flagged.

**P1 — Aggregation + badges (the part that actually gets stars)**
- `aggregate.py` pulls real IssuesEvent data from the public ClickHouse GH
  Archive instance and ranks repos by AI-slop %, producing a shareable
  leaderboard (`site/index.html`) + a per-repo badge SVG.
- Self-serve badge generator (`src/badge.py`): any maintainer can render their
  own badge locally, no network.

**P2 — Delegated triage (the "I don't want to babysit it" layer)**
- Optional auto-close (`auto_close`, default off; only at score ≥ 0.9; issues
  only by default; never members / bots).
- Weekly digest (`digest.yml`): a markdown report of the week's flagged items
  (count, avg score, signal breakdown, per-item table), committed to
  `digest/latest.md` and optionally posted to an issue.

### Signals (measured, not guessed)

On the ClickHouse GH Archive (PRs, 2025-07..08, body > 50 chars):

| Signal | AI-signed PR | Human PR (3.6M baseline) | Discrimination |
|---|---|---|---|
| `## Test` / `## Testing` | 78.3% | 0.8% | ~98× |
| `##` section headers (Summary/Problem/Context…) | 95.1% | 8.2% | ~11.6× |
| ✅ emoji | 17.9% | 0% | near-perfect |
| em-dash (—) | 0.2% | 0.2% | discarded (not discriminative) |

### Cost

$0. No embeddings, no LLM, no external service, no API key. Scoring is pure
regex; the only credential used is GitHub's built-in `github.token`.

### Validation

- Unit tests: `tests/test_scorer.py`, `tests/test_aggregate.py`,
  `tests/test_digest.py` — all pass.
- End-to-end: `tests/test_e2e.py` runs the real action code against a local
  mock GitHub API (label / comment / close / digest paths covered) — passes.
- The leaderboard back-test (16 well-known repos) reproduced known AI-slop
  battlegrounds: tldraw ~69% → godot ~0.5%.

### Publish note

The published repo already uses `Zensoro` as the owner. If you fork it,
replace `Zensoro` with your own GitHub username or org in the usage snippets
(see README → Publishing).
