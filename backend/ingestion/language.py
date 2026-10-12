"""Language detection by extension + content sniffing."""
from __future__ import annotations

EXT_MAP = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
}


def detect_language(path: str, content: str = "") -> str:
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext in EXT_MAP:
        return EXT_MAP[ext]
    # content sniffing fallback
    head = content[:2000]
    if "def " in head and ("import " in head or "from " in head):
        return "python"
    if "interface " in head or ": string" in head or "=>" in head:
        return "typescript"
    if "function " in head or "const " in head:
        return "javascript"
    return "unknown"


def overall_language(langs: list[str]) -> str:
    known = [l for l in langs if l != "unknown"]
    if not known:
        return "unknown"
    uniq = set(known)
    if len(uniq) == 1:
        v = uniq.pop()
        return v if v in ("python", "typescript", "javascript") else "unknown"
    return "mixed"
