"""Synthesizer: ranked claims -> markdown comment via Jinja2 + one LLM prose call."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from backend.llm.client import LLMClient
from backend.models import Claim

TEMPLATE_PATH = Path(__file__).parent / "template.md.j2"


def badge(c: Claim) -> str:
    return {"verified": "✅ Verified", "refuted": "❌ Refuted",
            "unverifiable": "⚠️ Unverifiable", "pending": "⏳ Pending"}[c.verification_status.value]


async def build_comment(claims: list[Claim], cost_usd: float, latency_ms: int,
                        llm: LLMClient | None = None) -> str:
    intro = "PolyMind Council reviewed the changed lines; only tool-checked findings are listed first."
    try:
        llm = llm or LLMClient()
        res = await llm.generate(
            "Write a 2-sentence PR review intro. Factual, no new claims.",
            f"Summarize: {len(claims)} findings. Keep it neutral.")
        if res.text.strip():
            intro = res.text.strip()[:400]
    except Exception:
        pass
    tmpl = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return tmpl.render(claims=claims, badge=badge, intro=intro,
                       cost_usd=cost_usd, latency_ms=latency_ms)
