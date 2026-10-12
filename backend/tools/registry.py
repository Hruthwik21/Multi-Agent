"""@tool decorator + registry: uniform interface + Gemini schema generation."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ToolFn = Callable[..., Awaitable[Any]]
_REGISTRY: dict[str, dict[str, Any]] = {}


def tool(name: str, description: str, params_schema: dict[str, Any]):  # type: ignore[no-untyped-def]
    def deco(fn: ToolFn) -> ToolFn:
        _REGISTRY[name] = {"name": name, "description": description,
                           "parameters": params_schema, "fn": fn}
        fn._tool_spec = _REGISTRY[name]  # type: ignore[attr-defined]
        return fn
    return deco


def list_tools(names: list[str] | None = None) -> list[dict[str, Any]]:
    if names is None:
        return list(_REGISTRY.values())
    return [t for n, t in _REGISTRY.items() if n in names]


def get_tool(name: str) -> dict[str, Any] | None:
    return _REGISTRY.get(name)
