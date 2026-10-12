"""run_tests: pytest -q in sandbox; falls back to py_compile when pytest missing."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from backend.models import ReviewContext
from backend.tools.registry import tool
from backend.tools.sandbox import run_sandboxed


@tool("run_tests", "Run pytest in sandbox, return summary JSON",
      {"type": "object", "properties": {"test_path": {"type": ["string", "null"]}},
       "required": []})
async def run_tests(ctx: ReviewContext, test_path: str | None = None) -> str:
    files = {f.path: (f.full_content or "") for f in ctx.changed_files if f.full_content}
    if shutil.which("pytest"):
        with tempfile.TemporaryDirectory() as tmp:
            for rel, content in files.items():
                p = Path(tmp) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8", errors="ignore")
            import subprocess

            try:
                target = test_path or "."
                proc = subprocess.run(["pytest", "-q", target], cwd=tmp,
                                      capture_output=True, text=True, timeout=30)
                return json.dumps({"returncode": proc.returncode,
                                   "stdout_tail": proc.stdout[-3000:],
                                   "stderr_tail": proc.stderr[-3000:]})
            except Exception as e:
                return json.dumps({"error": str(e)})
    # fallback: syntax check python files
    import py_compile

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for rel, content in files.items():
            if not rel.endswith(".py"):
                continue
            p = Path(tmp) / "m.py"
            p.write_text(content, encoding="utf-8", errors="ignore")
            try:
                py_compile.compile(str(p), doraise=True)
                results.append({"file": rel, "compiles": True})
            except Exception as e:
                results.append({"file": rel, "compiles": False, "error": str(e)[:500]})
    code, out, err = run_sandboxed(["python", "--version"])
    return json.dumps({"tool": "py_compile-fallback", "results": results, "python": (out + err).strip()})
