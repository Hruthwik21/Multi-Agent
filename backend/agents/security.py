"""Security agent."""
from backend.agents.base import BaseAgent


class SecurityAgent(BaseAgent):
    name = "security"
    allowed_tools = ["semgrep", "read_file", "search_cve"]
    system_file = "security.system.md"

    def focus(self) -> str:
        return "injection, authz, secrets, unsafe deserialization, SSRF"
