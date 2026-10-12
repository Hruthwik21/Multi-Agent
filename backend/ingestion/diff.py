"""Unified diff utilities: split per-file hunks, extract added line numbers."""
from __future__ import annotations

import re

FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)\s*$")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

from dataclasses import dataclass, field


@dataclass
class FileHunk:
    path: str
    patch: str
    added_lines: list[int] = field(default_factory=list)


def parse_diff(diff_text: str) -> list[FileHunk]:
    files: list[FileHunk] = []
    current_path = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_path, current_lines
        if current_path and current_lines:
            patch = "\n".join(current_lines)
            files.append(FileHunk(path=current_path, patch=patch,
                                  added_lines=added_line_numbers(patch)))
        current_lines = []

    for line in diff_text.splitlines():
        m = FILE_RE.match(line)
        if m:
            flush()
            current_path = m.group(2)
            current_lines = [line]
        elif line.startswith("+++ b/"):
            current_path = line[6:].strip()
            current_lines.append(line)
        elif current_path:
            current_lines.append(line)
        elif line.startswith("--- ") or line.startswith("+++ "):
            continue
    flush()
    # fallback: File: style diffs without diff --git header
    if not files and ("--- " in diff_text or "+++ " in diff_text):
        files.append(FileHunk(path="changed.py", patch=diff_text,
                              added_lines=added_line_numbers(diff_text)))
    return files


def added_line_numbers(patch: str) -> list[int]:
    out: list[int] = []
    new_line = 0
    for line in patch.splitlines():
        hm = HUNK_RE.match(line)
        if hm:
            new_line = int(hm.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            out.append(new_line)
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        else:
            new_line += 1
    return out
