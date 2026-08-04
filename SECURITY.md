# Security Policy

## What the bot can do

AI-Slop-Detector only ever writes to items **it has itself flagged**:

- adds the `ai-slop:needs-review` label,
- posts a comment,
- optionally closes an item — but **only** when you opt in via `auto_close`,
  **only** at score ≥ `close_threshold` (default `0.9`, i.e. very high
  confidence), **never** for members / owners / collaborators / bots, and
  **never** for PRs unless you also set `close_prs: true`.

It uses the workflow's `github.token`, which GitHub scopes to the single repo
the workflow runs in. It:

- never force-pushes or touches any git ref,
- never reads or exfiltrates secrets / env vars,
- never calls any external service (no analytics, no telemetry, no LLM API).

## Reporting a vulnerability

Please open a **security advisory** on the repository
(Security → Report a vulnerability) rather than a public issue. We aim to
respond within a few days.

## False positives

This is a *probabilistic* heuristic, not a verdict. If it flags you, just
reply on the item and a maintainer will clear / reopen it. Don't argue with
the bot — it has no feelings and no merge rights.
