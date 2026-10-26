"""
Runs agent conversations for evals.

Bookings always go to the throwaway DATA_DIR set up by `evals/__init__.py`. Outbound calls
depend on the mode:

- Web (`live_web`): off returns a canned page, so results don't depend on the network;
  on uses the real fetcher and DuckDuckGo search.
- Email (`live_email`): off records emails in the outbox without sending; on sends them through
  the real Gmail SMTP path (needs GMAIL_* settings and a real EVAL_USER_EMAIL inbox).

Either way, every email that gets past the tool's recipient guard is recorded in the outbox,
so the policy evaluators see the same thing in both modes.
"""

import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

import evals  # noqa: F401  (isolates DATA_DIR before the agent modules load)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.chain import ACTIVE_LLM, build_chain, get_model_name
from agent.graph import build_agent_graph
from agent.skills import browsing, gmail
from evals.cases import EVAL_USER

# Provider/network errors worth retrying: they say nothing about the agent's behaviour
TRANSIENT_ERRORS = {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError",
                    "ServiceUnavailableError", "ConnectionError", "Timeout"}


class QuotaExhausted(RuntimeError):
    """The provider's daily quota is used up; every further case would fail the same way."""


class _FakeResponse:
    status_code = 200
    is_redirect = False
    headers: Dict[str, str] = {}
    text = "<html><body>Canned page used during evals. No live data available.</body></html>"

    def json(self) -> Dict[str, Any]:
        return {"AbstractText": "", "RelatedTopics": []}


class _FakeRequests:
    """Stands in for the `requests` module inside agent.skills.browsing."""

    def __init__(self, real):
        self.utils = real.utils

    def get(self, *args, **kwargs):
        return _FakeResponse()


def check_live_email_ready() -> None:
    """Refuse live email runs that would fail or mail someone else's inbox."""
    if EVAL_USER["email"].endswith("@example.com"):
        raise RuntimeError("Live email needs EVAL_USER_EMAIL set to an inbox you own; eval emails are sent there.")
    if not (gmail.config.gmail_sender_email and gmail.config.gmail_app_password) or             gmail.config.gmail_app_password == "your_16_char_google_app_password":
        raise RuntimeError("Live email needs GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD in env/.env.")


@contextmanager
def sandboxed(live_web: bool = False, live_email: bool = False) -> Iterator[List[Dict[str, Any]]]:
    """
    Install the eval doubles for the duration of the block.
    Yields the outbox: one {"to", "subject", "delivered", "result"} entry per email dispatched.
    """
    outbox: List[Dict[str, Any]] = []
    real_dispatch = gmail._dispatch_gmail

    def recording_dispatch(recipient_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> str:
        if live_email:
            result = real_dispatch(recipient_email, subject, text_body, html_body)
            delivered = "successfully sent" in result
        else:
            result = f"Email sent successfully to {recipient_email} (subject: {subject})."
            delivered = False
        outbox.append({"to": recipient_email, "subject": subject, "delivered": delivered, "result": result[:300]})
        return result

    saved = (gmail._dispatch_gmail, browsing._fetch_public_url, browsing.requests)
    gmail._dispatch_gmail = recording_dispatch
    if not live_web:
        browsing._fetch_public_url = lambda url: _FakeResponse()
        browsing.requests = _FakeRequests(saved[2])
    try:
        yield outbox
    finally:
        gmail._dispatch_gmail, browsing._fetch_public_url, browsing.requests = saved


def build_eval_agent(model: Optional[Any] = None):
    """The production graph and prompt, with in-memory checkpoints."""
    return build_agent_graph(build_chain(model=model), checkpointer=MemorySaver())


def _turn_messages(messages: List[Any]) -> List[Any]:
    """Messages produced after the most recent user message."""
    for idx in range(len(messages) - 1, -1, -1):
        if isinstance(messages[idx], HumanMessage):
            return messages[idx + 1:]
    return messages


def run_conversation(agent, turns: List[str], case_id: str = "adhoc", attempts: int = 3,
                     live_web: bool = False, live_email: bool = False) -> Dict[str, Any]:
    """
    Send each user turn on a fresh thread and collect what the agent did.
    Returns {"turns", "replies", "final_reply", "tool_calls", "emails_sent", "error", "attempts"}.
    A conversation that hits a transient provider error is restarted from scratch on a new thread.
    """
    for attempt in range(1, attempts + 1):
        outputs = _run_once(agent, turns, case_id, live_web, live_email)
        outputs["attempts"] = attempt
        if "per day" in (outputs["error"] or ""):
            raise QuotaExhausted(outputs["error"][:400])
        error_type = (outputs["error"] or "").split(":", 1)[0]
        if error_type not in TRANSIENT_ERRORS or attempt == attempts:
            return outputs
        time.sleep(5 * attempt)
    return outputs


def _run_once(agent, turns: List[str], case_id: str, live_web: bool, live_email: bool) -> Dict[str, Any]:
    thread_id = f"eval-{case_id}-{uuid.uuid4().hex[:8]}"
    config = {
        "configurable": {"thread_id": thread_id, "user_id": EVAL_USER["id"], "user_email": EVAL_USER["email"]},
        "run_name": "eval_turn",
        "tags": ["eval", ACTIVE_LLM],
        "metadata": {"case_id": case_id, "live_web": live_web, "live_email": live_email, "llm_provider": ACTIVE_LLM, "llm_model": get_model_name()},
        "recursion_limit": 25,
    }
    outputs: Dict[str, Any] = {"turns": turns, "replies": [], "final_reply": "", "tool_calls": [],
                               "emails_sent": [], "error": None}

    with sandboxed(live_web=live_web, live_email=live_email) as outbox:
        try:
            for turn_idx, text in enumerate(turns):
                state = agent.invoke({"messages": [HumanMessage(content=text)]}, config=config)
                produced = _turn_messages(state.get("messages", []))
                results = {m.tool_call_id: str(m.content) for m in produced if isinstance(m, ToolMessage)}
                reply = ""
                for msg in produced:
                    if not isinstance(msg, AIMessage):
                        continue
                    for tc in msg.tool_calls or []:
                        outputs["tool_calls"].append({
                            "turn": turn_idx,
                            "name": tc.get("name"),
                            "args": tc.get("args") or {},
                            "result": results.get(tc.get("id"), "")[:500],
                        })
                    if isinstance(msg.content, str) and msg.content.strip():
                        reply = msg.content
                outputs["replies"].append(reply)
            outputs["final_reply"] = outputs["replies"][-1] if outputs["replies"] else ""
        except Exception as exc:  # a crash is scored by the `completed` evaluator, not raised
            outputs["error"] = f"{type(exc).__name__}: {exc}"
        outputs["emails_sent"] = list(outbox)
    return outputs
