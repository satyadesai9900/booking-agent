"""
Gmail Skill Module.
Enables the LangGraph Agent to send booking confirmation emails and notifications
directly to users via Gmail SMTP using TLS/SSL.
"""

import os
import re
import ssl
from html import escape as html_escape
import smtplib
from typing import Optional, Dict, Any
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from env.config import config
from agent.skills.booking import BOOKING_DATABASE, booking_db_manager
from agent.skills.context import current_user_id, current_user_email


def _recipient_not_allowed(recipient_email: str, run_config: Optional[RunnableConfig]) -> Optional[str]:
    """
    Emails may only go to the signed-in user's own address. This keeps the server's Gmail account
    from being used to send mail to arbitrary people (by a user, or by instructions planted in a
    web page the agent reads). Returns an error message, or None if sending is allowed.
    Local CLI runs (no web session) are not restricted.
    """
    own_email = current_user_email(run_config)
    if own_email is None:
        return None
    if recipient_email.strip().lower() != own_email:
        return (
            f"Email Delivery Blocked: emails can only be sent to your own account address ({own_email}). "
            f"Ask the user to forward the confirmation themselves if it should reach someone else."
        )
    return None


def _is_valid_email(email_str: str) -> bool:
    """Validates basic email address structure."""
    if not email_str or not isinstance(email_str, str):
        return False
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(email_pattern, email_str.strip()))


def generate_booking_html(booking: Dict[str, Any], notes: Optional[str] = None) -> str:
    """
    Renders a responsive, modern HTML booking confirmation email
    styled for Gmail and universal mobile/desktop email clients.
    """
    # Booking fields and notes come from user/model input: escape before embedding in HTML
    booking = {
        key: ([html_escape(str(v)) for v in value] if isinstance(value, list) else html_escape(str(value)))
        for key, value in booking.items()
        if value is not None
    }
    notes = html_escape(notes) if notes else notes

    booking_id = booking.get("booking_id", "N/A")
    category = booking.get("category", "Booking").upper()
    origin = booking.get("origin", "N/A")
    destination = booking.get("destination", "N/A")
    travel_date = booking.get("date", "N/A")
    ticket_class = booking.get("ticket_class", "Standard")
    passengers_count = booking.get("passengers", 1)
    passenger_names = booking.get("passenger_names", [])
    total_cost = booking.get("total_cost_usd", "N/A")
    status = booking.get("status", "CONFIRMED")
    platform = booking.get("platform", "Selected Platform")
    booked_at = booking.get("booked_at", "N/A")

    passenger_rows = "".join(
        f"<li style='padding:4px 0; color:#334155; font-size:14px; font-weight:500;'>👤 {name}</li>"
        for name in passenger_names
    )

    notes_section = ""
    if notes:
        notes_section = f"""
        <div style="margin-top:20px; padding:14px 18px; background-color:#eff6ff; border-left:4px solid #3b82f6; border-radius:6px;">
            <p style="margin:0; font-size:13px; font-weight:600; color:#1e40af; text-transform:uppercase; letter-spacing:0.5px;">Special Notes</p>
            <p style="margin:6px 0 0 0; font-size:14px; color:#1e3a8a; line-height:1.5;">{notes}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Booking Confirmation - {booking_id}</title>
</head>
<body style="margin:0; padding:0; background-color:#f1f5f9; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#f1f5f9; padding:30px 10px;">
        <tr>
            <td align="center">
                <table width="600" border="0" cellspacing="0" cellpadding="0" style="max-width:600px; width:100%; background-color:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding:32px 30px; text-align:center; color:#ffffff;">
                            <div style="display:inline-block; padding:6px 14px; background:rgba(255,255,255,0.2); border-radius:30px; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;">
                                {category} RESERVATION
                            </div>
                            <h1 style="margin:0; font-size:26px; font-weight:700; letter-spacing:-0.5px; line-height:1.2;">
                                Booking Confirmed!
                            </h1>
                            <p style="margin:8px 0 0 0; font-size:14px; color:#e0e7ff;">
                                Your travel ticket has been successfully booked and verified.
                            </p>
                        </td>
                    </tr>

                    <!-- Booking Reference Card -->
                    <tr>
                        <td style="padding:24px 30px 10px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:18px;">
                                <tr>
                                    <td>
                                        <div style="font-size:11px; text-transform:uppercase; color:#64748b; font-weight:600; letter-spacing:0.5px;">Booking Reference (PNR)</div>
                                        <div style="font-size:22px; font-weight:800; color:#1e293b; font-family:monospace; margin-top:4px;">{booking_id}</div>
                                    </td>
                                    <td align="right">
                                        <span style="display:inline-block; padding:6px 14px; background-color:#dcfce7; color:#15803d; border:1px solid #86efac; border-radius:20px; font-size:12px; font-weight:700; text-transform:uppercase;">
                                            ● {status}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Itinerary / Trip Card -->
                    <tr>
                        <td style="padding:10px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background:linear-gradient(to right, #fcfaff, #f8fafc); border:1px solid #e0e7ff; border-radius:12px; padding:20px;">
                                <tr>
                                    <td width="42%" style="text-align:left;">
                                        <div style="font-size:11px; text-transform:uppercase; color:#6366f1; font-weight:700;">Departure</div>
                                        <div style="font-size:18px; font-weight:700; color:#0f172a; margin-top:4px;">{origin}</div>
                                    </td>
                                    <td width="16%" style="text-align:center;">
                                        <div style="font-size:20px; color:#6366f1; font-weight:bold;">➔</div>
                                    </td>
                                    <td width="42%" style="text-align:right;">
                                        <div style="font-size:11px; text-transform:uppercase; color:#6366f1; font-weight:700;">Destination / Event</div>
                                        <div style="font-size:18px; font-weight:700; color:#0f172a; margin-top:4px;">{destination}</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Details Table -->
                    <tr>
                        <td style="padding:15px 30px;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                                <tr>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#64748b; font-size:13px;">Booking Platform:</td>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#4f46e5; font-weight:700; font-size:14px; text-align:right;">🌐 {platform}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#64748b; font-size:13px;">Date:</td>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#0f172a; font-weight:600; font-size:14px; text-align:right;">📅 {travel_date}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#64748b; font-size:13px;">Class / Tier:</td>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#0f172a; font-weight:600; font-size:14px; text-align:right;">⭐ {ticket_class}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#64748b; font-size:13px;">Total Passengers:</td>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#0f172a; font-weight:600; font-size:14px; text-align:right;">👥 {passengers_count} passenger(s)</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#64748b; font-size:13px;">Total Amount:</td>
                                    <td style="padding:10px 0; border-bottom:1px solid #f1f5f9; color:#059669; font-weight:800; font-size:18px; text-align:right;">{total_cost}</td>
                                </tr>
                                <tr>
                                    <td style="padding:10px 0; color:#64748b; font-size:13px;">Booked Timestamp:</td>
                                    <td style="padding:10px 0; color:#475569; font-size:13px; text-align:right;">{booked_at}</td>
                                </tr>
                            </table>

                            <!-- Passenger Names -->
                            <div style="margin-top:16px; padding:12px 16px; background-color:#f8fafc; border-radius:8px; border:1px solid #e2e8f0;">
                                <div style="font-size:12px; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Passenger List</div>
                                <ul style="margin:0; padding-left:18px;">
                                    {passenger_rows}
                                </ul>
                            </div>

                            {notes_section}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding:24px 30px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
                            <p style="margin:0; font-size:12px; color:#94a3b8; line-height:1.5;">
                                This confirmation email was dispatched by <strong>MantaBooking AI Assistant</strong>.
                                <br>
                                Please present this confirmation with your valid government photo ID upon arrival.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    return html


def generate_booking_plaintext(booking: Dict[str, Any], notes: Optional[str] = None) -> str:
    """Generates clean plain-text version of the booking confirmation."""
    booking_id = booking.get("booking_id", "N/A")
    category = booking.get("category", "Booking").upper()
    origin = booking.get("origin", "N/A")
    destination = booking.get("destination", "N/A")
    travel_date = booking.get("date", "N/A")
    ticket_class = booking.get("ticket_class", "Standard")
    passengers = booking.get("passengers", 1)
    passenger_names = ", ".join(booking.get("passenger_names", []))
    total_cost = booking.get("total_cost_usd", "N/A")
    status = booking.get("status", "CONFIRMED")
    booked_at = booking.get("booked_at", "N/A")

    lines = [
        f"===========================================================",
        f"         {category} BOOKING CONFIRMATION",
        f"===========================================================",
        f"Booking ID (PNR): {booking_id}",
        f"Status:           {status}",
        f"Category:         {category}",
        f"Route:            {origin} -> {destination}",
        f"Date:             {travel_date}",
        f"Class:            {ticket_class}",
        f"Passengers ({passengers}):  {passenger_names}",
        f"Total Cost:       {total_cost}",
        f"Booked At:        {booked_at}",
        f"===========================================================",
    ]

    if notes:
        lines.append(f"Notes: {notes}")
        lines.append(f"===========================================================")

    lines.append("\nThank you for booking with LangGraph AI Travel Assistant!")
    return "\n".join(lines)


def _dispatch_gmail(
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None
) -> str:
    """
    Internal helper to authenticate with Gmail SMTP and deliver email.
    If Gmail credentials are not configured, returns a simulated dry-run report
    with instructions on how to set up Gmail App Password in env/.env.
    """
    clean_recipient = recipient_email.strip()
    if not _is_valid_email(clean_recipient):
        return f"Email Delivery Failed: '{recipient_email}' is not a valid email address."

    sender = config.gmail_sender_email or os.getenv("GMAIL_SENDER_EMAIL") or os.getenv("GMAIL_USER", "").strip()
    password = config.gmail_app_password or os.getenv("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_PASS", "").strip()
    host = config.smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = config.smtp_port or int(os.getenv("SMTP_PORT", "587"))

    # If sender or app password is not configured, deliver informative dry-run response
    if not sender or not password or password == "your_16_char_google_app_password":
        return (
            f"[Gmail Notice - Setup Required]\n"
            f"The booking confirmation email for '{clean_recipient}' was generated successfully!\n"
            f"However, Gmail credentials are not yet configured in your 'env/.env' file.\n\n"
            f"To enable real email dispatch via Gmail:\n"
            f"1. Open 'env/.env'\n"
            f"2. Add:\n"
            f"   GMAIL_SENDER_EMAIL=your_email@gmail.com\n"
            f"   GMAIL_APP_PASSWORD=your_16_character_app_password\n"
            f"   (Generate an App Password at: https://myaccount.google.com/apppasswords)\n\n"
            f"--- EMAIL PREVIEW SENT TO RECIPIENT ---\n"
            f"To: {clean_recipient}\n"
            f"Subject: {subject}\n\n"
            f"{text_body}"
        )

    # Prepare MIME Multipart Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = clean_recipient

    # Attach Plaintext
    msg.attach(MIMEText(text_body, "plain", "utf-8"))

    # Attach HTML if provided
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        if port == 465:
            # SSL Connection
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
                server.login(sender, password)
                server.send_message(msg)
        else:
            # TLS Connection (standard 587)
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(sender, password)
                server.send_message(msg)

        return (
            f"Confirmation email successfully sent via Gmail to {clean_recipient}!\n"
            f"Subject: {subject}\n"
            f"Sender: {sender}"
        )

    except smtplib.SMTPAuthenticationError as auth_err:
        return (
            f"Gmail Authentication Failed for sender '{sender}'.\n"
            f"Reason: Invalid credentials or App Password required.\n"
            f"To fix this:\n"
            f"1. Make sure 2-Step Verification is enabled on your Google Account.\n"
            f"2. Visit https://myaccount.google.com/apppasswords to create a 16-character App Password.\n"
            f"3. Put that 16-character password into 'GMAIL_APP_PASSWORD' in 'env/.env'."
        )
    except smtplib.SMTPConnectError as conn_err:
        return f"Failed to connect to Gmail SMTP server ({host}:{port}): {str(conn_err)}"
    except Exception as e:
        return f"Failed to send email to {clean_recipient} via Gmail: {str(e)}"


@tool
@traceable(name="send_booking_email", run_type="tool")
def send_booking_email(
    recipient_email: str,
    booking_id: str,
    subject: Optional[str] = None,
    additional_notes: Optional[str] = None,
    config: RunnableConfig = None,
) -> str:
    """
    Send an official booking confirmation and itinerary email to the signed-in user via Gmail.
    Only the user's own account email address is accepted as the recipient.

    Args:
        recipient_email: The signed-in user's own email address.
        booking_id: The unique booking ID (e.g., 'FL-A1B2C3D4') generated during reservation.
        subject: Optional custom email subject line. If omitted, a standard subject is generated.
        additional_notes: Optional special instructions or notes to include in the email body.
    """
    blocked = _recipient_not_allowed(recipient_email, config)
    if blocked:
        return blocked

    clean_id = booking_id.strip().upper()
    user_id = current_user_id(config)
    # READ OPERATION: Query load-balanced Read Replica Pool (only this user's bookings)
    booking = booking_db_manager.get_booking(clean_id, user_id=user_id)

    if not booking:
        # Check if booking_id was passed without prefix or case mismatch across read replica records
        matching = [
            b for b in booking_db_manager.list_bookings(user_id=user_id)
            if clean_id in (b.get("booking_id", "") + b.get("internal_ref", "") + b.get("official_pnr", "")).upper()
        ]
        if matching:
            booking = matching[0]
            clean_id = booking.get("booking_id") or booking.get("internal_ref") or clean_id

    if not booking:
        # Fallback if booking ID not in database
        subject_line = subject or f"Booking Notification: {clean_id}"
        plain_text = (
            f"Booking Reference: {clean_id}\n\n"
            f"Your reservation ({clean_id}) has been recorded.\n"
            f"Notes: {additional_notes or 'Safe travels!'}\n\n"
            f"- LangGraph AI Booking Assistant"
        )
        return _dispatch_gmail(recipient_email, subject_line, plain_text)

    # Format official email subject
    email_subject = subject or (
        f"Booking Confirmation: {booking['category']} ({booking['booking_id']}) - "
        f"{booking['origin']} to {booking['destination']}"
    )

    # Generate both HTML and plaintext representations
    html_content = generate_booking_html(booking, notes=additional_notes)
    text_content = generate_booking_plaintext(booking, notes=additional_notes)

    return _dispatch_gmail(
        recipient_email=recipient_email,
        subject=email_subject,
        text_body=text_content,
        html_body=html_content,
    )


@tool
@traceable(name="send_email", run_type="tool")
def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    config: RunnableConfig = None,
) -> str:
    """
    Send a general text or notification email to the signed-in user via Gmail.
    Only the user's own account email address is accepted as the recipient.

    Args:
        recipient_email: The signed-in user's own email address.
        subject: The subject line of the email.
        body: The plain text content or body message of the email.
    """
    blocked = _recipient_not_allowed(recipient_email, config)
    if blocked:
        return blocked
    return _dispatch_gmail(
        recipient_email=recipient_email,
        subject=subject,
        text_body=body,
    )
