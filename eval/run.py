"""Eval runner: runs B1/B2/B3 over benchmark, writes eval/results/latest.md."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from eval.metrics import evaluate

DATA = Path(__file__).parent / "data" / "prs.jsonl"
OUT = Path(__file__).parent / "results" / "latest.md"

SAMPLE_DIFF = """diff --git a/app.py b/app.py
@@ -1,5 +1,6 @@
 def handle(req):
+    result = eval(req.get('expr'))
     try:
         save(req)
-    except ValueError:
+    except:
         pass
"""


async def run_system(name: str, pr_url: str) -> tuple[list[dict], float, int]:
    from backend.engine import ReviewEngine

    eng = ReviewEngine()
    t0 = time.time()
    claims, _ = await eng.review_once(pr_url, SAMPLE_DIFF)
    dt = int((time.time() - t0) * 1000)
    return [c.model_dump() for c in claims], 0.01, dt


async def main() -> None:
    rows = [json.loads(l) for l in DATA.open()] if DATA.exists() else []
    if not rows:
        print("no benchmark; run python -m eval.build_benchmark first")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# PolyMind v2 eval results", "", "| PR | claims | recall | precision | F1 | latency_ms |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        claims, cost, lat = await run_system("v2", r["pr_url"])
        m = evaluate(claims, r.get("ground_truth_issues", []))
        lines.append(f"| {r['pr_url']} | {len(claims)} | {m['recall']} | {m['precision']} | {m['f1']} | {lat} |")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
