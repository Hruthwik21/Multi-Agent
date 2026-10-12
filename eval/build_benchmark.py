"""Benchmark builder: scaffold 50-PR benchmark (offline sample included).

Real usage: scrape merged PRs from fastapi/pydantic/httpx/black/django where
review comments identified bugs -> eval/data/prs.jsonl {pr_url, ground_truth_issues}.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "data" / "prs.jsonl"

SAMPLE = [
    {"pr_url": "https://github.com/local/sample/pull/1",
     "ground_truth_issues": [{"file": "app.py", "line": 3, "category": "security",
                              "note": "eval() on user input"}]},
    {"pr_url": "https://github.com/local/sample/pull/2",
     "ground_truth_issues": [{"file": "db.py", "line": 8, "category": "bug",
                              "note": "bare except"}]},
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        with OUT.open("w") as f:
            for row in SAMPLE:
                f.write(json.dumps(row) + "\n")
    print(f"benchmark at {OUT} ({sum(1 for _ in OUT.open())} rows)")


if __name__ == "__main__":
    main()
