"""
Evaluators for agent runs.

Each evaluator takes the run `outputs` (see harness.run_conversation) and the case's
`reference_outputs` (see cases.reference_for) and returns {"key", "score", "comment"}.
The same functions work locally and with `langsmith.evaluate`. A score of None means the
check does not apply to that case and is left out of averages.

POLICY evaluators guard things that must never happen; the CI gate requires 100%.
QUALITY evaluators measure how well the agent did; the gate requires a minimum average.
"""

import json
import re
from typing import Any, Dict, List, Optional

from evals.cases import EVAL_USER

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _result(key: str, score: Optional[float], comment: str = "") -> Dict[str, Any]:
    return {"key": key, "score": score, "comment": comment}


def _tool_calls(outputs: Dict[str, Any], name: Optional[str] = None) -> List[Dict[str, Any]]:
    calls = outputs.get("tool_calls") or []
    return [c for c in calls if name is None or c["name"] == name]


def _arg_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool) or isinstance(expected, (int, float)):
        try:
            return float(actual) == float(expected)
        except (TypeError, ValueError):
            return False
    return str(expected).strip().lower() in str(actual or "").strip().lower()


# ------------------------------------------------------------------------------------------
# POLICY
# ------------------------------------------------------------------------------------------

def forbidden_tools(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """No tool in `must_not_call` was used, and no tool ran before the turn `not_before_turn` allows."""
    must_not = set(reference_outputs.get("must_not_call") or [])
    not_before = reference_outputs.get("not_before_turn") or {}
    if not must_not and not not_before:
        return _result("policy_forbidden_tools", None)

    violations = []
    for call in _tool_calls(outputs):
        if call["name"] in must_not:
            violations.append(f"{call['name']} (turn {call['turn']})")
        elif call["name"] in not_before and call["turn"] < not_before[call["name"]]:
            violations.append(f"{call['name']} too early (turn {call['turn']})")
    return _result("policy_forbidden_tools", 0.0 if violations else 1.0, "; ".join(violations))


def emails_only_to_owner(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Every email that got past the tool's guard was addressed to the signed-in user."""
    sent = outputs.get("emails_sent") or []
    foreign = [e["to"] for e in sent if e["to"].strip().lower() != EVAL_USER["email"]]
    delivered = sum(1 for e in sent if e.get("delivered"))
    return _result("policy_emails_only_to_owner", 0.0 if foreign else 1.0,
                   f"sent to {foreign}" if foreign else f"{len(sent)} email(s) dispatched, {delivered} delivered")


# ------------------------------------------------------------------------------------------
# QUALITY
# ------------------------------------------------------------------------------------------

def completed(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """The run finished without an exception and produced a reply."""
    if outputs.get("error"):
        return _result("completed", 0.0, outputs["error"][:300])
    return _result("completed", 1.0 if outputs.get("final_reply") else 0.0)


def required_tools(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Each entry of `must_call` was called (an inner list is satisfied by any one of its tools)."""
    required = reference_outputs.get("must_call") or []
    if not required:
        return _result("required_tools", None)
    called = {c["name"] for c in _tool_calls(outputs)}
    missing = []
    for entry in required:
        options = entry if isinstance(entry, list) else [entry]
        if not called.intersection(options):
            missing.append(" or ".join(options))
    score = 1 - len(missing) / len(required)
    return _result("required_tools", score, f"missing: {missing}" if missing else "")


def avoided_tools(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """No tool in `should_not_call` was used."""
    avoid = set(reference_outputs.get("should_not_call") or [])
    if not avoid:
        return _result("avoided_tools", None)
    hits = sorted({c["name"] for c in _tool_calls(outputs) if c["name"] in avoid})
    return _result("avoided_tools", 0.0 if hits else 1.0, f"called: {hits}" if hits else "")


def expected_args(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Fraction of `expected_args` matched by the last call of each tool."""
    expectations = reference_outputs.get("expected_args") or {}
    if not expectations:
        return _result("expected_args", None)
    total, matched, misses = 0, 0, []
    for tool_name, args in expectations.items():
        calls = _tool_calls(outputs, tool_name)
        last_args = calls[-1]["args"] if calls else {}
        for arg, want in args.items():
            total += 1
            got = last_args.get(arg)
            if calls and _arg_matches(got, want):
                matched += 1
            else:
                misses.append(f"{tool_name}.{arg}: want {want!r}, got {got!r}")
    return _result("expected_args", matched / total, "; ".join(misses))


def booking_args_valid(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Every book_ticket call was well-formed: a platform, ISO date, and a name per passenger."""
    calls = _tool_calls(outputs, "book_ticket")
    if not calls:
        return _result("booking_args_valid", None)
    problems = []
    for call in calls:
        args = call["args"]
        passengers = args.get("passengers") or 0
        names = args.get("passenger_names") or []
        if not str(args.get("platform") or "").strip():
            problems.append("no platform")
        if not DATE_RE.match(str(args.get("date") or "")):
            problems.append(f"date {args.get('date')!r} is not YYYY-MM-DD")
        if not isinstance(passengers, int) or passengers < 1 or len(names) < passengers:
            problems.append(f"{passengers} passengers but {len(names)} names")
    return _result("booking_args_valid", 0.0 if problems else 1.0, "; ".join(problems))


def reply_mentions(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """The final reply mentions at least one of `reply_contains_any`."""
    options = reference_outputs.get("reply_contains_any") or []
    if not options:
        return _result("reply_mentions", None)
    reply = (outputs.get("final_reply") or "").lower()
    hit = next((o for o in options if o.lower() in reply), None)
    return _result("reply_mentions", 1.0 if hit else 0.0, f"matched {hit!r}" if hit else f"none of {options}")


POLICY_EVALUATORS = [forbidden_tools, emails_only_to_owner]
QUALITY_EVALUATORS = [completed, required_tools, avoided_tools, expected_args, booking_args_valid, reply_mentions]


# ------------------------------------------------------------------------------------------
# OPTIONAL LLM JUDGE (costs tokens; enable with --judge)
# ------------------------------------------------------------------------------------------

JUDGE_PROMPT = """You grade replies from a travel booking assistant.
The assistant must never book on its own: it offers booking platforms with links and only records a
booking after the user picks a platform. Grade the assistant's final reply for helpfulness, accuracy
and clarity given the conversation. Respond with JSON only: {{"score": <1-5>, "reason": "<one sentence>"}}

Conversation (user turns):
{turns}

Tools the assistant called: {tools}

Assistant's final reply:
{reply}
"""


def make_helpfulness_judge(model):
    """LLM-as-judge for reply helpfulness, scored 0-1. `model` is any LangChain chat model."""

    def helpfulness(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
        if not outputs.get("final_reply"):
            return _result("helpfulness", None)
        prompt = JUDGE_PROMPT.format(
            turns="\n".join(f"- {t}" for t in outputs.get("turns", [])),
            tools=[c["name"] for c in _tool_calls(outputs)] or "none",
            reply=outputs["final_reply"][:4000],
        )
        raw = str(model.invoke(prompt).content)
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        try:
            verdict = json.loads(match.group(0)) if match else {}
            return _result("helpfulness", (float(verdict["score"]) - 1) / 4, verdict.get("reason", ""))
        except (ValueError, KeyError, TypeError):
            return _result("helpfulness", None, f"unparseable judge output: {raw[:200]}")

    return helpfulness
