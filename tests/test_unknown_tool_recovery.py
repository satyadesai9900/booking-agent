"""
Offline tests for recovering when the model calls a tool we never offered (no LLM calls).
Reproduces Groq's 400 `tool_use_failed` response to gpt-oss calling its built-in `browser.open`.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from agent.graph import MAX_TOOL_USE_RETRIES, build_agent_graph, unknown_tool_call

GROQ_TOOL_USE_FAILED = (
    "Error code: 400 - {'error': {'message': 'Model called browser tool which was not enabled for this "
    "request', 'type': 'invalid_request_error', 'code': 'tool_use_failed', 'failed_generation': "
    "'{\"name\": \"browser.open\", \"arguments\": {\"id\":\"https://www.confirmtkt.com/pnr-status/4521369874\"}}'}}"
)


class BadRequestError(Exception):
    """Stands in for openai.BadRequestError, which langchain-openai raises for Groq 400s."""


def scripted_chain(*steps):
    """A fake model: each call takes the next step, raising it if it is an exception."""
    calls = []

    def respond(messages):
        calls.append(list(messages))
        step = steps[len(calls) - 1]
        if isinstance(step, Exception):
            raise step
        return step

    return RunnableLambda(respond), calls


def _run(chain):
    agent = build_agent_graph(chain)
    config = {"configurable": {"thread_id": "t1"}}
    state = agent.invoke({"messages": [HumanMessage(content="Status of PNR 4521369874?")]}, config=config)
    return agent, config, state


def test_unknown_tool_call_parses_groq_error():
    assert unknown_tool_call(BadRequestError(GROQ_TOOL_USE_FAILED)) == "browser.open"
    assert unknown_tool_call(BadRequestError("code: tool_use_failed")) == "unknown"
    assert unknown_tool_call(RuntimeError("Error code: 429 rate limited")) is None


def test_recovers_after_unknown_tool_call():
    chain, calls = scripted_chain(BadRequestError(GROQ_TOOL_USE_FAILED), AIMessage(content="Here are the portals."))
    agent, config, state = _run(chain)

    assert state["messages"][-1].content == "Here are the portals."
    assert len(calls) == 2
    correction = calls[1][-1]
    assert isinstance(correction, SystemMessage)
    assert "`browser.open`" in correction.content and "browse_web" in correction.content
    # The correction is only for the retried request; it is not saved in the conversation
    saved = agent.get_state(config).values["messages"]
    assert not any(isinstance(m, SystemMessage) for m in saved)


def test_gives_up_after_max_retries():
    failures = [BadRequestError(GROQ_TOOL_USE_FAILED)] * (MAX_TOOL_USE_RETRIES + 1)
    chain, calls = scripted_chain(*failures)
    with pytest.raises(BadRequestError):
        _run(chain)
    assert len(calls) == MAX_TOOL_USE_RETRIES + 1


def test_other_errors_are_not_retried():
    chain, calls = scripted_chain(RuntimeError("Error code: 401 invalid api key"))
    with pytest.raises(RuntimeError):
        _run(chain)
    assert len(calls) == 1


def test_system_prompt_names_only_real_tools():
    from agent.graph import SYSTEM_PROMPT
    assert "ONLY tools you have" in SYSTEM_PROMPT.content
    assert "`browse_web` with the `url` argument" in SYSTEM_PROMPT.content
