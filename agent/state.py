"""
Agent State Definition.
"""

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph agent state containing the message conversation history."""
    messages: Annotated[List[BaseMessage], add_messages]
