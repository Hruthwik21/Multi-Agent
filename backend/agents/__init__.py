"""
Agent package for PolyMind.
Each module defines a single AI agent persona.
"""
from .analyst import create_analyst_agent
from .critic import create_critic_agent
from .expert import create_expert_agent
from .synthesizer import create_synthesizer_agent

__all__ = [
    "create_analyst_agent",
    "create_critic_agent",
    "create_expert_agent",
    "create_synthesizer_agent",
]
