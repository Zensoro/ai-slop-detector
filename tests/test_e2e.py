"""End-to-end integration test against a local mock of the GitHub REST API.

We can't reach real GitHub from this sandbox (no token / connector off), so we
emulate exactly the endpoints run.py / digest.py hit (labels POST, comments
POST, issue PATCH close, issues GET) and run the REAL action code against it.
Only the transport is swapped: localhost instead of api.github.com.

Run: python tests/test_e2e.py
"""
import os
import sys
import json
import time
import threading
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = "/Users/zen/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
RUN_PY = os.path.join(ROOT, "src", "run.py")
DIGEST_PY = os.path.join(ROOT, "src", "digest.py")
SIGNALS = os.path.join(ROOT, "signals", "default.toml")
MOCK_PORT = 8799
MOCK = f"http://127.0.0.1:{MOCK_PORT}"

# Records every call the mock receives: (method, path, json_body)
CALLS = []
CALLS_LOCK = threading.Lock()


def reset_calls():
    with CALLS_LOCK:
        CALLS.clear()


def calls():
    with CALLS_LOCK:
        return list(CALLS)


class Handler(BaseHTTPRequestHandler):
    def _drain(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if n else b""
        try:
            return json.loads(body) if body else None
        except Exception:
            return None

    def _record(self, method):
        payload = self._drain()
        with CALLS_LOCK:
            CALLS.append((method, self.path, payload))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def do_POST(self):
        self._record("POST")

    def do_PATCH(self):
        self._record("PATCH")

    def do_GET(self):
        # Digest fetches labeled issues from this endpoint.
        if "/issues" in self.path and "labels=" in self.path:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            items = [
                {
                    "number": 11, "title": "Add cool feature",
                    "body": "## Summary\nDid a thing.\n\n## Test\nok ✅",
                    "html_url": f"{MOCK}/o/r/issues/11",
                    "user": {"login": "alice"}, "created_at": now,
                    "pull_request": {"url": "x"},
                },
                {
                    "number": 12, "title": "fix typo",
                    "body": "just a typo fix",
                    "html_url": f"{MOCK}/o/r/issues/12",
                    "user": {"login": "bob"}, "created_at": now,
                },
            ]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(items).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

    def log_message(self, *a):
        pass  # silence


def start_server():
    srv = ThreadingHTTPServer(("127.0.0.1", MOCK_PORT), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def run_action(event_payload, extra_env=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(event_payload, f)
        event_path = f.name
    env = {
        "GITHUB_TOKEN": "test-token",
        "GITHUB_EVENT_PATH": event_path,
        "GITHUB_REPOSITORY": "o/r",
        "AI_SLOP_API": MOCK,
        "SIGNALS_PATH": SIGNALS,
        "THRESHOLD": "0.6",
    }
    if extra_env:
        env.update(extra_env)
    r = subprocess.run([PY, RUN_PY], env=env, capture_output=True, text=True)
    os.unlink(event_path)
    return r


def pr_payload(body, assoc="NONE", login="newbie"):
    return {"action": "opened", "pull_request": {
        "number": 101, "body": body, "author_association": assoc,
        "user": {"login": login},
    }}


def issue_payload(body, assoc="NONE", login="human"):
    return {"action": "opened", "issue": {
        "number": 202, "body": body, "author_association": assoc,
        "user": {"login": login},
    }}


def test_ai_pr_gets_label_and_comment():
    reset_calls()
    r = run_action(pr_payload("## Summary\nAdded feature.\n\n## Test\nTests added. ✅"))
    assert r.returncode == 0, r.stderr
    c = calls()
    assert any(m == "POST" and p.endswith("/labels") for m, p, _ in c), c
    assert any(m == "POST" and p.endswith("/comments") for m, p, _ in c), c
    # no close when auto_close off
    assert not any(m == "PATCH" for m, _, _ in c), c
    print("✓ AI PR → label + comment, no close")


def test_human_issue_skipped():
    reset_calls()
    r = run_action(issue_payload("just a small typo fix"))
    assert r.returncode == 0, r.stderr
    assert calls() == [], calls()
    print("✓ human issue → no API calls")


def test_high_score_pr_autoclosed():
    reset_calls()
    r = run_action(
        pr_payload("## Summary\nx\n\n## Test\ny ✅"),
        extra_env={"AUTO_CLOSE": "true", "CLOSE_THRESHOLD": "0.9", "CLOSE_PRS": "true"},
    )
    assert r.returncode == 0, r.stderr
    c = calls()
    assert any(m == "PATCH" for m, _, _ in c), c
    print("✓ high-score PR + auto_close → PATCH closed")


def test_trusted_author_skipped():
    reset_calls()
    r = run_action(pr_payload("## Summary\nx ✅", assoc="MEMBER", login="coredev"))
    assert r.returncode == 0, r.stderr
    assert calls() == [], calls()
    print("✓ MEMBER author → skipped (no false auto-close)")


def test_digest_end_to_end():
    out = os.path.join(tempfile.gettempdir(), "ai_slop_digest_test.md")
    env = {"AI_SLOP_API": MOCK, "GITHUB_TOKEN": "x", "GITHUB_REPOSITORY": "o/r"}
    r = subprocess.run(
        [PY, DIGEST_PY, "--repo", "o/r", "--token", "x", "--days", "7", "--out", out],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    content = open(out, encoding="utf-8").read()
    assert "Flagged this week:** 2" in content, content
    assert "Issues: 1 · PRs: 1" in content, content
    os.unlink(out)
    print("✓ digest.py → digest/latest.md generated with 2 items (1 PR, 1 issue)")


if __name__ == "__main__":
    start_server()
    time.sleep(0.3)
    test_ai_pr_gets_label_and_comment()
    test_human_issue_skipped()
    test_high_score_pr_autoclosed()
    test_trusted_author_skipped()
    test_digest_end_to_end()
    print("\nALL E2E TESTS PASSED")
