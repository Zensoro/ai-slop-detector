#!/usr/bin/env python3
"""GitHub Action entry: score a PR/issue and label + comment if flagged.

Reads the event payload from GITHUB_EVENT_PATH, scores the body, and (when
flagged) adds the `ai-slop:needs-review` label plus an explanatory comment.
Pure stdlib; no third-party deps; no external services -> $0 to run.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scorer import load_signals, score_text, verdict, explain, THRESHOLD

# Author associations we NEVER flag (internal/maintainer tooling).
TRUSTED_ASSOCIATIONS = {"MEMBER", "OWNER", "COLLABORATOR"}
# Points at real GitHub by default; overridable for tests / GHES / self-hosted.
API = os.environ.get("AI_SLOP_API", "https://api.github.com").rstrip("/")


def github_api(method, url, token, payload=None, retries=3):
    """Call the GitHub REST API with retry/backoff on transient failures.

    4xx (client) errors are raised immediately; 429 waits for Retry-After;
    5xx / network errors retry with exponential backoff. A hard failure
    raises RuntimeError so the caller can degrade gracefully instead of
    blowing up the whole Action run.
    """
    data = json.dumps(payload).encode() if payload is not None else None
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            req.add_header("User-Agent", "ai-slop-detector")
            if data:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", "5") or 5)
                print(
                    f"rate limited (429), waiting {wait}s (attempt {attempt + 1}/{retries})",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            if e.code >= 500:
                print(
                    f"server error {e.code}, retrying (attempt {attempt + 1}/{retries})",
                    file=sys.stderr,
                )
                time.sleep(2 * (attempt + 1))
                continue
            raise  # 4xx: deterministic, no point retrying
        except (urllib.error.URLError, OSError) as e:
            last_err = e
            print(
                f"network error ({e}), retrying (attempt {attempt + 1}/{retries})",
                file=sys.stderr,
            )
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GitHub API request failed after {retries} attempts: {last_err}")


def _main():
    token = os.environ.get("GITHUB_TOKEN")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    repo = os.environ.get("GITHUB_REPOSITORY")
    signals_path = os.environ.get("SIGNALS_PATH")
    threshold = float(os.environ.get("THRESHOLD", THRESHOLD))
    auto_close = os.environ.get("AUTO_CLOSE", "false").lower() == "true"
    close_threshold = float(os.environ.get("CLOSE_THRESHOLD", "0.9"))
    close_prs = os.environ.get("CLOSE_PRS", "false").lower() == "true"

    if not (token and event_path and repo):
        print("Missing GITHUB_TOKEN / GITHUB_EVENT_PATH / GITHUB_REPOSITORY", file=sys.stderr)
        sys.exit(1)

    with open(event_path, encoding="utf-8") as f:
        event = json.load(f)

    is_pr = bool(event.get("pull_request"))
    if is_pr:
        obj = event["pull_request"]
    elif event.get("issue"):
        obj = event["issue"]
    else:
        print("Event has no pull_request/issue; skipping.")
        return

    body = (obj.get("body") or "").strip()
    number = obj.get("number")
    association = obj.get("author_association", "")
    login = (obj.get("user") or {}).get("login", "")

    if len(body) < 20:
        print(f"#{number} body too short ({len(body)} chars); skipping.")
        return

    if association in TRUSTED_ASSOCIATIONS:
        print(f"#{number} author association={association} is trusted; skipping.")
        return
    if login.endswith("[bot]"):
        print(f"#{number} author {login} is a bot; skipping.")
        return

    signals = load_signals(signals_path)
    score, hits = score_text(body, signals)
    label = verdict(score, threshold)
    print(f"#{number} score={score:.2f} hits={hits} label={label}")

    if not label:
        return

    base = f"{API}/repos/{repo}/issues/{number}"
    # Add label (idempotent — GitHub dedupes).
    github_api("POST", f"{base}/labels", token, {"labels": [label]})
    comment = explain(score, hits, threshold)
    if comment:
        github_api("POST", f"{base}/comments", token, {"body": comment})
    print(f"Flagged #{number} with label `{label}` and explanatory comment.")

    # P2 — delegated triage: optional auto-close. OFF by default; only at very
    # high confidence; members/bots already returned above so can't be closed.
    if auto_close and score >= close_threshold:
        if is_pr and not close_prs:
            print(f"#{number} is a PR; auto-close disabled for PRs (close_prs=false).")
        else:
            close_note = (
                f"🤖 **Auto-closed** by AI-slop detector: score {score:.2f} ≥ "
                f"close threshold {close_threshold:.2f}. This is a *probabilistic* "
                f"flag, not a judgment. If this was a false positive, just reply "
                f"and a maintainer will reopen it."
            )
            github_api("POST", f"{base}/comments", token, {"body": close_note})
            github_api("PATCH", f"{base}", token, {"state": "closed"})
            print(f"Auto-closed #{number} (score={score:.2f}).")


def main():
    """Entry point. Degrades gracefully instead of failing the whole Action."""
    try:
        _main()
    except Exception as e:  # noqa: BLE001 — never let one item kill the Action
        print(f"ai-slop-detector error (non-fatal): {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
