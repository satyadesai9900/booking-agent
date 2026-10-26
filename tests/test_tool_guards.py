"""
Offline tests for the guards built into the tools themselves (no LLM calls).
These hold no matter what the model decides, so they are the last line of defence.
"""

import pytest

from agent.skills import book_ticket, check_ticket_status, send_booking_email, send_email
from evals.harness import sandboxed


def _config(user_id="user-a", email="a@example.com"):
    return {"configurable": {"user_id": user_id, "user_email": email}}


BOOKING = {
    "category": "flight", "origin": "Delhi", "destination": "Mumbai", "date": "2026-12-15",
    "passengers": 1, "passenger_names": ["Asha Rao"],
}


@pytest.mark.parametrize("platform", ["", "  ", "any", "None", "unknown"])
def test_book_ticket_refuses_without_a_chosen_platform(platform):
    result = book_ticket.invoke(dict(BOOKING, platform=platform), config=_config())
    assert result.startswith("Booking blocked")


def test_book_ticket_requires_a_name_per_passenger():
    result = book_ticket.invoke(dict(BOOKING, platform="Kayak", passengers=2), config=_config())
    assert "provide all 2 passenger names" in result


def test_bookings_are_private_to_their_owner():
    saved = book_ticket.invoke(dict(BOOKING, platform="Kayak", official_pnr="Q7RZ2K"), config=_config("user-a"))
    assert "Q7RZ2K" in saved

    assert "Booking Record for Q7RZ2K" in check_ticket_status.invoke({"booking_id": "Q7RZ2K"}, config=_config("user-a"))
    other_view = check_ticket_status.invoke({"booking_id": "Q7RZ2K"}, config=_config("user-b", "b@example.com"))
    assert "Booking Record" not in other_view
    assert "Asha Rao" not in other_view


@pytest.mark.parametrize("tool, args", [
    (send_email, {"recipient_email": "bob@other.example", "subject": "hi", "body": "hello"}),
    (send_booking_email, {"recipient_email": "bob@other.example", "booking_id": "AGT-FL-000000"}),
])
def test_email_tools_only_send_to_the_signed_in_user(tool, args):
    with sandboxed() as outbox:
        result = tool.invoke(args, config=_config())
    assert "Blocked" in result
    assert outbox == []


def test_email_to_own_address_is_sent():
    with sandboxed() as outbox:
        send_email.invoke({"recipient_email": "A@Example.com", "subject": "Trip", "body": "See you"}, config=_config())
    assert [e["to"] for e in outbox] == ["A@Example.com"]


def test_live_email_mode_calls_the_real_sender_and_records_delivery(monkeypatch):
    sent = []

    def smtp_stand_in(recipient_email, subject, text_body, html_body=None):
        sent.append(recipient_email)
        return f"Confirmation email successfully sent via Gmail to {recipient_email}!"

    from agent.skills import gmail
    monkeypatch.setattr(gmail, "_dispatch_gmail", smtp_stand_in)
    with sandboxed(live_email=True) as outbox:
        send_email.invoke({"recipient_email": "a@example.com", "subject": "Trip", "body": "x"}, config=_config())
        send_email.invoke({"recipient_email": "bob@other.example", "subject": "Trip", "body": "x"}, config=_config())
    assert sent == ["a@example.com"]
    assert [(e["to"], e["delivered"]) for e in outbox] == [("a@example.com", True)]


def test_canned_web_is_restored_after_sandbox():
    from agent.skills import browsing
    real_fetch = browsing._fetch_public_url
    with sandboxed():
        assert browsing._fetch_public_url is not real_fetch
    with sandboxed(live_web=True):
        assert browsing._fetch_public_url is real_fetch
    assert browsing._fetch_public_url is real_fetch
