"""Gemini wrapper: retry + timeout + cost tracking + streaming + mock fallback.

If GEMINI_API_KEY is missing or google-genai is not installed, the client runs
in deterministic mock mode so the whole pipeline (and tests) work offline.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import get_settings
from backend.errors import LLMError, LLMTimeout
from backend.llm.cost import approx_tokens, estimate_cost_usd


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)


class LLMClient:
    def __init__(self, model: str | None = None, timeout_s: int | None = None):
        s = get_settings()
        self.model = model or s.gemini_model
        self.timeout_s = timeout_s or s.request_timeout_s
        self._api_key = s.gemini_api_key
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        if not self._api_key:
            return
        try:
            from google import genai  # type: ignore

            self._client = genai.Client(api_key=self._api_key)
        except Exception:
            self._client = None

    @property
    def mock_mode(self) -> bool:
        return self._client is None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def generate(
        self,
        system: str,
        user: str,
        tools: list[dict] | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        try:
            return await asyncio.wait_for(
                self._generate_inner(system, user, tools or [], json_mode),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError as e:
            raise LLMTimeout(f"LLM call timed out after {self.timeout_s}s") from e

    async def _generate_inner(
        self, system: str, user: str, tools: list[dict], json_mode: bool
    ) -> LLMResult:
        if self.mock_mode:
            return self._mock_generate(system, user)
        try:
            return await asyncio.to_thread(self._real_generate, system, user, tools, json_mode)
        except Exception as e:
            raise LLMError(str(e)) from e

    def _real_generate(self, system: str, user: str, tools: list[dict], json_mode: bool) -> LLMResult:
        assert self._client is not None
        contents = f"{system}\n\n---\n\n{user}"
        config: dict = {}
        if json_mode:
            config["response_mime_type"] = "application/json"
        if tools:
            from backend.llm.schemas import gemini_tools_schema

            config["tools"] = gemini_tools_schema(tools)
        resp = self._client.models.generate_content(model=self.model, contents=contents, config=config or None)
        text = getattr(resp, "text", "") or ""
        it = approx_tokens(system + user)
        ot = approx_tokens(text)
        return LLMResult(
            text=text, input_tokens=it, output_tokens=ot,
            cost_usd=estimate_cost_usd(self.model, it, ot),
        )

    def _mock_generate(self, system: str, user: str) -> LLMResult:
        """Deterministic heuristic mock: extracts suspicious patterns into claims JSON."""
        lowered = (system + "\n" + user).lower()
        claims: list[dict] = []
        # crude pattern -> claim mapping so e2e works without a key
        patterns = [
            ("eval(", "Avoid eval(): arbitrary code execution risk", "security", "high"),
            ("exec(", "Avoid exec(): arbitrary code execution risk", "security", "high"),
            ("pickle.loads", "Unsafe deserialization with pickle", "security", "high"),
            ("password", "Possible hardcoded secret", "security", "medium"),
            ("secret", "Possible hardcoded secret", "security", "medium"),
            ("todo", "Leftover TODO in changed code", "docs", "nit"),
            ("except:", "Bare except swallows errors", "bug", "medium"),
            ("except exception", "Broad except clause", "bug", "low"),
            ("n+1", "Possible N+1 query pattern", "perf", "medium"),
            ("for ", "Loop in diff — check complexity", "perf", "low"),
        ]
        import re

        files = re.findall(r"[\w\-./]+\.(?:py|ts|js|tsx)", user)
        target = files[0] if files else "changed.py"
        for needle, issue, cat, sev in patterns:
            if needle in lowered:
                claims.append(
                    {
                        "issue": issue,
                        "file": target,
                        "line": 1,
                        "severity": sev,
                        "category": cat,
                        "evidence": f"Matched pattern '{needle.strip()}' in diff",
                        "suggested_fix": "Review and harden this code path.",
                        "confidence": 0.6,
                    }
                )
        if not claims:
            claims.append(
                {
                    "issue": "No critical issues detected in changed lines",
                    "file": target,
                    "line": 1,
                    "severity": "nit",
                    "category": "style",
                    "evidence": "Heuristic scan found no known-risk patterns",
                    "suggested_fix": None,
                    "confidence": 0.4,
                }
            )
        text = json.dumps({"claims": claims[:5]})
        it = approx_tokens(system + user)
        ot = approx_tokens(text)
        return LLMResult(text=text, input_tokens=it, output_tokens=ot,
                         cost_usd=estimate_cost_usd(self.model, it, ot))

    async def stream(self, system: str, user: str):  # pragma: no cover - helper
        result = await self.generate(system, user)
        yield result.text
