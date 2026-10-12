"""Ranker: score = severity_weight * confidence * verification_bonus; dedupe."""
from __future__ import annotations

from backend.models import Claim, Severity, VerificationStatus

SEV_W = {
    Severity.CRITICAL: 1.0,
    Severity.HIGH: 0.8,
    Severity.MEDIUM: 0.5,
    Severity.LOW: 0.25,
    Severity.NIT: 0.1,
}
VERIF_BONUS = {
    VerificationStatus.VERIFIED: 1.0,
    VerificationStatus.UNVERIFIABLE: 0.6,
    VerificationStatus.PENDING: 0.5,
    VerificationStatus.REFUTED: 0.0,
}


def score(c: Claim) -> float:
    return SEV_W.get(c.severity, 0.3) * c.confidence * VERIF_BONUS.get(c.verification_status, 0.5)


def rank_and_dedupe(claims: list[Claim]) -> list[Claim]:
    # drop refuted
    live = [c for c in claims if c.verification_status != VerificationStatus.REFUTED]
    # dedupe same file+line+category -> keep highest confidence
    best: dict[tuple, Claim] = {}
    for c in live:
        key = (c.file, c.line, c.category)
        if key not in best or c.confidence > best[key].confidence:
            best[key] = c
    ranked = sorted(best.values(), key=score, reverse=True)
    return ranked
