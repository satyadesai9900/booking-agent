"""
Ticket Booking Skill Module.
Provides multi-category ticket reservation and status verification tools.
"""

import uuid
import datetime
from typing import List, Dict, Any
from langchain_core.tools import tool

# In-memory booking database store
BOOKING_DATABASE: Dict[str, Dict[str, Any]] = {}


@tool
def book_ticket(
    category: str,
    origin: str,
    destination: str,
    date: str,
    passengers: int,
    passenger_names: List[str],
    ticket_class: str = "Economy",
) -> str:
    """
    Book tickets for travel or entertainment.

    Args:
        category: Mode of transport or event ('flight', 'train', 'bus', 'movie', 'event').
        origin: Departure location, city, or venue.
        destination: Arrival destination or movie title.
        date: Travel or event date (e.g. 'YYYY-MM-DD').
        passengers: Number of tickets to book.
        passenger_names: List of passenger/attendee full names.
        ticket_class: Class tier (e.g., 'Economy', 'Premium', 'Business', 'First'). Default is 'Economy'.
    """
    if passengers <= 0:
        return "Booking failed: Number of passengers must be at least 1."

    if len(passenger_names) < passengers:
        return (
            f"Booking failed: Please provide all {passengers} passenger names "
            f"(only {len(passenger_names)} provided)."
        )

    # Generate unique booking reference (PNR)
    prefix_map = {
        "flight": "FL",
        "train": "TR",
        "bus": "BS",
        "movie": "MV",
        "event": "EV",
    }
    prefix = prefix_map.get(category.lower(), "BK")
    booking_id = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    # Sample pricing estimation
    base_fares = {
        "flight": 150.0,
        "train": 45.0,
        "bus": 25.0,
        "movie": 15.0,
        "event": 75.0,
    }
    multiplier = 2.0 if ticket_class.lower() in ["business", "first"] else 1.0
    total_cost = base_fares.get(category.lower(), 50.0) * passengers * multiplier

    booking_record = {
        "booking_id": booking_id,
        "category": category.capitalize(),
        "origin": origin,
        "destination": destination,
        "date": date,
        "passengers": passengers,
        "passenger_names": passenger_names,
        "ticket_class": ticket_class.capitalize(),
        "total_cost_usd": f"${total_cost:.2f}",
        "status": "CONFIRMED",
        "booked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    BOOKING_DATABASE[booking_id] = booking_record

    return (
        f"Ticket Confirmed Successfully!\n"
        f"----------------------------------------\n"
        f"Booking ID: {booking_id}\n"
        f"Category: {booking_record['category']}\n"
        f"Route / Event: {origin} -> {destination}\n"
        f"Date: {date}\n"
        f"Class: {ticket_class.capitalize()}\n"
        f"Passengers ({passengers}): {', '.join(passenger_names)}\n"
        f"Total Cost: ${total_cost:.2f}\n"
        f"Status: CONFIRMED\n"
        f"----------------------------------------"
    )


@tool
def check_ticket_status(booking_id: str) -> str:
    """
    Check the status and details of an existing ticket reservation by its booking ID.

    Args:
        booking_id: The reservation reference (e.g., 'FL-A1B2C3D4').
    """
    booking = BOOKING_DATABASE.get(booking_id.strip().upper())
    if not booking:
        return f"No booking found for ID '{booking_id}'. Please verify the ID."

    return (
        f"Booking Record for {booking_id}:\n"
        f"- Category: {booking['category']}\n"
        f"- Route/Event: {booking['origin']} to {booking['destination']}\n"
        f"- Date: {booking['date']}\n"
        f"- Class: {booking['ticket_class']}\n"
        f"- Passengers: {', '.join(booking['passenger_names'])}\n"
        f"- Status: {booking['status']}\n"
        f"- Booked At: {booking['booked_at']}"
    )
