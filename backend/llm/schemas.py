"""Function-calling schemas exposed to Gemini (JSON-schema style dicts)."""
from __future__ import annotations


def gemini_tools_schema(tools: list[dict]) -> list[dict]:
    """Convert internal tool specs to Gemini function-declaration format (passthrough)."""
    decls = []
    for t in tools:
        decls.append(
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return [{"function_declarations": decls}] if decls else []
