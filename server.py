"""
Backend API Server for LangGraph Agent.
Exposes REST endpoints for the React frontend.
The LLM API key is securely handled on the backend and NEVER exposed to the frontend.

All state (users, sessions, bookings, chat checkpoints) lives in SQLite under DATA_DIR,
so the server can run with several gunicorn workers and survives restarts.
"""

import os
import re
import sys
import uuid
import secrets
import sqlite3
import logging
import datetime
import urllib.parse
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langsmith import traceable

from env.config import config
from agent.llm import build_chain, ACTIVE_LLM
from agent.chain import get_model_name, is_api_key_configured
from agent.graph import build_agent_graph
from agent.skills.booking import (
    PLATFORMS_CATALOG,
    detect_pnr_info,
    book_ticket,
    booking_db_manager,
)
from agent.storage.booking_db import DATA_DIR
from agent.storage.user_db import user_store, public_user

logger = logging.getLogger("mantabooking")

# "1-click demo" logins create a separate throwaway guest account per click (disable in production)
ENABLE_DEMO_LOGIN = os.getenv("ENABLE_DEMO_LOGIN", "true").strip().lower() in ("1", "true", "yes")

THREAD_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    return auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""


def get_current_user_from_request() -> Optional[Dict[str, Any]]:
    """Extracts and validates the authenticated user from the Bearer token."""
    return user_store.get_user_for_token(_bearer_token())


def _auth_response(user: Dict[str, Any]):
    token = user_store.create_session(user["id"])
    return jsonify({"success": True, "token": token, "user": public_user(user)})


def _agent_config(user: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
    """
    LangGraph run config for a user's conversation.
    The checkpoint thread is namespaced by user id, so one user can never load another's history,
    and the user's identity is passed to tools (never chosen by the model).
    """
    return {
        "configurable": {
            "thread_id": f"{user['id']}::{thread_id}",
            "user_id": user["id"],
            "user_email": user["email"],
        }
    }


# Initialize Flask app
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# The UI is served from this same origin, so cross-origin access is off unless explicitly configured
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    CORS(app, origins=_cors_origins)

# Global LangGraph agent with a SQLite checkpointer (conversation memory shared by all workers)
_checkpoint_conn = sqlite3.connect(os.path.join(DATA_DIR, "checkpoints.db"), check_same_thread=False, timeout=30.0)
_checkpoint_conn.execute("PRAGMA journal_mode = WAL;")
checkpointer = SqliteSaver(_checkpoint_conn)
chain = None
agent = None


@traceable(name="init_agent")
def init_agent():
    """Initializes LCEL Chain (model | parser) and LangGraph workflow."""
    global chain, agent
    try:
        # Build the chain containing model and parser
        chain = build_chain()
        # Compile LangGraph agent using the chain
        agent = build_agent_graph(chain, checkpointer=checkpointer)
        print(f"[Backend] LangGraph Agent initialized with chain (provider: {ACTIVE_LLM})")
    except Exception as e:
        print(f"[Backend] Warning: Error initializing agent: {e}")


# Initialize agent at server startup
init_agent()

# ==============================================================================
# AUTHENTICATION ENDPOINTS
# ==============================================================================

@app.route("/api/auth/register", methods=["POST"])
@traceable(name="auth_register")
def auth_register():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")

    if not email or not password or not name:
        return jsonify({"error": "Name, email, and password are required."}), 400
    if not re.match(r"^[\w\.+-]+@[\w\.-]+\.\w+$", email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    user = user_store.create_user(email=email, name=name, password=password)
    if user is None:
        return jsonify({"error": "An account with this email already exists. Please sign in."}), 400
    return _auth_response(user)


@app.route("/api/auth/login", methods=["POST"])
@traceable(name="auth_login")
def auth_login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = user_store.authenticate(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    return _auth_response(user)


@app.route("/api/auth/demo", methods=["POST"])
@traceable(name="auth_demo")
def auth_demo():
    if not ENABLE_DEMO_LOGIN:
        return jsonify({"error": "Demo access is disabled on this server. Please create an account."}), 403

    # Each demo click gets its own guest account, so demo visitors never see each other's data
    guest_id = uuid.uuid4().hex[:10]
    user = user_store.create_user(
        email=f"guest-{guest_id}@demo.mantabooking.local",
        name="Demo Traveler",
        password=secrets.token_urlsafe(24),
        role="guest",
    )
    return _auth_response(user)


@app.route("/api/auth/me", methods=["GET"])
@traceable(name="auth_me")
def auth_me():
    user = get_current_user_from_request()
    if user:
        return jsonify({"authenticated": True, "user": public_user(user)})
    return jsonify({
        "authenticated": False,
        "user": None
    })


@app.route("/api/auth/logout", methods=["POST"])
@traceable(name="auth_logout")
def auth_logout():
    token = _bearer_token()
    if token:
        user_store.delete_session(token)
    return jsonify({"success": True, "message": "Logged out successfully."})


# ==============================================================================
# CORE SYSTEM & CHAT ENDPOINTS
# ==============================================================================

@app.route("/api/status", methods=["GET"])
@traceable(name="get_status")
def get_status():
    """
    Health check and status endpoint.
    Verifies backend agent readiness WITHOUT leaking the API key.
    """
    gmail_ready = bool(
        (config.gmail_sender_email or os.getenv("GMAIL_SENDER_EMAIL")) and
        (config.gmail_app_password or os.getenv("GMAIL_APP_PASSWORD"))
    )

    status = {
        "status": "ready" if agent is not None else "initializing",
        "provider": ACTIVE_LLM,
        "model": get_model_name(),
        "chain": "model | parser",
        "api_key_configured": is_api_key_configured(),
        "gmail_configured": gmail_ready,
        "checkpointer": "SqliteSaver",
        "demo_login_enabled": ENABLE_DEMO_LOGIN,
        "skills": ["get_booking_platforms", "browse_web", "book_ticket", "check_ticket_status", "get_database_status", "send_booking_email", "send_email"],
        "database": {
            "architecture": "Read-Write Separation (Master-Replica CQRS)",
            "master_writes": booking_db_manager.primary_db.write_count,
            "replica_reads": sum(r["total_read_queries"] for r in booking_db_manager.replica_pool.get_stats(booking_db_manager.primary_db.get_current_lsn())),
            "replicas_count": len(booking_db_manager.replica_pool.replicas),
            "status": "HEALTHY"
        },
        "timestamp": datetime.datetime.now().isoformat()
    }

    current_user = get_current_user_from_request()
    if current_user:
        status["bookings_count"] = booking_db_manager.count(user_id=current_user["id"])
    return jsonify(status)


@app.route("/api/chat", methods=["POST"])
@traceable(name="chat_endpoint", run_type="chain")
def chat():
    """
    Main chat endpoint for React frontend.
    Accepts user message and thread_id, executes LangGraph agent workflow,
    and returns assistant reply along with any executed tool calls and outputs.
    """
    current_user = get_current_user_from_request()
    if not current_user:
        return jsonify({
            "success": False,
            "requires_auth": True,
            "error": "Authentication required. Please sign in to MantaBooking to chat with your AI Co-Pilot."
        }), 401

    global agent
    if agent is None:
        init_agent()
        if agent is None:
            return jsonify({
                "error": f"Agent is not ready. Please verify the {ACTIVE_LLM} API key in env/.env."
            }), 500

    data = request.get_json(force=True, silent=True) or {}
    message_text = data.get("message", "").strip()
    thread_id = str(data.get("thread_id") or config.default_thread_id).strip()

    if not message_text:
        return jsonify({"error": "Message cannot be empty."}), 400
    if not THREAD_ID_PATTERN.match(thread_id):
        return jsonify({"error": "Invalid thread_id."}), 400

    thread_config = _agent_config(current_user, thread_id)

    try:
        # Invoke agent on the user's own thread
        state = agent.invoke(
            {"messages": [HumanMessage(content=message_text)]},
            config=thread_config,
        )

        all_messages = state.get("messages", [])

        # Find the index of the latest HumanMessage to extract this turn's actions
        last_human_idx = -1
        for idx in range(len(all_messages) - 1, -1, -1):
            if isinstance(all_messages[idx], HumanMessage):
                last_human_idx = idx
                break

        turn_messages = all_messages[last_human_idx + 1:] if last_human_idx != -1 else all_messages

        # Extract tool calls and outputs from turn
        tool_events = []
        final_reply = ""

        # Map tool outputs by tool_call_id
        tool_outputs = {}
        for msg in turn_messages:
            if isinstance(msg, ToolMessage):
                tool_outputs[msg.tool_call_id] = str(msg.content)

        for msg in turn_messages:
            if isinstance(msg, AIMessage):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        t_id = tc.get("id")
                        tool_events.append({
                            "id": t_id,
                            "tool": tc.get("name"),
                            "args": tc.get("args"),
                            "output": tool_outputs.get(t_id, "Executed successfully")
                        })
                if msg.content and isinstance(msg.content, str):
                    final_reply = msg.content

        # Fallback if reply is still empty
        if not final_reply and turn_messages:
            for msg in reversed(turn_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    final_reply = str(msg.content)
                    break

        return jsonify({
            "success": True,
            "reply": final_reply or "Action completed.",
            "thread_id": thread_id,
            "tools_called": tool_events,
            "bookings_count": booking_db_manager.count(user_id=current_user["id"]),
            "timestamp": datetime.datetime.now().isoformat()
        })

    except Exception:
        # Log details server-side; don't leak internals (stack traces, provider errors) to the client
        logger.exception("Agent invocation failed for thread %s", thread_config["configurable"]["thread_id"])
        return jsonify({
            "success": False,
            "error": "The assistant hit an internal error while processing your message. Please try again."
        }), 500


@app.route("/api/platforms", methods=["GET"])
@traceable(name="get_platforms")
def get_platforms():
    """
    Returns curated authorized booking platforms with prefilled search URLs.
    """
    category = request.args.get("category", "flight").lower().strip()
    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()

    cat_key = "flight"
    if any(k in category for k in ["flight", "air", "plane"]):
        cat_key = "flight"
    elif any(k in category for k in ["train", "rail", "railway"]):
        cat_key = "train"
    elif any(k in category for k in ["bus", "coach"]):
        cat_key = "bus"
    elif any(k in category for k in ["movie", "cinema", "film"]):
        cat_key = "movie"
    elif any(k in category for k in ["event", "concert", "show"]):
        cat_key = "event"
    elif any(k in category for k in ["hotel", "stay", "resort"]):
        cat_key = "hotel"

    platforms = PLATFORMS_CATALOG.get(cat_key, PLATFORMS_CATALOG["flight"])
    enriched_platforms = []
    for p in platforms:
        target_url = p["url"]
        if cat_key == "flight" and origin and destination and p["name"] == "Google Flights":
            q = f"flights from {origin} to {destination}" + (f" on {date}" if date else "")
            target_url = f"https://www.google.com/travel/flights?q={urllib.parse.quote_plus(q)}"

        enriched_platforms.append({
            "name": p["name"],
            "url": target_url,
            "description": p["description"]
        })

    return jsonify({
        "category": cat_key,
        "origin": origin,
        "destination": destination,
        "date": date,
        "platforms": enriched_platforms
    })


@app.route("/api/pnr-status", methods=["GET", "POST"])
@traceable(name="check_pnr_status")
def check_pnr_status():
    """
    Instant PNR status checker identifying carrier systems and live portal links.
    """
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        pnr = data.get("pnr", "").strip()
    else:
        pnr = request.args.get("pnr", "").strip()

    if not pnr:
        return jsonify({"error": "PNR parameter cannot be empty."}), 400

    pnr_info = detect_pnr_info(pnr)
    # Format detection is public; saved booking details are only returned to their owner.
    # READ OPERATION: Route lookup to load-balanced Read Replica Pool
    current_user = get_current_user_from_request()
    booking_record = booking_db_manager.search_pnr(pnr, user_id=current_user["id"]) if current_user else None

    return jsonify({
        "pnr": pnr,
        "info": pnr_info,
        "has_local_booking": bool(booking_record),
        "booking": booking_record,
        "read_source": "Read-Replica-Pool"
    })


@app.route("/api/bookings", methods=["GET", "POST"])
@traceable(name="manage_bookings")
def manage_bookings():
    """
    GET returns all confirmed reservations (authenticated user).
    POST creates or registers a new ticket reservation or official carrier PNR.
    """
    current_user = get_current_user_from_request()

    if request.method == "POST":
        if not current_user:
            return jsonify({
                "success": False,
                "requires_auth": True,
                "error": "Authentication required. Please sign in to register itineraries or record carrier PNRs."
            }), 401

        data = request.get_json(force=True, silent=True) or {}
        default_names = [current_user.get("name", "Traveler")]
        result = book_ticket.invoke({
            "category": data.get("category", "flight"),
            "origin": data.get("origin", "N/A"),
            "destination": data.get("destination", "N/A"),
            "date": data.get("date", "N/A"),
            "passengers": int(data.get("passengers", 1)),
            "passenger_names": data.get("passenger_names") or default_names,
            "platform": data.get("platform", "Google Flights"),
            "official_pnr": data.get("official_pnr", ""),
            "ticket_class": data.get("ticket_class", "Economy"),
        }, config={"configurable": {"user_id": current_user["id"], "user_email": current_user["email"]}})
        return jsonify({
            "success": True,
            "result": result,
            "bookings_count": booking_db_manager.count(user_id=current_user["id"]),
            "bookings": booking_db_manager.list_bookings(user_id=current_user["id"]),
            "write_destination": "Primary-Master-DB (WAL SQLite)"
        })

    if not current_user:
        return jsonify({
            "authenticated": False,
            "count": 0,
            "bookings": [],
            "read_source": "Read-Replica-Pool"
        })

    # READ OPERATION: Route query to load-balanced Read Replica Pool
    bookings_list = booking_db_manager.list_bookings(user_id=current_user["id"])
    return jsonify({
        "authenticated": True,
        "count": len(bookings_list),
        "bookings": bookings_list,
        "read_source": "Read-Replica-Pool",
        "db_metrics": booking_db_manager.get_metrics()
    })


@app.route("/api/database/status", methods=["GET"])
@app.route("/api/database/metrics", methods=["GET"])
@traceable(name="database_metrics")
def get_database_metrics():
    """
    Returns real-time diagnostics of the Read/Write Separated Database architecture.
    Includes Primary Master write stats, Read Replica Pool status, replication lag, and latency.
    """
    if not get_current_user_from_request():
        return jsonify({"requires_auth": True, "error": "Authentication required."}), 401
    return jsonify(booking_db_manager.get_metrics())


@app.route("/api/reset", methods=["POST"])
@traceable(name="reset_thread")
def reset_thread():
    """
    Generates a new thread ID for starting a clean conversation.
    """
    new_thread_id = str(uuid.uuid4())[:8]
    return jsonify({
        "success": True,
        "new_thread_id": new_thread_id,
        "message": f"New thread {new_thread_id} initialized."
    })


# Frontend Static & PWA Serving
@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory(FRONTEND_DIR, "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def serve_sw():
    response = send_from_directory(FRONTEND_DIR, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.route("/.well-known/assetlinks.json")
def serve_assetlinks():
    return send_from_directory(os.path.join(FRONTEND_DIR, ".well-known"), "assetlinks.json", mimetype="application/json")

@app.route("/privacy")
def serve_privacy():
    return send_from_directory(FRONTEND_DIR, "privacy.html")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@traceable(name="serve_frontend")
def serve_frontend(path):
    """Serves the React frontend SPA."""
    if path and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("=" * 60)
    print(f" LangGraph Agent Backend running at http://127.0.0.1:{port}")
    print(f" Frontend React UI available at  http://127.0.0.1:{port}")
    print(" API key is securely handled by the backend server.")
    print("=" * 60)
    app.run(host="127.0.0.1", port=port, debug=False)
