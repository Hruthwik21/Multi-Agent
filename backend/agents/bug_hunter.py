"""Bug Hunter agent."""
from backend.agents.base import BaseAgent


class BugHunterAgent(BaseAgent):
    name = "bug_hunter"
    allowed_tools = ["read_file", "run_tests", "ast_query"]
    system_file = "bug_hunter.system.md"

    def focus(self) -> str:
        return "logic errors, null safety, edge cases, off-by-one, race conditions"
