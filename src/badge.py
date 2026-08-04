#!/usr/bin/env python3
"""Self-serve AI-slop badge generator.

Any maintainer can produce their own badge SVG from a local percentage —
no ClickHouse, no network, no API. This is the "self-serve" piece that
completes the loop: install the P0 Action, get a per-repo score, drop a
badge into your README.

Usage:
  python src/badge.py owner/repo 12.3
  python src/badge.py owner/repo 12.3 --out badges/owner__repo.svg

Also imported by aggregate.py so the leaderboard and the self-serve CLI
share one implementation (DRY).
"""
import argparse


def color_for(pct):
    """Traffic-light color for a pollution percentage."""
    if pct >= 30:
        return "#e5484d"  # red
    if pct >= 10:
        return "#f5a623"  # orange
    if pct >= 3:
        return "#f5d90a"  # yellow
    return "#46a758"  # green


def make_badge(repo, pct):
    """shields.io-style two-part SVG badge, right side = AI-slop %."""
    val = f"{pct:.1f}%"
    color = color_for(pct).lstrip("#")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="140" height="20" role="img">
  <rect rx="3" width="140" height="20" fill="#444"/>
  <rect x="55" rx="3" width="85" height="20" fill="#{color}"/>
  <g fill="#fff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="8" y="14" fill="#fff">AI-slop</text>
    <text x="60" y="14" fill="#fff">{val}</text>
  </g>
</svg>'''


def main():
    p = argparse.ArgumentParser(description="Generate an AI-slop badge SVG.")
    p.add_argument("repo", help="owner/name")
    p.add_argument("pct", type=float, help="AI-slop percentage, e.g. 12.3")
    p.add_argument("--out", help="write to file instead of stdout")
    args = p.parse_args()
    svg = make_badge(args.repo, args.pct)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", args.out)
    else:
        print(svg)


if __name__ == "__main__":
    main()
