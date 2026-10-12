"""Sandbox: run subprocesses with timeout, cwd isolation, best-effort hardening.

Linux: resource limits + no-network note. Windows: timeout + cwd jail.
Prod Docker fallback documented in PLAN.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def run_sandboxed(cmd: list[str], cwd_files: dict[str, str] | None = None,
                  timeout: int = 30) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory(prefix="polymind-sbx-") as tmp:
        if cwd_files:
            for rel, content in cwd_files.items():
                p = Path(tmp) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8", errors="ignore")

        def _limits() -> None:  # pragma: no cover - unix only
            try:
                import resource

                resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
                resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            except Exception:
                pass

        try:
            proc = subprocess.run(
                cmd, cwd=tmp, capture_output=True, text=True, timeout=timeout,
                preexec_fn=_limits,  # type: ignore[arg-type]
            )
            return proc.returncode, proc.stdout[-4000:], proc.stderr[-4000:]
        except FileNotFoundError as e:
            return 127, "", f"tool binary missing: {e}"
        except subprocess.TimeoutExpired:
            return 124, "", f"timed out after {timeout}s"


DOCKER_FALLBACK = "docker run --rm --network=none --memory=512m --cpus=1"
