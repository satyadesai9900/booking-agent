"""
Agent Skills Package.
Exposes tools for browsing, ticket booking, and status checking.
"""

from agent.skills.browsing import browse_web
from agent.skills.booking import book_ticket, check_ticket_status, BOOKING_DATABASE

# Full tool suite supplied to LangGraph
TOOLS = [browse_web, book_ticket, check_ticket_status]

__all__ = [
    "browse_web",
    "book_ticket",
    "check_ticket_status",
    "BOOKING_DATABASE",
    "TOOLS",
]
