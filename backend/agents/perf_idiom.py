"""Perf & Idiom agent."""
from backend.agents.base import BaseAgent


class PerfIdiomAgent(BaseAgent):
    name = "perf_idiom"
    allowed_tools = ["read_file", "run_linter", "complexity_check"]
    system_file = "perf_idiom.system.md"

    def focus(self) -> str:
        return "N+1, O(n^2), style, maintainability, dead code"
