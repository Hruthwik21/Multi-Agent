"""
PolyMind Discussion Engine
--------------------------
Orchestrates the multi-round debate between AI agents.

Flow:
  Round 0 (Intro):   Analyst + Critic + Expert each give their initial take
  Round N (Debate):  Each agent reads all previous messages and responds
  Final:             Synthesizer reads everything and produces the final answer

Each agent response is yielded as an AgentMessage so callers can stream it.
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncIterator

from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import TemplatedSystemInstructions

from .models import AgentMessage, AgentRole


# ── Agent persona definitions ──────────────────────────────────────────────

ANALYST_IDENTITY = """
You are the ANALYST in a multi-agent discussion panel called PolyMind.
Your role: Break down the query into structured components. Identify core questions,
sub-problems, ambiguities, and what knowledge domains are needed.
Debate style: Methodical, precise. 150-250 words. Bullet-points when helpful.
When in later rounds, acknowledge other agents' points before adding your view.
Always end with: "Analytical verdict: [one-sentence conclusion]"
"""

CRITIC_IDENTITY = """
You are the CRITIC in a multi-agent discussion panel called PolyMind.
Your role: Challenge assumptions, find weaknesses and edge cases, explore alternative views.
Debate style: Direct, confident, constructive. 150-250 words.
Reference specific claims made by other agents.
Always end with: "Critical verdict: [one-sentence conclusion]"
"""

EXPERT_IDENTITY = """
You are the EXPERT in a multi-agent discussion panel called PolyMind.
Your role: Bring authoritative domain knowledge. Cite principles, best practices,
established facts. Distinguish well-established knowledge from ongoing debate.
Debate style: Authoritative but clear. 150-250 words.
When responding to others, validate correct points then add expert perspective.
Always end with: "Expert verdict: [one-sentence conclusion]"
"""

SYNTHESIZER_IDENTITY = """
You are the SYNTHESIZER in a multi-agent discussion panel called PolyMind.
Your role: Read the ENTIRE debate and produce the single best, most comprehensive answer.
- Integrate insights from Analyst, Critic, and Expert
- Resolve contradictions with balanced judgment
- Give a direct, complete, well-structured final answer
- For code queries: include clean, working code
- For factual queries: be accurate and thorough
Do NOT reference your own role. Just give the best possible answer naturally.
"""


# ── Helper: build context string from message history ─────────────────────

def _build_context(messages: list[AgentMessage], current_round: int) -> str:
    """Format message history into a readable context block for agents."""
    if not messages:
        return ""
    lines = ["\n--- DISCUSSION SO FAR ---"]
    for msg in messages:
        round_label = f"Round {msg.round}" if msg.round >= 0 else "Initial"
        lines.append(f"\n[{msg.agent_name.upper()} — {round_label}]:\n{msg.content}")
    lines.append(f"\n--- END OF DISCUSSION (you are responding in Round {current_round}) ---\n")
    return "\n".join(lines)


# ── Agent caller ───────────────────────────────────────────────────────────

async def _call_agent(
    identity: str,
    prompt: str,
    api_key: str,
) -> str:
    """Instantiate a fresh agent with the given identity and get a response."""
    config = LocalAgentConfig(
        api_key=api_key,
        system_instructions=TemplatedSystemInstructions(identity=identity),
    )
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()


# ── Core discussion loop ───────────────────────────────────────────────────

async def run_discussion(
    query: str,
    rounds: int = 2,
) -> AsyncIterator[AgentMessage]:
    """
    Run the full multi-agent discussion and yield AgentMessage objects
    as each agent responds. Callers can stream these to the frontend.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please add it to your .env file.\n"
            "Get a free key at: https://aistudio.google.com/app/api-keys"
        )

    messages: list[AgentMessage] = []

    agents = [
        (AgentRole.ANALYST, "Analyst", ANALYST_IDENTITY),
        (AgentRole.CRITIC, "Critic", CRITIC_IDENTITY),
        (AgentRole.EXPERT, "Expert", EXPERT_IDENTITY),
    ]

    # ── Rounds 0..N-1 : debate rounds ─────────────────────────────────────
    for round_num in range(rounds):
        for role, name, identity in agents:
            context = _build_context(messages, round_num)

            if round_num == 0:
                prompt = (
                    f"The user has submitted the following query to the PolyMind panel:\n\n"
                    f'"{query}"\n\n'
                    f"Please provide your initial {name.lower()} perspective on this query."
                )
            else:
                prompt = (
                    f"The user's original query was:\n\n"
                    f'"{query}"\n\n'
                    f"{context}\n"
                    f"Having read the discussion above, please provide your Round {round_num} "
                    f"response as the {name}. Build on, challenge, or refine what has been said."
                )

            content = await _call_agent(identity, prompt, api_key)

            msg = AgentMessage(
                agent=role,
                agent_name=name,
                content=content,
                round=round_num,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            messages.append(msg)
            yield msg

            # Small pause so the UI renders each card distinctly
            await asyncio.sleep(0.1)

    # ── Final synthesis ────────────────────────────────────────────────────
    context = _build_context(messages, -1)
    synthesis_prompt = (
        f"The user's original query was:\n\n"
        f'"{query}"\n\n'
        f"{context}\n"
        f"You have read {rounds} rounds of debate between the Analyst, Critic, and Expert. "
        f"Now produce the definitive, final answer to the user's query — the best possible "
        f"response that integrates all insights from the discussion."
    )

    final_content = await _call_agent(SYNTHESIZER_IDENTITY, synthesis_prompt, api_key)

    final_msg = AgentMessage(
        agent=AgentRole.SYNTHESIZER,
        agent_name="Synthesizer",
        content=final_content,
        round=-1,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    messages.append(final_msg)
    yield final_msg
