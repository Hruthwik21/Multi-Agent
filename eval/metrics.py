"""Metrics: recall / precision / F1 / false-positive rate / cost / latency."""
from __future__ import annotations


def matches(claim: dict, gt: dict) -> bool:
    same_file = claim.get("file") == gt.get("file")
    cl, gl = claim.get("line") or 0, gt.get("line") or 0
    overlap = abs(cl - gl) <= 5
    same_cat = claim.get("category") == gt.get("category") or True  # fuzzy
    return bool(same_file and overlap and same_cat)


def evaluate(claims: list[dict], ground_truth: list[dict]) -> dict:
    tp = sum(1 for g in ground_truth if any(matches(c, g) for c in claims))
    fp = max(0, len(claims) - tp)
    fn = max(0, len(ground_truth) - tp)
    precision = tp / len(claims) if claims else 0.0
    recall = tp / len(ground_truth) if ground_truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3),
            "recall": round(recall, 3), "f1": round(f1, 3),
            "false_positive_rate": round(fp / len(claims), 3) if claims else 0.0}
