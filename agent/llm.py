"""
LLM Provider and Initialization Module.
Provides single-line LLM switching and integration with LCEL chains.
"""

from typing import Optional, Any
from langsmith import traceable
from agent.chain import (
    ACTIVE_LLM,
    get_model,
    build_chain,
    AgentOutputParser,
    StrOutputParser,
)


@traceable(name="get_llm")
def get_llm(
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model_name: Optional[str] = None
):
    """
    Instantiate the model for the configured provider.
    Change the provider with a single line: ACTIVE_LLM = "gemini", "openai", etc.
    """
    return get_model(provider=provider or ACTIVE_LLM, api_key=api_key, model_name=model_name)


__all__ = [
    "ACTIVE_LLM",
    "get_llm",
    "get_model",
    "build_chain",
    "AgentOutputParser",
    "StrOutputParser",
]
