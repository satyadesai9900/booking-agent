"""
Backend API Server for LangGraph Agent.
Exposes REST endpoints for the React frontend.
The Gemini API key is securely handled on the backend and NEVER exposed to the frontend.
"""

import os
import sys
import uuid
import datetime
from typing import List, Dict, Any
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from env.config import get_gemini_api_key, config
from agent.llm import get_llm, build_chain, ACTIVE_LLM
from agent.graph import build_agent_graph
from agent.skills.booking import BOOKING_DATABASE

# Initialize Flask app
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# Global LangGraph agent instance with MemorySaver checkpointer
checkpointer = MemorySaver()
chain = None
agent = None


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


@app.route("/api/status", methods=["GET"])
def get_status():
    """
    Health check and status endpoint.
    Verifies backend agent readiness WITHOUT leaking the API key.
    """
    if ACTIVE_LLM == "groq":
        current_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        has_key = bool(os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "your_groq_api_key_here")
    elif ACTIVE_LLM == "openai":
        current_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        has_key = bool(os.getenv("OPENAI_API_KEY"))
    elif ACTIVE_LLM == "anthropic":
        current_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    else:
        current_model = config.gemini_model
        has_key = bool(os.getenv("GEMINI_API_KEY") or (config.gemini_api_key and config.gemini_api_key != "your_gemini_api_key_here"))

    return jsonify({
        "status": "ready" if agent is not None else "initializing",
        "provider": ACTIVE_LLM,
        "model": current_model,
        "chain": "model | parser",
        "api_key_configured": has_key,
        "checkpointer": "MemorySaver",
        "default_thread_id": config.default_thread_id,
        "skills": ["browse_web", "book_ticket", "check_ticket_status"],
        "bookings_count": len(BOOKING_DATABASE),
        "timestamp": datetime.datetime.now().isoformat()
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint for React frontend.
    Accepts user message and thread_id, executes LangGraph agent workflow,
    and returns assistant reply along with any executed tool calls and outputs.
    """
    global agent
    if agent is None:
        init_agent()
        if agent is None:
            return jsonify({
                "error": "Agent is not ready. Please verify GEMINI_API_KEY in env/.env."
            }), 500

    data = request.get_json(force=True, silent=True) or {}
    message_text = data.get("message", "").strip()
    thread_id = str(data.get("thread_id", config.default_thread_id) or config.default_thread_id)

    if not message_text:
        return jsonify({"error": "Message cannot be empty."}), 400

    thread_config = {"configurable": {"thread_id": thread_id}}

    try:
        # Invoke agent on the specified thread
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
            "bookings_count": len(BOOKING_DATABASE),
            "timestamp": datetime.datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    """
    Returns all confirmed reservations from the booking skill database.
    """
    bookings_list = list(BOOKING_DATABASE.values())
    return jsonify({
        "count": len(bookings_list),
        "bookings": bookings_list
    })


@app.route("/api/reset", methods=["POST"])
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


# Frontend Static Serving
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
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
