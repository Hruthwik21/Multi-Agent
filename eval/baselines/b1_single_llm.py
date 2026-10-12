"""B1: single Gemini call 'review this diff, output JSON claims'."""
from __future__ import annotations

from backend.llm.client import LLMClient
from backend.models import ReviewContext


async def baseline_single_llm(ctx: ReviewContext) -> str:
    llm = LLMClient()
    res = await llm.generate("Review this diff. Output JSON claims.",
                             ctx.diff[:8000], json_mode=True)
    return res.text
