"""
Agent Skills Package.
Exposes tools for browsing, ticket booking, and status checking.
"""

from agent.skills.browsing import browse_web
from agent.skills.booking import (
    book_ticket,
    check_ticket_status,
    get_booking_platforms,
    get_database_status,
    booking_db_manager,
    BOOKING_DATABASE,
)
from agent.skills.gmail import send_booking_email, send_email

# Full tool suite supplied to LangGraph
TOOLS = [
    get_booking_platforms,
    browse_web,
    book_ticket,
    check_ticket_status,
    get_database_status,
    send_booking_email,
    send_email,
]

__all__ = [
    "get_booking_platforms",
    "browse_web",
    "book_ticket",
    "check_ticket_status",
    "get_database_status",
    "send_booking_email",
    "send_email",
    "booking_db_manager",
    "BOOKING_DATABASE",
    "TOOLS",
]
