"""semgrep: run Semgrep OSS if installed; else pattern fallback with bundled rules."""
from __future__ import annotations

import json
import shutil

from backend.models import ReviewContext
from backend.tools.registry import tool
from backend.tools.sandbox import run_sandboxed

PATTERNS = {
    "python-injection": ["eval(", "exec(", "os.system(", "subprocess.call("],
    "secrets": ["password =", "passwd =", "api_key =", "secret ="],
    "deserialization": ["pickle.loads", "yaml.load(", "marshal.loads"],
    "ssrf": ["requests.get(", "urllib.request.urlopen("],
}


@tool("semgrep", "Run Semgrep OSS (or pattern fallback) over a changed file",
      {"type": "object", "properties": {
          "rule_set": {"type": "string", "default": "auto"},
          "file_path": {"type": "string"}}, "required": ["file_path"]})
async def semgrep(ctx: ReviewContext, file_path: str, rule_set: str = "auto") -> str:
    target = next((f for f in ctx.changed_files if f.path == file_path), None)
    if target is None:
        return json.dumps({"error": f"file not in scope: {file_path}"})
    content = target.full_content or target.patch
    if shutil.which("semgrep"):
        code, out, err = run_sandboxed(
            ["semgrep", "--json", "--quiet", "--config", "auto", "--include=*.py", "-"],
            cwd_files={"t.py": content})
        if code == 0 and out:
            return out
    findings = []
    for rule, needles in PATTERNS.items():
        for i, line in enumerate(content.splitlines(), 1):
            if any(n in line for n in needles):
                findings.append({"rule": rule, "line": i, "code": line.strip()[:200]})
    return json.dumps({"tool": "pattern-fallback", "findings": findings})
