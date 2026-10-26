"""
LangChain LCEL Chain Module.
Combines the Model and Parser in an LCEL pipeline (model | parser).
Allows switching the active LLM with just a single line of code.
"""

import os
from typing import Optional, Any, List
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.runnables import Runnable, RunnableSequence

from env.config import config, get_gemini_api_key
from agent.skills import TOOLS
# Group traces under one LangSmith project unless the environment chooses another
os.environ.setdefault("LANGSMITH_PROJECT", "booking-agent")
# ==============================================================================
# 🎯 CHANGE YOUR LLM WITH JUST THIS SINGLE LINE OF CODE (or set LLM_PROVIDER / ACTIVE_LLM in env):
# Supported options: "gemini" | "openai" | "anthropic" | "groq" | "ollama" | "deepseek"
# ==============================================================================
ACTIVE_LLM: str = (os.getenv("LLM_PROVIDER") or os.getenv("ACTIVE_LLM") or "groq").lower().strip()
# ==============================================================================

# Default model per provider (each overridable via its <PROVIDER>_MODEL env var)
DEFAULT_MODELS = {
    "gemini": "gemini-3.8-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-5-5",
    "groq": "openai/gpt-oss-120b",
    "ollama": "llama3.2",
    "deepseek": "deepseek-chat",
}

# Env var holding each provider's API key (ollama runs locally without one)
API_KEY_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def get_model_name(provider: Optional[str] = None) -> str:
    """Model name the given (or active) provider will use."""
    selected = (provider or ACTIVE_LLM).lower().strip()
    if selected == "gemini":
        return config.gemini_model or DEFAULT_MODELS["gemini"]
    return os.getenv(f"{selected.upper()}_MODEL") or DEFAULT_MODELS.get(selected, "")


def is_api_key_configured(provider: Optional[str] = None) -> bool:
    """Whether the provider's API key is set to a real (non-placeholder) value."""
    selected = (provider or ACTIVE_LLM).lower().strip()
    env_var = API_KEY_ENV_VARS.get(selected)
    if env_var is None:
        return True
    value = os.getenv(env_var, "").strip()
    return bool(value) and not value.startswith("your_")


class AgentOutputParser(Runnable):
    """
    Parser in the LCEL chain.
    Parses and standardizes model output into an AIMessage while preserving
    tool calls, text content, and metadata for downstream LangGraph execution.
    """
    def invoke(self, input: Any, config=None) -> AIMessage:
        if isinstance(input, AIMessage):
            return input
        if hasattr(input, "content"):
            return AIMessage(
                content=str(input.content),
                tool_calls=getattr(input, "tool_calls", [])
            )
        return AIMessage(content=str(input))


def get_model(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
):
    """
    Instantiates the model for the chosen provider.
    Change the provider with a single line: ACTIVE_LLM = "openai", "gemini", etc.
    """
    selected_provider = (provider or ACTIVE_LLM).lower().strip()
    temp = temperature if temperature is not None else config.temperature

    if selected_provider == "gemini":
        key = api_key or get_gemini_api_key()
        name = model_name or get_model_name("gemini")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=name,
                google_api_key=key,
                temperature=temp,
            )
        except ImportError:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=name,
                api_key=key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                temperature=temp,
            )

    elif selected_provider == "openai":
        from langchain_openai import ChatOpenAI
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        name = model_name or get_model_name("openai")
        return ChatOpenAI(
            model=name,
            api_key=key,
            temperature=temp,
        )

    elif selected_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            name = model_name or get_model_name("anthropic")
            return ChatAnthropic(
                model_name=name,
                api_key=key,
                temperature=temp,
            )
        except ImportError:
            # Fallback to OpenAI-compatible OpenRouter or proxy if langchain-anthropic not installed
            from langchain_openai import ChatOpenAI
            key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            return ChatOpenAI(
                model=model_name or "anthropic/claude-3.5-sonnet",
                api_key=key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                temperature=temp,
            )

    elif selected_provider == "groq":
        from langchain_openai import ChatOpenAI
        key = api_key or os.getenv("GROQ_API_KEY", "")
        name = model_name or get_model_name("groq")
        return ChatOpenAI(
            model=name,
            api_key=key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temp,
        )

    elif selected_provider == "ollama":
        from langchain_openai import ChatOpenAI
        name = model_name or get_model_name("ollama")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return ChatOpenAI(
            model=name,
            api_key="ollama",
            base_url=base_url,
            temperature=temp,
        )

    elif selected_provider == "deepseek":
        from langchain_openai import ChatOpenAI
        key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        name = model_name or get_model_name("deepseek")
        return ChatOpenAI(
            model=name,
            api_key=key,
            base_url="https://api.deepseek.com/v1",
            temperature=temp,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: '{selected_provider}'. "
            f"Choose from: 'gemini', 'openai', 'anthropic', 'groq', 'ollama', 'deepseek'."
        )


def build_chain(
    model: Optional[Any] = None,
    tools: Optional[List[Any]] = None,
    parser: Optional[Runnable] = None,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> RunnableSequence:
    """
    Builds the LCEL Chain keeping model and parser combined using the pipe operator (|).

    Chain structure:
        chain = model_with_tools | parser
    """
    # 1. Resolve Model (can switch in a single line via ACTIVE_LLM or provider param)
    selected_model = model or get_model(provider=provider, model_name=model_name)

    # 2. Bind Tools if provided
    active_tools = tools if tools is not None else TOOLS
    model_with_tools = selected_model.bind_tools(active_tools) if active_tools else selected_model

    # 3. Resolve Parser
    selected_parser = parser or AgentOutputParser()

    # 4. Chain: Model and Parser kept in LCEL chain
    chain = model_with_tools | selected_parser
    return chain


# Pre-built standard output parser for text-only direct chains
text_parser = StrOutputParser()

__all__ = [
    "ACTIVE_LLM",
    "DEFAULT_MODELS",
    "get_model_name",
    "is_api_key_configured",
    "AgentOutputParser",
    "StrOutputParser",
    "get_model",
    "build_chain",
    "text_parser",
]
