"""
LangGraph Agent Package.
Industry-standard modular architecture for conversational AI agents.
"""

from agent.state import AgentState
from agent.llm import get_llm, get_model, build_chain, AgentOutputParser, ACTIVE_LLM
from agent.graph import build_agent_graph, SYSTEM_PROMPT
from agent.skills import (
    browse_web,
    book_ticket,
    check_ticket_status,
    BOOKING_DATABASE,
    TOOLS,
)
from agent import skills
from agent import skills as skill  # alias so agent.skill works directly

__all__ = [
    "AgentState",
    "get_llm",
    "get_model",
    "build_chain",
    "AgentOutputParser",
    "ACTIVE_LLM",
    "build_agent_graph",
    "SYSTEM_PROMPT",
    "TOOLS",
    "BOOKING_DATABASE",
    "browse_web",
    "book_ticket",
    "check_ticket_status",
    "skills",
    "skill",
]

