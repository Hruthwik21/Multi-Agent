"""ast_query + complexity_check + search_cve + repro generator tools."""
from __future__ import annotations

import json
from pathlib import Path

from backend.models import ReviewContext
from backend.tools.registry import tool

# ensure registry imports register everything
from backend.tools import read_file as _rf  # noqa: F401
from backend.tools import run_linter as _rl  # noqa: F401
from backend.tools import run_tests as _rt  # noqa: F401
from backend.tools import semgrep as _sg  # noqa: F401


@tool("ast_query", "Return AST chunks for a file filtered by kind/name",
      {"type": "object", "properties": {
          "file": {"type": "string"}, "kind": {"type": "string", "default": ""},
          "name": {"type": "string", "default": ""}},
       "required": ["file"]})
async def ast_query(ctx: ReviewContext, file: str, kind: str = "", name: str = "") -> str:
    target = next((f for f in ctx.changed_files if f.path == file), None)
    if target is None:
        return json.dumps({"error": f"file not in scope: {file}"})
    chunks = [c.model_dump() for c in target.ast_chunks
              if (not kind or c.kind == kind) and (not name or name.lower() in c.name.lower())]
    return json.dumps({"chunks": chunks[:10]})


@tool("complexity_check", "Cyclomatic-complexity heuristic for a file",
      {"type": "object", "properties": {"file_path": {"type": "string"}},
       "required": ["file_path"]})
async def complexity_check(ctx: ReviewContext, file_path: str) -> str:
    target = next((f for f in ctx.changed_files if f.path == file_path), None)
    if target is None:
        return json.dumps({"error": "not in scope"})
    text = target.full_content or target.patch
    keywords = [" if ", " for ", " while ", " and ", " or ", " except", " elif ", " case "]
    score = sum(text.count(k) for k in keywords)
    verdict = "high" if score > 30 else "medium" if score > 12 else "low"
    return json.dumps({"complexity_score": score, "verdict": verdict})


CVE_DB_PATH = Path(__file__).parent / "cve_db.json"


@tool("search_cve", "Offline CVE lookup over bundled top entries",
      {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
async def search_cve(ctx: ReviewContext, query: str) -> str:
    try:
        db = json.loads(CVE_DB_PATH.read_text()) if CVE_DB_PATH.exists() else []
    except Exception:
        db = []
    q = query.lower()
    hits = [e for e in db if q in json.dumps(e).lower()][:5]
    if not hits:
        hits = [{"note": f"No bundled CVE matches '{query}'. Treat as unverifiable without network."}]
    return json.dumps({"hits": hits})
