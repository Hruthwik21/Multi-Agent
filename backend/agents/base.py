"""BaseAgent: tool loop + JSON parsing + single retry (Phase 3)."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import structlog

from backend.llm.client import LLMClient
from backend.models import Claim, ReviewContext
from backend.tools.registry import list_tools

PROMPT_DIR = Path(__file__).parent.parent / "prompts"

log = structlog.get_logger()


class BaseAgent(ABC):
    name: str = "base"
    allowed_tools: list[str] = []
    system_file: str = ""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def system_prompt(self) -> str:
        base = ""
        if self.system_file:
            p = PROMPT_DIR / self.system_file
            if p.exists():
                base = p.read_text(encoding="utf-8")
        shared = PROMPT_DIR / "shared_json_schema.md"
        if shared.exists():
            base += "\n\n" + shared.read_text(encoding="utf-8")
        return base or f"You are {self.name}. Output JSON claims only."

    def tool_specs(self) -> list[dict]:
        return [
            {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
            for t in list_tools(self.allowed_tools)
        ]

    @abstractmethod
    def focus(self) -> str: ...

    def build_user(self, ctx: ReviewContext) -> str:
        files = "\n".join(f"- {f.path} ({f.language})" for f in ctx.changed_files)
        chunks = []
        for f in ctx.changed_files[:6]:
            for c in f.ast_chunks[:4]:
                chunks.append(f"### {f.path}:{c.start_line}-{c.end_line} {c.kind} {c.name}\n{c.code[:1500]}")
        return (
            f"PR: {ctx.pr_title}\nRepo: {ctx.repo}\nLanguage: {ctx.language}\nCI: {ctx.ci_status}\n"
            f"Focus: {self.focus()}\n\nChanged files:\n{files}\n\n"
            f"Diff (truncated 12000 chars):\n{ctx.diff[:12000]}\n\n"
            f"AST chunks:\n{chr(10).join(chunks)[:8000]}"
        )

    async def review(self, ctx: ReviewContext) -> list[Claim]:
        specs = self.tool_specs()
        system = self.system_prompt()
        user = self.build_user(ctx)
        # tool loop (single pass: LLM mock ignores tools; real LLM may return tool_calls)
        result = await self.llm.generate(system, user, tools=specs, json_mode=True)
        claims = self.parse_claims(result.text, ctx)
        if not claims and "claims" not in result.text.lower():
            # retry once with strict instruction
            retry = await self.llm.generate(
                system, user + "\n\nOutput VALID JSON only: {\"claims\": [...]}", json_mode=True)
            claims = self.parse_claims(retry.text, ctx)
        return claims

    def parse_claims(self, text: str, ctx: ReviewContext) -> list[Claim]:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                # drop possible 'json' prefix
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            data = json.loads(cleaned)
            items = data.get("claims", data if isinstance(data, list) else [])
        except Exception as e:
            log.warning("claim-parse-failed", agent=self.name, error=str(e)[:300])
            return []
        valid: list[Claim] = []
        changed_paths = {f.path for f in ctx.changed_files}
        for item in items:
            try:
                if not isinstance(item, dict):
                    continue
                fpath = str(item.get("file", ""))
                if changed_paths and fpath not in changed_paths:
                    # coerce to first changed file instead of dropping
                    fpath = next(iter(changed_paths))
                conf = float(item.get("confidence", 0.5))
                if conf < 0.4:
                    continue
                claim = Claim(
                    id=Claim.make_id(fpath, item.get("line"),
                                     str(item.get("issue", ""))[:200]),
                    issue=str(item.get("issue", ""))[:500],
                    file=fpath,
                    line=item.get("line"),
                    severity=item.get("severity", "medium"),  # type: ignore[arg-type]
                    category=item.get("category", "bug"),  # type: ignore[arg-type]
                    evidence=str(item.get("evidence", ""))[:1000],
                    suggested_fix=(str(item.get("suggested_fix") or "") or None),
                    confidence=conf,
                    agent=self.name,
                )
                valid.append(claim)
            except Exception as e:
                log.warning("claim-invalid", agent=self.name, error=str(e)[:200])
        return valid
