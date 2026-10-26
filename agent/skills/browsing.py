"""
Browsing Skill Module.
Provides web search, URL content extraction, and travel/PNR portal resolution.
"""

import re
import socket
import ipaddress
import urllib.parse
from typing import Optional
import requests
from langchain_core.tools import tool
from langsmith import traceable

MAX_REDIRECTS = 3


def _is_public_http_url(url: str) -> bool:
    """
    Only allow http(s) URLs whose host resolves exclusively to public IP addresses.
    Prevents the agent from being steered into fetching internal services
    (localhost, cloud metadata endpoints, private networks).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(info[4][0].split("%")[0]).is_global for info in infos)


def _fetch_public_url(url: str) -> requests.Response:
    """GET a URL, following redirects manually so every hop is checked by _is_public_http_url."""
    for _ in range(MAX_REDIRECTS + 1):
        if not _is_public_http_url(url):
            raise ValueError("only public http(s) addresses can be fetched")
        resp = requests.get(
            url, timeout=10, allow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        if resp.is_redirect and resp.headers.get("Location"):
            url = urllib.parse.urljoin(url, resp.headers["Location"])
            continue
        return resp
    raise ValueError("too many redirects")


@tool
@traceable(name="browse_web", run_type="tool")
def browse_web(query: str, url: Optional[str] = None) -> str:
    """
    Search the internet for real-time information, travel schedules, or fetch content from a URL.
    Can also resolve official PNR and flight/train status enquiry portals.

    Args:
        query: The search keywords, PNR number, or question.
        url: Optional specific website URL to retrieve information from.
    """
    # 1. Direct URL Content Fetching
    if url:
        try:
            resp = _fetch_public_url(url)
            if resp.status_code == 200:
                # Strip out script and style tags roughly
                cleaned_text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", resp.text, flags=re.DOTALL | re.IGNORECASE)
                cleaned_text = re.sub(r"<[^>]+>", " ", cleaned_text)
                cleaned_text = " ".join(cleaned_text.split())[:1500]
                return f"[Source: {url}] Extracted content:\n{cleaned_text}"
            return f"Failed to fetch {url}. Status code: {resp.status_code}"
        except Exception as e:
            return f"Error accessing {url}: {str(e)}"

    clean_query = query.strip()
    query_upper = clean_query.upper()

    # 2. Check for PNR and Ticket Status Inquiry in Query
    pnr_match_10 = re.search(r"\b(\d{10})\b", clean_query) or re.search(r"\b(\d{3}-\d{7})\b", clean_query)

    common_words = {"FLIGHT", "TICKET", "STATUS", "SEARCH", "TRAVEL", "RECORD", "ONLINE", "AIRWAY", "BOOKED", "NUMBER", "UPDATE", "PLEASE", "VERIFY"}
    pnr_kw_match = re.search(r"\b(?:PNR|LOCATOR|REF|REFERENCE|TICKET)\s*[:#-]?\s*([A-Z0-9]{6})\b", query_upper)
    code_6 = None
    if pnr_kw_match and pnr_kw_match.group(1) not in common_words:
        code_6 = pnr_kw_match.group(1)
    else:
        for cand in re.findall(r"\b([A-Z0-9]{6})\b", query_upper):
            if cand not in common_words and not any(cand.startswith(k) for k in ["FL-", "TR-", "BS-", "AGT-"]):
                code_6 = cand
                break

    if "PNR" in query_upper or "TICKET STATUS" in query_upper or pnr_match_10 or code_6:
        if pnr_match_10:
            digits_10 = re.sub(r"\D", "", pnr_match_10.group(1))
            return (
                f"Indian Railways 10-Digit PNR Detected: **{digits_10}**\n"
                f"----------------------------------------\n"
                f"Because passenger reservation records (coach, berth, chart status) are private and maintained "
                f"exclusively on secure CRIS/IRCTC railway servers, live PNR status must be accessed through "
                f"official certified reservation enquiry portals.\n\n"
                f"Official Live PNR Status Portals:\n"
                f"1. [ConfirmTkt Live PNR Status](https://www.confirmtkt.com/pnr-status/{digits_10}) - Real-time seat confirmation & chart preparation\n"
                f"2. [Official IRCTC PNR Enquiry](https://www.irctc.co.in/nget/enquiry/pnr-enquiry) - Official Indian Railways central portal\n"
                f"3. [RailYatri Live PNR Tracker](https://www.railyatri.in/pnr-status/{digits_10}) - Coach positioning and delay updates"
            )

        if code_6:
            return (
                f"Airline 6-Character PNR / Record Locator Detected: **{code_6}**\n"
                f"----------------------------------------\n"
                f"Airline passenger manifests are confidential and hosted on airline GDS servers (Amadeus/Sabre). "
                f"To check your live flight reservation, seat assignments, and baggage allowance:\n\n"
                f"1. [CheckMyTrip Global Itinerary](https://www.checkmytrip.com/) - Multi-airline GDS booking lookup\n"
                f"2. [Google Flights](https://www.google.com/travel/flights) - Airline search & flight tracker\n"
                f"3. Visit your operating airline's website (e.g. IndiGo, Air India, Emirates, Delta) -> Click **'Manage Booking'** -> Enter PNR **{code_6}** and passenger last name."
            )

    # 3. Search query fallback via DuckDuckGo Instant Answer API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={requests.utils.quote(clean_query)}&format=json&no_html=1"
        resp = requests.get(ddg_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("AbstractText", "")
            related_topics = [
                topic.get("Text", "")
                for topic in data.get("RelatedTopics", [])
                if isinstance(topic, dict) and topic.get("Text")
            ]
            if abstract:
                return f"Search result for '{clean_query}':\n{abstract}"
            elif related_topics:
                results = "\n- ".join(related_topics[:4])
                return f"Search results for '{clean_query}':\n- {results}"
    except Exception:
        pass

    encoded_q = urllib.parse.quote_plus(clean_query)
    return (
        f"Web search summary for '{clean_query}':\n"
        f"Real-time information and live listings can be viewed directly via:\n"
        f"- [Google Travel & Search](https://www.google.com/search?q={encoded_q})\n"
        f"- [DuckDuckGo Web Search](https://duckduckgo.com/?q={encoded_q})"
    )

