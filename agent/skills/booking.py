"""
Ticket Booking Skill Module.
Provides platform selection, reservation links, and ticket status verification tools.
Policy: Do NOT directly book on own; tell user to select booking platform and provide links.
"""

import re
import uuid
import datetime
import urllib.parse
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

# Read/Write Separated Database Engine (Master SQLite + Read Replica Pool)
from agent.storage.booking_db import (
    BOOKING_DATABASE,
    booking_db_manager,
    PrimaryWriteDatabase,
    ReadReplicaDatabase,
)
from agent.skills.context import current_user_id

# Catalog of authorized and popular booking platforms by category
PLATFORMS_CATALOG: Dict[str, List[Dict[str, str]]] = {
    "flight": [
        {
            "name": "Google Flights",
            "url": "https://www.google.com/travel/flights",
            "description": "Real-time airline price tracking, calendar matrix & lowest fares",
        },
        {
            "name": "Skyscanner",
            "url": "https://www.skyscanner.com/transport/flights",
            "description": "Global multi-airline comparison & budget carrier deals",
        },
        {
            "name": "MakeMyTrip Flights",
            "url": "https://www.makemytrip.com/flights/",
            "description": "Popular flight booking with instant discounts, coupons & cashback",
        },
        {
            "name": "Kayak",
            "url": "https://www.kayak.com/flights",
            "description": "Price prediction, flexible date search & multi-provider fare alerts",
        },
        {
            "name": "Expedia",
            "url": "https://www.expedia.com/Flights",
            "description": "Worldwide flight reservations, member rewards & bundle savings",
        },
    ],
    "train": [
        {
            "name": "IRCTC (Indian Railways)",
            "url": "https://www.irctc.co.in/nget/train-search",
            "description": "Official ticket booking for Indian Railways with live berth availability",
        },
        {
            "name": "Trainline (Europe & UK)",
            "url": "https://www.thetrainline.com/",
            "description": "Leading rail & coach booking across UK, France, Germany & Europe",
        },
        {
            "name": "Amtrak (USA)",
            "url": "https://www.amtrak.com/",
            "description": "Official nationwide passenger rail service in North America",
        },
        {
            "name": "Rail Europe",
            "url": "https://www.raileurope.com/",
            "description": "Cross-border high-speed European trains (Eurostar, TGV, Frecciarossa)",
        },
        {
            "name": "ConfirmTkt",
            "url": "https://www.confirmtkt.com/",
            "description": "Train seat availability with confirmation probability prediction",
        },
    ],
    "bus": [
        {
            "name": "RedBus",
            "url": "https://www.redbus.in/",
            "description": "World's largest online bus ticketing platform with live GPS tracking",
        },
        {
            "name": "FlixBus",
            "url": "https://www.flixbus.com/",
            "description": "Budget intercity coach travel across Europe & the Americas",
        },
        {
            "name": "Busbud",
            "url": "https://www.busbud.com/",
            "description": "Worldwide bus ticket booking with multi-currency checkout",
        },
        {
            "name": "AbhiBus",
            "url": "https://www.abhibus.com/",
            "description": "State and private bus booking with seat selection",
        },
        {
            "name": "Greyhound",
            "url": "https://www.greyhound.com/",
            "description": "Extensive intercity bus network across North America",
        },
    ],
    "movie": [
        {
            "name": "BookMyShow",
            "url": "https://in.bookmyshow.com/",
            "description": "Cinema showtimes, trailer reviews, and seat selection",
        },
        {
            "name": "Fandango",
            "url": "https://www.fandango.com/",
            "description": "Movie theater tickets, VIP screenings & showtimes across the US",
        },
        {
            "name": "AMC Theatres",
            "url": "https://www.amctheatres.com/",
            "description": "Official AMC reservation for IMAX, Dolby Cinema & standard screenings",
        },
        {
            "name": "PVR INOX",
            "url": "https://www.pvrcinemas.com/",
            "description": "India's largest multiplex chain ticketing and food combos",
        },
    ],
    "event": [
        {
            "name": "Ticketmaster",
            "url": "https://www.ticketmaster.com/",
            "description": "Official tickets for live music, sports, festivals & theatre",
        },
        {
            "name": "BookMyShow Events",
            "url": "https://in.bookmyshow.com/explore/events",
            "description": "Concerts, standup comedy, nightlife & sporting events",
        },
        {
            "name": "Eventbrite",
            "url": "https://www.eventbrite.com/",
            "description": "Community events, tech conferences, networking & workshops",
        },
        {
            "name": "StubHub",
            "url": "https://www.stubhub.com/",
            "description": "Fan-protected ticket resale for sold-out events and concerts",
        },
        {
            "name": "SeatGeek",
            "url": "https://seatgeek.com/",
            "description": "Interactive stadium seat maps and Deal Score ticket ratings",
        },
    ],
    "hotel": [
        {
            "name": "Booking.com",
            "url": "https://www.booking.com/",
            "description": "Worldwide hotels, resorts, and apartments with free cancellation",
        },
        {
            "name": "Agoda",
            "url": "https://www.agoda.com/",
            "description": "Discounted hotel rates across Asia-Pacific and global destinations",
        },
        {
            "name": "Airbnb",
            "url": "https://www.airbnb.com/",
            "description": "Vacation rentals, cabins, beachfront villas & unique stays",
        },
        {
            "name": "Expedia Hotels",
            "url": "https://www.expedia.com/Hotels",
            "description": "Comprehensive hotel comparisons and member discounts",
        },
    ],
}


def format_platforms_message(
    category: str,
    origin: str = "",
    destination: str = "",
    date: str = ""
) -> str:
    """Formats recommended booking platforms with clickable links and selection instructions."""
    cat_key = category.lower().strip()
    if any(k in cat_key for k in ["flight", "air", "plane"]):
        cat_key = "flight"
    elif any(k in cat_key for k in ["train", "rail", "railway"]):
        cat_key = "train"
    elif any(k in cat_key for k in ["bus", "coach"]):
        cat_key = "bus"
    elif any(k in cat_key for k in ["movie", "cinema", "film"]):
        cat_key = "movie"
    elif any(k in cat_key for k in ["event", "concert", "show", "festival"]):
        cat_key = "event"
    elif any(k in cat_key for k in ["hotel", "stay", "resort"]):
        cat_key = "hotel"
    else:
        cat_key = "flight"

    platforms = PLATFORMS_CATALOG.get(cat_key, PLATFORMS_CATALOG["flight"])
    cat_title = cat_key.capitalize()

    route_info = ""
    if origin and destination:
        route_info = f" for **{origin} -> {destination}**"
    elif destination:
        route_info = f" for **{destination}**"
    if date:
        route_info += f" on **{date}**"

    lines = [
        f"Available Booking Platforms for {cat_title}{route_info}:",
        "Please select your preferred booking platform and click the link to check fares or complete your reservation:\n",
    ]

    for idx, p in enumerate(platforms, 1):
        target_url = p["url"]
        if cat_key == "flight" and origin and destination and p["name"] == "Google Flights":
            q = f"flights from {origin} to {destination}"
            if date:
                q += f" on {date}"
            target_url = f"https://www.google.com/travel/flights?q={urllib.parse.quote_plus(q)}"

        lines.append(f"{idx}. [{p['name']}]({target_url}) - {p['description']}")

    lines.append(
        "\n> **Action Required**: Please select one of the booking platforms above and let me know your choice, or click the direct link to book!"
    )
    return "\n".join(lines)


@tool
@traceable(name="get_booking_platforms", run_type="tool")
def get_booking_platforms(
    category: str,
    origin: str = "",
    destination: str = "",
    date: str = "",
) -> str:
    """
    Retrieve recommended booking platforms and direct reservation links for travel, movies, or events.
    Always provide these options to the user so THEY can select which platform to book on.
    DO NOT directly book anything on your own.

    Args:
        category: Type of booking ('flight', 'train', 'bus', 'movie', 'event', 'hotel').
        origin: Optional departure city or venue.
        destination: Optional destination city, event, or movie title.
        date: Optional travel or event date (e.g. 'YYYY-MM-DD').
    """
    return format_platforms_message(category, origin, destination, date)


def detect_pnr_info(raw_pnr: str) -> Dict[str, Any]:
    """
    Analyzes a booking reference or PNR string to identify its type,
    format validity, carrier system, and official live verification portals.
    """
    clean_pnr = raw_pnr.strip().upper()
    digits_only = re.sub(r"\D", "", clean_pnr)

    # 1. Indian Railways (IRCTC / CRIS) 10-digit PNR
    if len(digits_only) == 10 and (len(clean_pnr) == 10 or (len(clean_pnr) == 11 and "-" in clean_pnr)):
        return {
            "type": "train_irctc",
            "name": "Indian Railways (IRCTC / CRIS) PNR",
            "pnr": digits_only,
            "is_official_carrier_pnr": True,
            "portals": [
                {
                    "name": "ConfirmTkt Live PNR Status",
                    "url": f"https://www.confirmtkt.com/pnr-status/{digits_only}",
                    "desc": "Real-time berth/coach confirmation status & prediction",
                },
                {
                    "name": "Official IRCTC PNR Enquiry",
                    "url": "https://www.irctc.co.in/nget/enquiry/pnr-enquiry",
                    "desc": "Official Indian Railways central reservation portal",
                },
                {
                    "name": "RailYatri PNR Tracker",
                    "url": f"https://www.railyatri.in/pnr-status/{digits_only}",
                    "desc": "Live coach positioning and chart preparation updates",
                },
            ],
            "guidance": (
                "Indian Railways PNRs are 10-digit numbers issued by CRIS/IRCTC upon completed ticket booking. "
                "Because passenger charts and berth allotments are maintained on secure IRCTC servers, "
                "you can check the live confirmation and coach status via the official portal links above."
            ),
        }

    # 2. Standard IATA Airline PNR / GDS Record Locator (6 alphanumeric characters, e.g. W4KZ9P, AB12CD)
    if re.match(r"^[A-Z0-9]{6}$", clean_pnr) and not clean_pnr.startswith(("FL-", "TR-", "BS-", "AGT-")):
        return {
            "type": "airline_iata",
            "name": "Airline IATA GDS Record Locator / PNR",
            "pnr": clean_pnr,
            "is_official_carrier_pnr": True,
            "portals": [
                {
                    "name": "CheckMyTrip (Amadeus)",
                    "url": "https://www.checkmytrip.com/",
                    "desc": "Global itinerary lookup for Amadeus & partner GDS airline bookings",
                },
                {
                    "name": "Google Flights / Airline Portal",
                    "url": "https://www.google.com/travel/flights",
                    "desc": "Access your airline's 'Manage Booking' page with this PNR and passenger last name",
                },
            ],
            "guidance": (
                "Airline PNRs are 6-character alphanumeric record locators issued by global reservation systems "
                "(Amadeus, Sabre, Travelport) or directly by airlines upon payment. "
                "To manage seats, baggage, or check in, visit your airline's official 'Manage Booking' page "
                "and enter this 6-character PNR along with the passenger's last name."
            ),
        }

    # 3. Agent Internal Itinerary Reference (e.g., AGT-FL-XXXX, FL-XXXX, etc.)
    if re.match(r"^(AGT-|FL-|TR-|BS-|MV-|EV-|BK-)", clean_pnr):
        return {
            "type": "agent_internal",
            "name": "Agent Internal Itinerary Draft Reference",
            "pnr": clean_pnr,
            "is_official_carrier_pnr": False,
            "portals": [],
            "guidance": (
                f"Reference '{clean_pnr}' is an INTERNAL draft ID generated within this agent session. "
                "It is NOT an airline GDS or railway reservation number, which is why commercial carrier websites "
                "do not recognize it. Official carrier PNRs are issued directly by the booking platform "
                "(Google Flights, IRCTC, MakeMyTrip, etc.) upon completing checkout."
            ),
        }

    # 4. General / Custom Reference
    return {
        "type": "custom",
        "name": "Custom Booking Reference",
        "pnr": clean_pnr,
        "is_official_carrier_pnr": False,
        "portals": [],
        "guidance": (
            f"Reference '{clean_pnr}' does not match standard 10-digit Indian Railways PNR or 6-character Airline PNR formats. "
            "Please check the booking confirmation email or SMS received from your travel provider."
        ),
    }


@tool
@traceable(name="book_ticket", run_type="tool")
def book_ticket(
    category: str,
    origin: str,
    destination: str,
    date: str,
    passengers: int,
    passenger_names: List[str],
    platform: str = "",
    official_pnr: str = "",
    ticket_class: str = "Economy",
    config: RunnableConfig = None,
) -> str:
    """
    Finalize or register a ticket reservation ONLY AFTER the user has chosen their booking platform.
    Can also register an existing official carrier PNR (e.g. 10-digit IRCTC or 6-char flight PNR)
    that the user received after booking on the website.

    IMPORTANT: Do NOT invoke this tool directly on your own when a user initially asks to book!
    You must first ask the user to select their booking platform and provide them the links.
    Only call this tool when the user has explicitly selected a platform (e.g. 'Google Flights', 'MakeMyTrip', 'Skyscanner', 'IRCTC', 'Trainline', 'BookMyShow').

    Args:
        category: Mode of transport or event ('flight', 'train', 'bus', 'movie', 'event').
        origin: Departure location, city, or venue.
        destination: Arrival destination or movie title.
        date: Travel or event date (e.g. 'YYYY-MM-DD').
        passengers: Number of tickets to book.
        passenger_names: List of passenger/attendee full names.
        platform: The booking platform selected by the user (e.g., 'Google Flights', 'MakeMyTrip', 'Skyscanner', 'IRCTC', 'Trainline', 'BookMyShow'). REQUIRED.
        official_pnr: Optional real carrier PNR (e.g. 10-digit IRCTC PNR or 6-character flight PNR) received from the platform website.
        ticket_class: Class tier (e.g., 'Economy', 'Premium', 'Business', 'First'). Default is 'Economy'.
    """
    # Enforce policy: Never directly book on own without user selecting platform
    if not platform or not platform.strip() or platform.strip().lower() in ["none", "unknown", "unspecified", "any", "n/a"]:
        platforms_info = format_platforms_message(category, origin, destination, date)
        return (
            "Booking blocked: You cannot directly book on your own!\n"
            "Please ask the user to choose their preferred booking platform and provide them the platform links first:\n\n"
            f"{platforms_info}"
        )

    if passengers <= 0:
        return "Booking failed: Number of passengers must be at least 1."

    if len(passenger_names) < passengers:
        return (
            f"Booking failed: Please provide all {passengers} passenger names "
            f"(only {len(passenger_names)} provided)."
        )

    prefix_map = {
        "flight": "FL",
        "train": "TR",
        "bus": "BS",
        "movie": "MV",
        "event": "EV",
    }
    prefix = prefix_map.get(category.lower(), "BK")
    internal_ref = f"AGT-{prefix}-{uuid.uuid4().hex[:6].upper()}"

    clean_official_pnr = official_pnr.strip().upper() if official_pnr else ""
    # The internal reference is always the primary key; the carrier PNR is indexed for lookups.
    # (Keying by PNR let a second registration of the same PNR overwrite another user's booking.)
    primary_id = internal_ref

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
        "booking_id": primary_id,
        "internal_ref": internal_ref,
        "official_pnr": clean_official_pnr or None,
        "platform": platform.strip(),
        "category": category.capitalize(),
        "origin": origin,
        "destination": destination,
        "date": date,
        "passengers": passengers,
        "passenger_names": passenger_names,
        "ticket_class": ticket_class.capitalize(),
        "total_cost_usd": f"${total_cost:.2f}",
        "status": "CONFIRMED" if clean_official_pnr else "ITINERARY_SAVED",
        "user_id": current_user_id(config),
        "booked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # WRITE OPERATION: Persist to Primary Master DB & replicate to Read Replicas
    booking_db_manager.save_booking(booking_record)

    # Formulate clear response
    if clean_official_pnr:
        pnr_info = detect_pnr_info(clean_official_pnr)
        portal_lines = [f"- [{p['name']}]({p['url']}) - {p['desc']}" for p in pnr_info.get("portals", [])]
        portal_text = ("\nOfficial Live Verification Portals:\n" + "\n".join(portal_lines)) if portal_lines else ""

        return (
            f"Official Ticket Reservation Registered!\n"
            f"----------------------------------------\n"
            f"Official Carrier PNR: {clean_official_pnr} ({pnr_info['name']})\n"
            f"Internal Session Ref: {internal_ref}\n"
            f"Platform: {platform.strip()}\n"
            f"Category: {booking_record['category']}\n"
            f"Route / Event: {origin} -> {destination}\n"
            f"Date: {date}\n"
            f"Class: {ticket_class.capitalize()}\n"
            f"Passengers ({passengers}): {', '.join(passenger_names)}\n"
            f"Total Cost: ${total_cost:.2f}\n"
            f"Status: CONFIRMED\n"
            f"----------------------------------------{portal_text}"
        )
    else:
        return (
            f"Ticket Itinerary Draft Saved!\n"
            f"----------------------------------------\n"
            f"Booking ID: {internal_ref} (Internal Agent Reference)\n"
            f"Platform: {platform.strip()}\n"
            f"Category: {booking_record['category']}\n"
            f"Route / Event: {origin} -> {destination}\n"
            f"Date: {date}\n"
            f"Class: {ticket_class.capitalize()}\n"
            f"Passengers ({passengers}): {', '.join(passenger_names)}\n"
            f"Estimated Fare: ${total_cost:.2f}\n"
            f"Status: ITINERARY_SAVED\n"
            f"----------------------------------------\n"
            f"PNR Notice:\n"
            f"- '{internal_ref}' is an internal agent reference.\n"
            f"- Your official carrier PNR is issued directly by {platform.strip()} upon completing checkout on their website.\n"
            f"- Once you complete booking on {platform.strip()} and receive your official PNR (e.g. 10-digit train PNR or 6-character flight PNR), share it with me to attach it to your itinerary for live tracking!"
        )


@tool
@traceable(name="check_ticket_status", run_type="tool")
def check_ticket_status(booking_id: str, config: RunnableConfig = None) -> str:
    """
    Check the status and details of an existing ticket reservation by its booking ID or real carrier PNR.
    Supports both internal agent reservations and official carrier PNRs (e.g. 10-digit IRCTC, 6-character Airline PNR).

    Args:
        booking_id: The reservation reference or carrier PNR (e.g. 'AGT-FL-A1B2C3', '4521369874', 'W4KZ9P').
    """
    clean_id = booking_id.strip().upper()
    # READ OPERATION: Route query to load-balanced Read Replica Pool
    booking = booking_db_manager.get_booking(clean_id, user_id=current_user_id(config))
    pnr_info = detect_pnr_info(clean_id)

    # Case 1: Booking found in local agent database
    if booking:
        official_pnr_str = booking.get("official_pnr")
        pnr_display = f"{clean_id} (Internal Agent Ref)"
        if official_pnr_str:
            pnr_display = f"{official_pnr_str} [Official PNR] (Internal ID: {booking.get('internal_ref', clean_id)})"

        portal_lines = []
        if official_pnr_str:
            off_info = detect_pnr_info(official_pnr_str)
            if off_info.get("portals"):
                portal_lines.append("\nLive Carrier Verification Portals:")
                for p in off_info["portals"]:
                    portal_lines.append(f"- [{p['name']}]({p['url']}) - {p['desc']}")

        return (
            f"Booking Record for {clean_id}:\n"
            f"----------------------------------------\n"
            f"- Reference / PNR: {pnr_display}\n"
            f"- Platform: {booking.get('platform', 'Direct / Partner')}\n"
            f"- Category: {booking['category']}\n"
            f"- Route/Event: {booking['origin']} to {booking['destination']}\n"
            f"- Date: {booking['date']}\n"
            f"- Class: {booking['ticket_class']}\n"
            f"- Passengers: {', '.join(booking['passenger_names'])}\n"
            f"- Status: {booking['status']}\n"
            f"- Booked At: {booking['booked_at']}\n"
            f"----------------------------------------\n"
            f"Note: {pnr_info['guidance']}"
            + ("\n" + "\n".join(portal_lines) if portal_lines else "")
        )

    # Case 2: Not in local database, but matches an official real carrier PNR format (e.g. IRCTC 10-digit or Airline 6-character)
    if pnr_info.get("is_official_carrier_pnr"):
        portal_lines = []
        for p in pnr_info["portals"]:
            portal_lines.append(f"- [{p['name']}]({p['url']}) - {p['desc']}")

        return (
            f"Official Carrier PNR Detected: {pnr_info['pnr']}\n"
            f"Format Identified: {pnr_info['name']}\n"
            f"----------------------------------------\n"
            f"{pnr_info['guidance']}\n\n"
            f"Official Live PNR Verification Portals:\n"
            + "\n".join(portal_lines) + "\n\n"
            f"> Tip: To save this booking into your agent itinerary for email notifications and local tracking, "
            f"you can ask me to 'Register booking for PNR {pnr_info['pnr']}' with your travel route and date."
        )

    # Case 3: Neither in database nor recognized official PNR
    return (
        f"No booking found in local session for reference '{clean_id}'.\n\n"
        f"Why this might happen:\n"
        f"1. {pnr_info['guidance']}\n"
        f"2. Indian Railways (IRCTC) PNRs are exactly 10 digits (e.g. 4521369874).\n"
        f"3. Airline PNRs / Record Locators are 6 alphanumeric characters (e.g. W4KZ9P).\n"
        f"4. If you completed booking on an external platform website, please check your confirmation email/SMS for your official carrier PNR."
    )


@tool
@traceable(name="get_database_status", run_type="tool")
def get_database_status() -> str:
    """
    Check the operational health and metrics of the Read/Write Separated Database system.
    Shows the status of the Primary Master Write DB and the Read Replica Pool,
    including replication lag, query counts, and read/write ratio.
    """
    metrics = booking_db_manager.get_metrics()
    primary = metrics["primary_master"]
    replicas = metrics["read_replicas_pool"]
    perf = metrics["performance"]

    rep_lines = [
        f"  - {r['replica_name']}: Status={r['status']} | Reads={r['total_read_queries']} | Lag={r['replication_lag_records']} records | Latency={r['avg_latency_ms']}ms"
        for r in replicas["replicas"]
    ]

    return (
        f"MantaBooking Read/Write Separated Database Engine:\n"
        f"--------------------------------------------------\n"
        f"Architecture: {metrics['architecture']}\n"
        f"System Status: {metrics['status']}\n\n"
        f"Primary Master DB (WRITES):\n"
        f"  - Mode: {primary['mode']}\n"
        f"  - Engine: {primary['type']}\n"
        f"  - Total Writes: {primary['total_writes']}\n"
        f"  - Current LSN: {primary['current_lsn']}\n"
        f"  - Last Write: {primary['last_write_at'] or 'None'}\n\n"
        f"Read Replicas Pool (READS):\n"
        f"  - Active Replicas: {replicas['count']}\n"
        f"  - Load Balancing: {replicas['load_balancing']}\n"
        f"  - Total Reads Served: {replicas['total_reads_served']}\n"
        f"  - Read/Write Ratio: {replicas['read_write_ratio']}\n"
        + "\n".join(rep_lines) + "\n\n"
        f"Performance & Concurrency:\n"
        f"  - Average Query Latency: {perf['avg_query_latency_ms']} ms\n"
        f"  - Concurrency Model: {perf['thread_safety']}\n"
        f"--------------------------------------------------"
    )

