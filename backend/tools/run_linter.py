"""run_linter: ruff for Python, eslint for JS/TS; heuristic fallback offline."""
from __future__ import annotations

import json
import shutil

from backend.models import ReviewContext
from backend.tools.registry import tool
from backend.tools.sandbox import run_sandboxed


@tool("run_linter", "Lint a changed file, return findings JSON",
      {"type": "object", "properties": {"file_path": {"type": "string"}},
       "required": ["file_path"]})
async def run_linter(ctx: ReviewContext, file_path: str) -> str:
    target = next((f for f in ctx.changed_files if f.path == file_path), None)
    if target is None:
        return json.dumps({"error": f"file not in scope: {file_path}"})
    content = target.full_content or target.patch
    lang = target.language
    if lang == "python" and shutil.which("ruff"):
        code, out, err = run_sandboxed(
            ["ruff", "check", "--output-format=json", "-"],
            cwd_files={"t.py": content})
        return out or json.dumps({"error": err})
    if lang in ("javascript", "typescript") and shutil.which("eslint"):
        code, out, err = run_sandboxed(["eslint", "-f", "json", "--stdin"],
                                       cwd_files={"t.js": content})
        return out or json.dumps({"error": err})
    # heuristic fallback: bare except, eval, long lines, TODO
    findings = []
    for i, line in enumerate(content.splitlines(), 1):
        s = line.strip()
        if s == "except:":
            findings.append({"line": i, "rule": "bare-except", "msg": "Bare except"})
        if "eval(" in s or "exec(" in s:
            findings.append({"line": i, "rule": "dangerous-call", "msg": "eval/exec usage"})
        if len(line) > 120:
            findings.append({"line": i, "rule": "line-too-long", "msg": f"{len(line)} chars"})
        if "TODO" in s or "FIXME" in s:
            findings.append({"line": i, "rule": "todo", "msg": "Leftover TODO"})
    return json.dumps({"tool": "heuristic-linter", "findings": findings})
