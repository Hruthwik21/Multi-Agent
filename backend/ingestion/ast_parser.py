"""AST chunking: stdlib `ast` for Python, regex fallback for TS/JS.

tree-sitter is the plan's choice; stdlib keeps dev dependency-free while
preserving the contract (functions/classes intersecting the diff).
"""
from __future__ import annotations

import ast
import re

from backend.models import ASTChunk


def chunk_python(code: str) -> list[ASTChunk]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines = code.splitlines()
    out: list[ASTChunk] = []

    def snippet(node: ast.AST) -> tuple[int, int, str]:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start) or start
        return start, end, "\n".join(lines[start - 1:end])

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            s, e, c = snippet(node)
            out.append(ASTChunk(kind="class", name=node.name, start_line=s, end_line=e, code=c))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s, e, c = snippet(node)
            out.append(ASTChunk(kind="function", name=node.name, start_line=s, end_line=e, code=c))
    return out


_TS_FUNC = re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*\(.*?\)\s*\{)")


def chunk_ts_js(code: str) -> list[ASTChunk]:
    out: list[ASTChunk] = []
    lines = code.splitlines()
    for i, line in enumerate(lines, start=1):
        m = _TS_FUNC.search(line)
        if m:
            name = m.group(1) or m.group(2) or m.group(3) or f"block_{i}"
            block = "\n".join(lines[i - 1:min(len(lines), i + 19)])
            out.append(ASTChunk(kind="function", name=name, start_line=i,
                                end_line=min(len(lines), i + 19), code=block))
    return out


def chunk_code(code: str, language: str) -> list[ASTChunk]:
    if language == "python":
        return chunk_python(code)
    if language in ("typescript", "javascript"):
        return chunk_ts_js(code)
    # try python first, else ts fallback
    py = chunk_python(code)
    return py if py else chunk_ts_js(code)


def filter_by_changed(chunks: list[ASTChunk], changed: list[int]) -> list[ASTChunk]:
    if not changed:
        return chunks
    changed_set = set(changed)
    out = [c for c in chunks if any(c.start_line <= ln <= c.end_line for ln in changed_set)]
    return out or chunks
