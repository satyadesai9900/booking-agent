"""
Request Context for Agent Skills.
The server passes the signed-in user through LangGraph's RunnableConfig
(`configurable.user_id` / `configurable.user_email`). Tools declare a `config: RunnableConfig`
parameter, which LangChain injects at runtime and hides from the model, so the model can never
choose or spoof which user a tool acts for.
"""

from typing import Optional
from langchain_core.runnables import RunnableConfig

# Owner used when the agent runs outside the web server (e.g. agent.cli on a local machine)
LOCAL_CLI_USER_ID = "local-cli"


def current_user_id(config: Optional[RunnableConfig]) -> str:
    configurable = (config or {}).get("configurable", {})
    return configurable.get("user_id") or LOCAL_CLI_USER_ID


def current_user_email(config: Optional[RunnableConfig]) -> Optional[str]:
    """Email of the signed-in user, or None when running locally without a web session."""
    configurable = (config or {}).get("configurable", {})
    email = configurable.get("user_email")
    return email.strip().lower() if email else None
