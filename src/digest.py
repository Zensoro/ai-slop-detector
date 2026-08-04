#!/usr/bin/env python3
"""P2: Weekly delegation digest.

Collects items labeled `ai-slop:needs-review` in the last N days, re-scores
them for a breakdown, and emits a markdown digest. The pure aggregation
(`build_digest`) is unit-tested without any network; `fetch_labeled` talks to
the GitHub REST API and is only invoked from `main()`.

$0: uses the workflow's GITHUB_TOKEN, no extra services.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scorer import load_signals, score_text, THRESHOLD

API = os.environ.get("AI_SLOP_API", "https://api.github.com").rstrip("/")
LABEL = "ai-slop:needs-review"


def _gh_get(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "ai-slop-detector")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_labeled(repo, token, days=7, label=LABEL, per_page=100):
    """Return items (issues + PRs) carrying `label` created in the last `days`.

    The API `since` param filters on updated_at, so we additionally filter by
    created_at to honor the true window.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    items, page = [], 1
    while True:
        url = (
            f"{API}/repos/{repo}/issues"
            f"?labels={urllib.parse.quote(label)}&state=all"
            f"&since={since}&per_page={per_page}&page={page}"
        )
        batch = _gh_get(url, token)
        if not isinstance(batch, list) or not batch:
            break
        for it in batch:
            created = it.get("created_at", "")
            if created < since:
                continue
            # Pull requests carry a `pull_request` key; skip them if you only
            # want issues, but here we keep both for a full picture.
            items.append(it)
        if len(batch) < per_page:
            break
        page += 1
    return items


def build_digest(items, repo, days=7, signals=None):
    """Pure aggregation. Returns (markdown_str, stats_dict). No network."""
    signals = signals or load_signals()
    pr_n = issue_n = 0
    score_sum = 0.0
    signal_counter = {}
    rows = []
    for it in items:
        body = it.get("body") or ""
        score, hits = score_text(body, signals)
        is_pr = "pull_request" in it
        pr_n += int(is_pr)
        issue_n += int(not is_pr)
        score_sum += score
        for h in hits:
            signal_counter[h] = signal_counter.get(h, 0) + 1
        rows.append(
            {
                "number": it.get("number"),
                "title": (it.get("title") or "").replace("|", "/").replace("\n", " "),
                "url": it.get("html_url", ""),
                "is_pr": is_pr,
                "score": score,
                "hits": hits,
                "author": (it.get("user") or {}).get("login", ""),
            }
        )

    total = len(items)
    avg = score_sum / total if total else 0.0
    top = sorted(rows, key=lambda r: r["score"], reverse=True)

    lines = [
        f"# 🛡️ AI-Slop Weekly Digest — `{repo}`",
        "",
        f"_Window: last {days} days · generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        f"- **Flagged this week:** {total}",
        f"  - Issues: {issue_n} · PRs: {pr_n}",
        f"- **Avg AI-slop score:** {avg:.2f}",
        "- **Top triggered signals:** "
        + (
            ", ".join(f"`{k}` ×{v}" for k, v in sorted(
                signal_counter.items(), key=lambda kv: kv[1], reverse=True
            ))
            or "_(none)_"
        ),
        "",
        "## Items (highest score first)",
        "",
        "| # | type | score | signals | author |",
        "|---|---|---|---|---|",
    ]
    for r in top:
        kind = "PR" if r["is_pr"] else "issue"
        sig = ", ".join(r["hits"]) or "—"
        lines.append(
            f"| [{r['number']}]({r['url']}) | {kind} | {r['score']:.2f} | {sig} | {r['author']} |"
        )
    if not top:
        lines.append("| — | — | — | — | — |")
    lines += [
        "",
        "> Scores are probabilistic structural estimates, not verdicts. "
        "Items labeled `ai-slop:needs-review` still need a human glance.",
        "",
    ]
    return "\n".join(lines), {
        "total": total,
        "pr_n": pr_n,
        "issue_n": issue_n,
        "avg": avg,
        "signals": signal_counter,
    }


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--out", default="digest/latest.md")
    p.add_argument("--comment-issue", type=int, default=0,
                   help="If set, post the digest as a comment on this issue number.")
    args = p.parse_args()

    if not (args.repo and args.token):
        print("Missing --repo / --token (or GITHUB_REPOSITORY / GITHUB_TOKEN).", file=sys.stderr)
        sys.exit(1)

    items = fetch_labeled(args.repo, args.token, days=args.days)
    md, stats = build_digest(items, args.repo, days=args.days)
    print(f"Digest: {stats['total']} items ({stats['issue_n']} issues, {stats['pr_n']} PRs), "
          f"avg score {stats['avg']:.2f}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {args.out}")

    if args.comment_issue:
        url = f"{API}/repos/{args.repo}/issues/{args.comment_issue}/comments"
        _gh_post(url, args.token, {"body": md})
        print(f"Posted digest to issue #{args.comment_issue}")


def _gh_post(url, token, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "ai-slop-detector")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


if __name__ == "__main__":
    main()
