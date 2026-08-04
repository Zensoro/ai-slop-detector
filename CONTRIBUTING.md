# Contributing

Thanks for wanting to improve AI-Slop-Detector. It's intentionally tiny and
dependency-free so anyone can audit it.

## Principles

- **Pure standard library only.** No third-party packages in `src/`. The detector
  must run on GitHub's default `ubuntu-latest` runner with just `setup-python`.
- **No network calls at scoring time** except the GitHub API to label / comment /
  close an item — and only using the workflow's provided `github.token`.
- **Signals are config, not code.** Adding a detector signal = adding a
  `[[signals]]` block in `signals/default.toml`. Do not hardcode new patterns in
  Python.

## Adding a signal

1. Propose the regex + weight in `signals/default.toml`.
2. Back it with data: show discriminability (AI% vs human%) from a real sample,
   or a ClickHouse GH Archive query. A good signal is ≥ ~5× more common in
   AI-signed content than in the 3.6M-human baseline.
3. Add or adjust a unit test in `tests/test_scorer.py`.

## Running the tests

```bash
python tests/test_scorer.py     # scoring + signal fallback
python tests/test_aggregate.py  # leaderboard/badge build (offline)
python tests/test_digest.py     # weekly digest aggregation (offline)
python tests/test_e2e.py        # real run.py/digest.py vs a local mock GitHub API
```

The full suite should print `ALL TESTS PASSED` / `ALL E2E TESTS PASSED`.

## End-to-end check (no real GitHub needed)

`tests/test_e2e.py` runs the *real* `src/run.py` / `src/digest.py` against a
local mock of the GitHub REST API (labels POST, comments POST, issue PATCH
close, issues GET). To point the code at a different API (GitHub Enterprise /
your own mock), set `AI_SLOP_API`.

## Pull requests

- Keep changes small and focused.
- Update `README.md` / `CHANGELOG.md` if behavior changes.
- By contributing you agree your contributions are licensed under the MIT License.
