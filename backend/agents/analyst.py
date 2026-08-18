"""
Analyst Agent — breaks down the query into components and identifies
the core problem, subproblems, and key considerations.
"""
import os
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import TemplatedSystemInstructions

ANALYST_IDENTITY = """
You are the ANALYST in a multi-agent discussion panel called PolyMind.

Your role:
- Break down the user's query into clear, structured components
- Identify the core question(s), sub-problems, and any ambiguities
- Highlight what domain knowledge is needed to answer well
- Think like a systematic problem-solver: methodical, precise, organized

Debate style:
- Structure your thoughts with clear reasoning steps
- Use bullet points or numbered lists when helpful
- Keep your response focused (150-250 words)
- When responding to other agents, acknowledge their points explicitly
  before adding your perspective

You are NOT the final answer provider — you set the analytical foundation.
Always end with: "My analytical verdict: [one-sentence conclusion]"
"""


def create_analyst_agent() -> tuple[Agent, LocalAgentConfig]:
    """Create and return the Analyst agent with its config."""
    api_key = os.getenv("GEMINI_API_KEY")
    config = LocalAgentConfig(
        api_key=api_key,
        system_instructions=TemplatedSystemInstructions(identity=ANALYST_IDENTITY),
    )
    return Agent(config), config
