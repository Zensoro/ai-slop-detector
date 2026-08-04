import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import aggregate as A


def test_color_for():
    assert A.color_for(50) == "#e5484d"
    assert A.color_for(15) == "#f5a623"
    assert A.color_for(5) == "#f5d90a"
    assert A.color_for(1) == "#46a758"


def test_make_badge():
    svg = A.make_badge("x/y", 12.3)
    assert "<svg" in svg and "12.3%" in svg and "#" in svg


def test_parse():
    rows = A.parse_json_each_row(
        '{"repo_name":"a","total":10,"ai_count":3,"pct":30.0}\n'
    )
    assert rows[0]["repo_name"] == "a"


def test_build_outputs_sorts_and_writes():
    rows = [
        {"repo_name": "b/b", "total": 100, "ai_count": 50, "pct": 50.0},
        {"repo_name": "a/a", "total": 100, "ai_count": 5, "pct": 5.0},
    ]
    tmp = tempfile.mkdtemp()
    A.build_outputs(rows, root=tmp)

    lb = json.load(open(os.path.join(tmp, "data", "leaderboard.json")))
    assert lb[0]["repo"] == "b/b"  # sorted descending

    assert os.path.exists(os.path.join(tmp, "site", "index.html"))
    assert os.path.exists(os.path.join(tmp, "badges", "b__b.svg"))

    csv_text = open(os.path.join(tmp, "data", "leaderboard.csv")).read()
    assert "b/b" in csv_text and "a/a" in csv_text

    site = open(os.path.join(tmp, "site", "index.html")).read()
    assert "AI-Slop Pollution Index" in site and "b/b" in site


if __name__ == "__main__":
    test_color_for()
    test_make_badge()
    test_parse()
    test_build_outputs_sorts_and_writes()
    print("ALL P1 TESTS PASSED")
