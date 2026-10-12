"""Arbiter: the differentiator. Verifies each claim with tools (Phase 5).

Strategy table:
- style -> run_linter
- security -> semgrep (+ search_cve fallback note)
- perf -> complexity_check
- bug logic -> run_tests / repro
- test -> check test file exists+runs
- docs -> always unverifiable
"""
from __future__ import annotations

import asyncio
import json

from backend.errors import ToolError
from backend.models import Category, Claim, ReviewContext, VerificationStatus


class Arbiter:
    def __init__(self, parallel: int = 4):
        self.sem = asyncio.Semaphore(parallel)

    async def verify(self, claims: list[Claim], ctx: ReviewContext) -> list[Claim]:
        return list(await asyncio.gather(*[self._verify_one(c, ctx) for c in claims]))

    def _pick_strategy(self, claim: Claim) -> str:
        if claim.category == Category.STYLE:
            return "linter"
        if claim.category == Category.SECURITY:
            return "semgrep"
        if claim.category == Category.PERF:
            return "complexity"
        if claim.category == Category.TEST:
            return "test"
        if claim.category == Category.DOCS:
            return "manual_review"
        return "test"  # bug -> tests/repro

    async def _verify_one(self, claim: Claim, ctx: ReviewContext) -> Claim:
        async with self.sem:
            strategy = self._pick_strategy(claim)
            try:
                if strategy == "manual_review":
                    claim.verification_status = VerificationStatus.UNVERIFIABLE
                    claim.verification_tool = "manual_review"
                    claim.verification_output = "Docs/nit claims are not tool-verifiable."
                    return claim
                if strategy == "linter":
                    from backend.tools.run_linter import run_linter

                    out = await run_linter(ctx, claim.file)
                    data = json.loads(out)
                    findings = data.get("findings", [])
                    hit = any(abs((f.get("line") or 0) - (claim.line or 0)) <= 3 for f in findings) \
                        if findings else False
                    claim.verification_status = VerificationStatus.VERIFIED if hit else VerificationStatus.REFUTED
                    claim.verification_tool = "run_linter"
                    claim.verification_output = out[:1000]
                    return claim
                if strategy == "semgrep":
                    from backend.tools.semgrep import semgrep

                    out = await semgrep(ctx, claim.file)
                    data = json.loads(out)
                    findings = data.get("findings", [])
                    hit = bool(findings)
                    claim.verification_status = VerificationStatus.VERIFIED if hit else VerificationStatus.UNVERIFIABLE
                    claim.verification_tool = "semgrep"
                    claim.verification_output = out[:1000]
                    return claim
                if strategy == "complexity":
                    from backend.tools.ast_query import complexity_check

                    out = await complexity_check(ctx, claim.file)
                    data = json.loads(out)
                    verdict = data.get("verdict", "low")
                    claim.verification_status = (
                        VerificationStatus.VERIFIED if verdict in ("high", "medium")
                        else VerificationStatus.UNVERIFIABLE)
                    claim.verification_tool = "complexity_check"
                    claim.verification_output = out[:1000]
                    return claim
                # test / bug path
                from backend.tools.run_tests import run_tests

                out = await run_tests(ctx, None)
                data = json.loads(out)
                if "results" in data:  # py_compile fallback
                    bad = [r for r in data["results"] if not r.get("compiles")]
                    if bad and claim.category == Category.BUG:
                        claim.verification_status = VerificationStatus.VERIFIED
                    else:
                        claim.verification_status = VerificationStatus.UNVERIFIABLE
                    claim.verification_tool = "run_tests"
                    claim.verification_output = out[:1000]
                    return claim
                rc = data.get("returncode", 0)
                if rc != 0 and claim.category == Category.BUG:
                    claim.verification_status = VerificationStatus.VERIFIED
                elif rc == 0:
                    claim.verification_status = VerificationStatus.UNVERIFIABLE
                else:
                    claim.verification_status = VerificationStatus.UNVERIFIABLE
                claim.verification_tool = "run_tests"
                claim.verification_output = out[:1000]
                return claim
            except ToolError as e:
                claim.verification_status = VerificationStatus.UNVERIFIABLE
                claim.verification_tool = strategy
                claim.verification_output = str(e)[:1000]
                return claim
