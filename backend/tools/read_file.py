"""Scoped read_file tool: only within PR's changed files; blocks path traversal."""
from __future__ import annotations

from backend.errors import ToolError
from backend.models import ReviewContext
from backend.tools.registry import tool


@tool("read_file", "Read a slice of a changed file in the PR",
      {"type": "object", "properties": {
          "path": {"type": "string"}, "start": {"type": "integer", "default": 1},
          "end": {"type": "integer", "default": 200}}, "required": ["path"]})
async def read_file(ctx: ReviewContext, path: str, start: int = 1, end: int = 200) -> str:
    if ".." in path.replace("\\", "/") or path.startswith("/") or ":" in path:
        raise ToolError(f"Blocked path traversal: {path!r}")
    for f in ctx.changed_files:
        if f.path == path:
            lines = (f.full_content or f.patch).splitlines()
            s = max(1, start) - 1
            e = min(len(lines), end)
            return "\n".join(lines[s:e]) or "(empty slice)"
    raise ToolError(f"File not in PR scope: {path}")
