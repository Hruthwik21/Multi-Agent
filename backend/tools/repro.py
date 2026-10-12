"""repro: ask LLM to write a minimal failing test, run it in sandbox.

Fails -> VERIFIED (bug reproduced). Passes -> REFUTED.
"""
from __future__ import annotations

import json

from backend.models import Claim, ReviewContext
from backend.tools.registry import tool
from backend.tools.sandbox import run_sandboxed


@tool("generate_repro", "Generate+run a minimal repro script for a claim",
      {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]})
async def generate_repro(ctx: ReviewContext, claim_id: str) -> str:  # pragma: no cover - used via arbiter
    return json.dumps({"note": "use Arbiter.run_repro() directly"})


async def run_repro(claim: Claim, ctx: ReviewContext) -> tuple[bool, str]:
    """Return (failed, output). failed=True means bug reproduced -> verified."""
    from backend.llm.client import LLMClient

    llm = LLMClient()
    prompt = (f"Write a minimal Python pytest that reproduces this issue:\n{claim.issue}\n"
              f"File: {claim.file}\nEvidence: {claim.evidence}\n"
              "Output ONLY python code, no markdown fences.")
    res = await llm.generate("You write minimal failing tests.", prompt)
    code = res.text.strip().removeprefix("```python").removeprefix("```").removesuffix("```")
    files = {f.path: (f.full_content or "") for f in ctx.changed_files if f.full_content}
    files["test_repro.py"] = code
    rc, out, err = run_sandboxed(["python", "-m", "pytest", "-q", "test_repro.py"], cwd_files=files)
    output = (out + "\n" + err)[-2000:]
    failed = rc != 0
    return failed, output
