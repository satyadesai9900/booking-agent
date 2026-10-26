"""Offline checks that the evaluators score known outputs correctly (no LLM calls)."""

from evals.cases import CASES, EVAL_USER, reference_for
from evals.evaluators import (
    avoided_tools,
    booking_args_valid,
    completed,
    emails_only_to_owner,
    expected_args,
    forbidden_tools,
    reply_mentions,
    required_tools,
)
from evals.run import summarize


def _outputs(calls=(), reply="Done.", emails=(), error=None):
    return {
        "turns": ["hi"],
        "final_reply": reply,
        "tool_calls": [{"turn": t, "name": n, "args": a, "result": ""} for t, n, a in calls],
        "emails_sent": list(emails),
        "error": error,
    }


GOOD_BOOKING = {
    "platform": "Google Flights", "origin": "Delhi", "destination": "Mumbai",
    "date": "2026-12-15", "passengers": 1, "passenger_names": ["Asha Rao"],
}


def test_forbidden_tools_flags_any_forbidden_call():
    ref = {"must_not_call": ["book_ticket"]}
    assert forbidden_tools(_outputs([(0, "get_booking_platforms", {})]), ref)["score"] == 1.0
    assert forbidden_tools(_outputs([(0, "book_ticket", GOOD_BOOKING)]), ref)["score"] == 0.0


def test_forbidden_tools_enforces_not_before_turn():
    ref = {"not_before_turn": {"book_ticket": 1}}
    assert forbidden_tools(_outputs([(1, "book_ticket", GOOD_BOOKING)]), ref)["score"] == 1.0
    result = forbidden_tools(_outputs([(0, "book_ticket", GOOD_BOOKING)]), ref)
    assert result["score"] == 0.0 and "too early" in result["comment"]


def test_forbidden_tools_not_applicable_without_rules():
    assert forbidden_tools(_outputs(), {})["score"] is None


def test_emails_only_to_owner():
    own = {"to": EVAL_USER["email"], "subject": "x"}
    other = {"to": "bob@other.example", "subject": "x"}
    assert emails_only_to_owner(_outputs(emails=[own]), {})["score"] == 1.0
    assert emails_only_to_owner(_outputs(emails=[own, other]), {})["score"] == 0.0


def test_required_tools_supports_any_of_groups():
    ref = {"must_call": [["check_ticket_status", "browse_web"], "get_database_status"]}
    assert required_tools(_outputs([(0, "browse_web", {}), (0, "get_database_status", {})]), ref)["score"] == 1.0
    assert required_tools(_outputs([(0, "browse_web", {})]), ref)["score"] == 0.5


def test_avoided_tools():
    ref = {"should_not_call": ["send_email"]}
    assert avoided_tools(_outputs(), ref)["score"] == 1.0
    assert avoided_tools(_outputs([(0, "send_email", {})]), ref)["score"] == 0.0


def test_expected_args_partial_credit_uses_last_call():
    ref = {"expected_args": {"book_ticket": {"platform": "google flights", "passengers": 2}}}
    calls = [(0, "book_ticket", {"platform": "Kayak", "passengers": 2}), (1, "book_ticket", GOOD_BOOKING)]
    result = expected_args(_outputs(calls), ref)
    assert result["score"] == 0.5
    assert "passengers" in result["comment"]


def test_expected_args_zero_when_tool_never_called():
    assert expected_args(_outputs(), {"expected_args": {"book_ticket": {"platform": "Kayak"}}})["score"] == 0.0


def test_booking_args_valid():
    assert booking_args_valid(_outputs(), {})["score"] is None
    assert booking_args_valid(_outputs([(0, "book_ticket", GOOD_BOOKING)]), {})["score"] == 1.0
    bad = dict(GOOD_BOOKING, date="Dec 15", passengers=2)
    result = booking_args_valid(_outputs([(0, "book_ticket", bad)]), {})
    assert result["score"] == 0.0
    assert "YYYY-MM-DD" in result["comment"] and "2 passengers but 1 names" in result["comment"]


def test_reply_mentions_is_case_insensitive():
    ref = {"reply_contains_any": ["IRCTC"]}
    assert reply_mentions(_outputs(reply="Try irctc.co.in"), ref)["score"] == 1.0
    assert reply_mentions(_outputs(reply="Try Trainline"), ref)["score"] == 0.0


def test_completed_scores_errors_as_zero():
    assert completed(_outputs(), {})["score"] == 1.0
    assert completed(_outputs(error="RateLimitError: slow down"), {})["score"] == 0.0


def test_summary_gates():
    def row(policy, quality):
        return {"scores": {
            "policy_forbidden_tools": {"score": policy},
            "required_tools": {"score": quality},
            "expected_args": {"score": None},
        }}

    passing = summarize([row(1.0, 1.0), row(1.0, 0.8)], min_quality=0.8)
    assert passing["policy_passed"] and passing["quality_passed"]
    assert passing["metrics"]["required_tools"] == 0.9
    assert "expected_args" not in passing["metrics"]

    assert not summarize([row(1.0, 1.0), row(0.0, 1.0)], min_quality=0.8)["policy_passed"]
    assert not summarize([row(1.0, 0.5)], min_quality=0.8)["quality_passed"]


def test_cases_are_well_formed():
    known_tools = {"get_booking_platforms", "browse_web", "book_ticket", "check_ticket_status",
                   "get_database_status", "send_booking_email", "send_email"}
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)), "case ids must be unique"
    for case in CASES:
        assert case["turns"], case["id"]
        ref = reference_for(case)
        named = set(ref.get("must_not_call", [])) | set(ref.get("should_not_call", []))
        named |= set(ref.get("not_before_turn", {})) | set(ref.get("expected_args", {}))
        for entry in ref.get("must_call", []):
            named |= set(entry if isinstance(entry, list) else [entry])
        assert named <= known_tools, f"{case['id']} names unknown tools: {named - known_tools}"
        for tool, turn in ref.get("not_before_turn", {}).items():
            assert turn < len(case["turns"]), f"{case['id']}: {tool} can never be called"


def test_daily_quota_stops_the_run_instead_of_scoring_failures(monkeypatch):
    import pytest
    from evals import harness

    def quota_hit(*args, **kwargs):
        return {"error": "RateLimitError: Rate limit reached ... on tokens per day (TPD): Limit 200000"}

    monkeypatch.setattr(harness, "_run_once", quota_hit)
    with pytest.raises(harness.QuotaExhausted):
        harness.run_conversation(agent=None, turns=["hi"])
