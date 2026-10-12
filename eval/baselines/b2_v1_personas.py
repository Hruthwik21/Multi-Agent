"""B2: v1 personas (no tools, no arbiter) — legacy debate loop stub for comparison."""
from __future__ import annotations

from backend.llm.client import LLMClient
from backend.models import ReviewContext


async def baseline_v1_personas(ctx: ReviewContext) -> str:
    llm = LLMClient()
    out = []
    for persona in ("analyst", "critic", "expert"):
        r = await llm.generate(f"You are {persona}. Review the diff briefly.", ctx.diff[:4000])
        out.append(f"## {persona}\n{r.text[:1000]}")
    return "\n\n".join(out)
