from pydantic import BaseModel
from typing import Optional
from enum import Enum


class AgentRole(str, Enum):
    ANALYST = "analyst"
    CRITIC = "critic"
    EXPERT = "expert"
    SYNTHESIZER = "synthesizer"
    MODERATOR = "moderator"
    SYSTEM = "system"


class AgentMessage(BaseModel):
    """A single message from an agent during the discussion."""
    agent: AgentRole
    agent_name: str
    content: str
    round: int  # 0 = intro, 1+ = debate rounds, -1 = final synthesis
    timestamp: Optional[str] = None


class DiscussionRequest(BaseModel):
    """Incoming query from the user."""
    query: str
    rounds: int = 2


class DiscussionResult(BaseModel):
    """Full result of a completed discussion."""
    query: str
    messages: list[AgentMessage]
    final_answer: str
    total_rounds: int


class StreamEvent(BaseModel):
    """SSE event payload."""
    event: str  # "agent_message" | "stream_chunk" | "done" | "error"
    session_id: str
    data: dict
