#!/usr/bin/env python3
"""One-command real GitHub integration test for AI-Slop-Detector.

Creates a throwaway test repo, uploads the Action + workflows, and opens a
real AI-style issue, a real human issue, and a real AI-style PR so the Action
actually runs on GitHub's servers (labels, comments, auto-close, digest).

Zero third-party deps — uses only urllib against api.github.com
(or AI_SLOP_API if you point it at a GHES / mock).

Usage:
  python scripts/bootstrap_repo.py --token ghp_xxx [--name ai-slop-test] [--org myorg]
  # or via env:
  GITHUB_TOKEN=ghp_xxx python scripts/bootstrap_repo.py

This creates real resources under YOUR account/org. The repo is created
private; delete it when done (`gh repo delete --yes <full_name>`).
"""
import os
import sys
import json
import base64
import argparse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.environ.get("AI_SLOP_API", "https://api.github.com").rstrip("/")

# (local_path, repo_path) — only what the Action needs to run.
FILES = [
    ("action.yml", "action.yml"),
    ("src/run.py", "src/run.py"),
    ("src/scorer.py", "src/scorer.py"),
    ("src/badge.py", "src/badge.py"),
    ("src/digest.py", "src/digest.py"),
    ("signals/default.toml", "signals/default.toml"),
    (".github/workflows/ai-slop.yml", ".github/workflows/ai-slop.yml"),
    (".github/workflows/digest.yml", ".github/workflows/digest.yml"),
    ("README.md", "README.md"),
]

AI_BODY = "## Summary\nAdds an automated check for AI-generated contributions.\n\n## Problem\nMaintainers are drowning in slop.\n\n## Test\nAdded unit tests. ✅"
HUMAN_BODY = "Small fix: the README had a typo in the install command."


def gh(method, path, token, payload=None):
    url = f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "ai-slop-bootstrap")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode()
        return json.loads(body) if body else {}


def create_repo(token, name, org=None, private=True):
    payload = {"name": name, "private": private, "auto_init": True,
               "has_issues": True}
    if org:
        return gh("POST", f"/orgs/{org}/repos", token, payload)
    return gh("POST", "/user/repos", token, payload)


def upload_file(token, repo, repo_path, local_path, message):
    with open(os.path.join(ROOT, local_path), "rb") as f:
        content = base64.b64encode(f.read()).decode()
    gh("PUT", f"/repos/{repo}/contents/{repo_path}", token,
       {"message": message, "content": content})


def open_issue(token, repo, title, body):
    return gh("POST", f"/repos/{repo}/issues", token,
              {"title": title, "body": body})


def open_pr(token, repo, branch, title, body):
    base_sha = gh("GET", f"/repos/{repo}/git/ref/heads/main", token)["object"]["sha"]
    gh("POST", f"/repos/{repo}/git/refs", token,
       {"ref": f"refs/heads/{branch}", "sha": base_sha})
    gh("PUT", f"/repos/{repo}/contents/PROBE.md", token,
       {"message": f"probe change on {branch}", "content": base64.b64encode(b"probe").decode(),
        "branch": branch})
    return gh("POST", f"/repos/{repo}/pulls", token,
              {"head": branch, "base": "main", "title": title, "body": body})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    p.add_argument("--name", default="ai-slop-detector-test")
    p.add_argument("--org", default=None, help="Create under this org instead of your user.")
    p.add_argument("--no-pr", action="store_true", help="Skip the PR trigger (issues only).")
    args = p.parse_args()
    if not args.token:
        print("Need --token or GITHUB_TOKEN env.", file=sys.stderr)
        sys.exit(1)

    print(f"Creating repo {args.name} ...")
    repo = create_repo(args.token, args.name, args.org)["full_name"]
    print(f"  → {repo}")

    # Wait a moment for auto_init commit to land
    import time
    time.sleep(2)

    print("Uploading Action files ...")
    for local, repo_path in FILES:
        upload_file(args.token, repo, repo_path, local, f"add {repo_path}")
        print(f"  → {repo_path}")

    print("Opening trigger events (real run on GitHub) ...")
    ai_issue = open_issue(args.token, repo,
                           "Add AI-generated contribution detection (AI-style)", AI_BODY)
    print(f"  → issue #{ai_issue['number']} (AI-style, should be labeled)")
    human_issue = open_issue(args.token, repo, "Fix readme typo (human)", HUMAN_BODY)
    print(f"  → issue #{human_issue['number']} (human, should be ignored)")

    if not args.no_pr:
        pr = open_pr(args.token, repo, "ai-slop-probe",
                     "AI-style PR (should be labeled)", AI_BODY)
        print(f"  → PR #{pr['number']} (AI-style, should be labeled)")

    print("\nDone. Check the Actions tab + issue/PR labels/comments at:")
    print(f"  https://github.com/{repo}")
    print(f"Enable auto-close: edit .github/workflows/ai-slop.yml to add `with: auto_close: true`")
    print(f"Enable weekly digest: it's already wired (digest.yml, every Monday).")
    print(f"Clean up: gh repo delete --yes {repo}")


if __name__ == "__main__":
    main()
