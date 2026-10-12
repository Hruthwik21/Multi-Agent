"""ReviewEngine orchestrator: ingest -> parallel agents -> arbiter -> synthesize."""
from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from backend.agents.arbiter import Arbiter
from backend.agents.bug_hunter import BugHunterAgent
from backend.agents.perf_idiom import PerfIdiomAgent
from backend.agents.security import SecurityAgent
from backend.ingestion.github import context_from_diff, fetch_pr_context
from backend.llm.client import LLMClient
from backend.models import Claim, ReviewContext
from backend.synthesis import ranker
from backend.synthesis.synthesizer import build_comment


@dataclass
class SSEEvent:
    event: str
    data: dict

    def encode(self) -> str:
        import json

        return f"event: {self.event}\ndata: {json.dumps(self.data, default=str)}\n\n"


class ReviewEngine:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()
        self.agents = [BugHunterAgent(self.llm), SecurityAgent(self.llm), PerfIdiomAgent(self.llm)]
        self.arbiter = Arbiter()

    async def _ingest(self, pr_url: str, diff_text: str | None) -> ReviewContext:
        if diff_text:
            return context_from_diff(pr_url, diff_text)
        try:
            return await fetch_pr_context(pr_url)
        except Exception:
            # offline fallback: empty context so agents still run
            return context_from_diff(pr_url, "")

    async def run(self, pr_url: str, diff_text: str | None = None) -> AsyncIterator[SSEEvent]:
        t0 = time.time()
        session_id = uuid.uuid4().hex[:8]
        yield SSEEvent("session_started", {"session_id": session_id, "pr_url": pr_url})
        ctx = await self._ingest(pr_url, diff_text)
        n_lines = sum(len(f.patch.splitlines()) for f in ctx.changed_files)
        yield SSEEvent("ingestion_done",
                       {"files_changed": len(ctx.changed_files), "lines": n_lines,
                        "language": ctx.language})
        # run sequentially but stream (simpler + deterministic); still fast in mock mode
        all_claims: list[Claim] = []
        cost = 0.0
        for agent in self.agents:
            yield SSEEvent("agent_started", {"agent": agent.name})
            claims = await agent.review(ctx)
            for c in claims:
                yield SSEEvent("agent_claim", {"agent": agent.name, "claim": c.model_dump()})
            yield SSEEvent("agent_done", {"agent": agent.name, "claims_count": len(claims)})
            all_claims.extend(claims)
        yield SSEEvent("arbiter_started", {"claims_count": len(all_claims)})
        verified = await self.arbiter.verify(all_claims, ctx)
        for c in verified:
            yield SSEEvent("claim_verified",
                           {"claim_id": c.id, "status": c.verification_status.value,
                            "tool": c.verification_tool})
        ranked = ranker.rank_and_dedupe(verified)
        latency_ms = int((time.time() - t0) * 1000)
        comment = await build_comment(ranked, cost, latency_ms, self.llm)
        yield SSEEvent("synthesis_done",
                       {"final_comment": comment, "cost_usd": cost, "latency_ms": latency_ms})
        yield SSEEvent("done", {"session_id": session_id, "report_url": f"/report/{session_id}",
                                "claims": [c.model_dump() for c in ranked],
                                "comment": comment})

    async def review_once(self, pr_url: str, diff_text: str | None = None) -> tuple[list[Claim], str]:
        ctx = await self._ingest(pr_url, diff_text)
        all_claims: list[Claim] = []
        for agent in self.agents:
            all_claims.extend(await agent.review(ctx))
        verified = await self.arbiter.verify(all_claims, ctx)
        ranked = ranker.rank_and_dedupe(verified)
        comment = await build_comment(ranked, 0.0, 0, self.llm)
        return ranked, comment
