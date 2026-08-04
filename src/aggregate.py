#!/usr/bin/env python3
"""P1: Aggregate AI-slop pollution index + per-repo badges + shareable site.

$0: data from the public ClickHouse GH Archive instance (no auth), outputs
committed to the repo and/or published via Pages. Re-run weekly by aggregate.yml.

Pipeline:
  fetch (ClickHouse) -> data/raw.json
  build  -> data/leaderboard.json + .csv
         -> badges/<repo>.svg   (one per tracked repo, embeddable)
         -> site/index.html     (the screenshot-worthy leaderboard)
"""
import os
import sys
import json
import csv
import urllib.request

try:
    from badge import make_badge, color_for
except ImportError:  # running from project root with src/ on the path
    from src.badge import make_badge, color_for

# Project root (parent of src/) so repos.txt and the generated
# data/ badges/ site/ land at the repo root, matching .gitignore + aggregate.yml.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = "https://play.clickhouse.com/?user=explorer"
WINDOW_START = "2026-01-01"
WINDOW_END = "2026-04-30"


def load_repos(path=None):
    path = path or os.path.join(ROOT, "repos.txt")
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def build_query(repos):
    in_list = ", ".join(f"'{r}'" for r in repos)
    return f"""SELECT repo_name, count() AS total,
  countIf(match(body, '✅') OR match(body, '(?m)^##\\s+(Summary|Overview|Problem|Context|Root Cause|Tests?|Testing)')) AS ai_count,
  round(100.0*ai_count/total,1) AS pct
FROM github_events
WHERE event_type='IssuesEvent' AND action='opened'
  AND created_at BETWEEN '{WINDOW_START}' AND '{WINDOW_END}'
  AND repo_name IN ({in_list})
GROUP BY repo_name ORDER BY pct DESC
FORMAT JSONEachRow"""


def fetch_clickhouse(sql):
    try:
        req = urllib.request.Request(CH, data=sql.encode(), method="POST")
        req.add_header("Content-Type", "text/plain")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read().decode()
    except Exception as e:  # noqa: BLE001
        print("ClickHouse fetch failed:", e, file=sys.stderr)
        return None


def parse_json_each_row(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def safe_name(repo):
    return repo.replace("/", "__")


def fetch_or_load(repos, refresh=False, root=ROOT):
    raw_path = os.path.join(root, "data", "raw.json")
    if not refresh and os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as f:
            return json.load(f)
    text = fetch_clickhouse(build_query(repos))
    if text is None:
        if os.path.exists(raw_path):
            with open(raw_path, encoding="utf-8") as f:
                return json.load(f)
        raise SystemExit("No data available and ClickHouse fetch failed.")
    rows = parse_json_each_row(text)
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return rows


# color_for / make_badge are imported from src/badge.py (shared with the
# self-serve CLI) so the leaderboard and per-repo badges stay in sync.


def build_site(data, root=ROOT):
    max_pct = max((d["pct"] for d in data), default=1) or 1
    rows_html = []
    for i, d in enumerate(data, 1):
        w = max(2, int(round(d["pct"] / max_pct * 100)))
        c = color_for(d["pct"])
        rows_html.append(f'''  <tr>
    <td class="rank">{i}</td>
    <td class="repo">{d['repo']}</td>
    <td class="num">{d['pct']:.1f}%</td>
    <td><div class="bar" style="width:{w}%;background:{c}"></div></td>
    <td class="num">{d['ai_count']}/{d['total']}</td>
  </tr>''')
    rows_html = "\n".join(rows_html)
    return f'''<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Slop Pollution Index</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:32px}}
 h1{{font-size:22px;margin:0 0 4px}}
 .sub{{color:#8b949e;font-size:13px;margin-bottom:20px}}
 table{{width:100%;border-collapse:collapse;font-size:14px}}
 th,td{{padding:8px 10px;text-align:left;border-bottom:1px solid #21262d}}
 th{{color:#8b949e;font-weight:600;font-size:12px;text-transform:uppercase}}
 .rank{{color:#8b949e;width:30px}}
 .repo{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
 .num{{text-align:right;color:#8b949e;width:90px}}
 .bar{{height:10px;border-radius:5px}}
 .foot{{margin-top:24px;color:#6e7681;font-size:12px;line-height:1.6}}
 code{{background:#161b22;padding:2px 6px;border-radius:4px;color:#e6edf3}}
</style></head>
<body>
 <h1>🛡️ AI-Slop Pollution Index</h1>
 <div class="sub">各开源仓库外部贡献中 AI 生成内容占比 · 数据窗口 {WINDOW_START} ~ {WINDOW_END} · 来源 GH Archive (ClickHouse 公共实例)</div>
 <table>
  <thead><tr><th>#</th><th>仓库</th><th>AI 占比</th><th>污染指数</th><th class="num">标记/总数</th></tr></thead>
  <tbody>
{rows_html}
  </tbody>
 </table>
 <div class="foot">
  判定信号：<code>##</code> Markdown 小标题 (Summary/Problem/Context/Test/Testing…) + <code>✅</code> emoji。AI 签名 PR 中 Summary 小标题占 82.4% vs 人类 0%；Test/Testing 小标题 78.3% vs 人类 0.8%；✅ 在人类 PR 中占 0%。<br>
  本指数为概率性估计，非精确值；仅反映数据窗口内的趋势（GH Archive 在 2026-05 后严重缩水，回溯仅到此窗口）。
 </div>
</body></html>'''


def build_outputs(rows, root=ROOT):
    data = [
        {
            "repo": r["repo_name"],
            "total": r["total"],
            "ai_count": r["ai_count"],
            "pct": float(r["pct"]),
        }
        for r in rows
    ]
    data.sort(key=lambda x: x["pct"], reverse=True)

    data_dir = os.path.join(root, "data")
    badges_dir = os.path.join(root, "badges")
    site_dir = os.path.join(root, "site")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(badges_dir, exist_ok=True)
    os.makedirs(site_dir, exist_ok=True)

    with open(os.path.join(data_dir, "leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(data_dir, "leaderboard.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "repo", "ai_count", "total", "pct"])
        for i, d in enumerate(data, 1):
            w.writerow([i, d["repo"], d["ai_count"], d["total"], d["pct"]])

    for d in data:
        with open(os.path.join(badges_dir, f"{safe_name(d['repo'])}.svg"), "w", encoding="utf-8") as f:
            f.write(make_badge(d["repo"], d["pct"]))

    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_site(data, root))

    print(f"Built {len(data)} entries -> data/leaderboard.json+csv, badges/ ({len(data)} svg), site/index.html")
    if data:
        print(f"Top: {data[0]['repo']} {data[0]['pct']:.1f}% | Bottom: {data[-1]['repo']} {data[-1]['pct']:.1f}%")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--fetch", action="store_true", help="force re-pull from ClickHouse")
    p.add_argument("--no-fetch", action="store_true", help="use cached data/raw.json only")
    args = p.parse_args()
    repos = load_repos()
    rows = fetch_or_load(repos, refresh=(args.fetch and not args.no_fetch))
    build_outputs(rows)
    print("P1 build complete.")


if __name__ == "__main__":
    main()
