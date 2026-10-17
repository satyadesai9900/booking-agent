# Booking Agent - LangGraph AI Travel & Booking Assistant

Agent built for online travel and ticket booking. A full-stack AI Assistant application powered by **Google Gemini 3.8 Flash**, **LangGraph**, and a modern **React Frontend**.

---

## Architecture Overview

```
langgraph/
├── agent/                         # Python Backend Agent Core
│   ├── chain.py                   # LCEL Chain (model | parser) + single-line LLM switching
│   ├── graph.py                   # StateGraph definition & tool compilation
│   ├── llm.py                     # LLM Provider exports and chain integration
│   ├── state.py                   # AgentState message definitions
│   ├── cli.py                     # Command-line interface runner
│   └── skills/                    # Python tool implementations
│       ├── booking.py             # book_ticket & check_ticket_status
│       ├── browsing.py            # browse_web search & URL retrieval
│       └── skill.md               # Tool capabilities specification
├── env/
│   ├── .env                       # Backend-only API keys (never exposed to UI)
│   ├── .env.example               # Template environment configuration
│   └── config.py                  # Environment loader & settings
├── frontend/                      # React Frontend UI
│   ├── index.html                 # Standalone React 18 SPA (runs directly in any browser)
│   ├── package.json               # Node/Vite package configuration
│   ├── vite.config.js             # Vite configuration with API proxy
│   └── src/                       # Modular React components
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       └── components/
│           ├── Header.jsx         # App header with thread info & security status
│           ├── Sidebar.jsx        # Sidebar with capabilities & quick actions
│           ├── MessageBubble.jsx  # Formatted messages & visual ticket cards
│           ├── ToolExecutionCard.jsx # Expandable live tool inspector
│           ├── TicketConfirmationCard.jsx # Boarding pass visualizer
│           ├── BookingsDrawer.jsx # Slide-out active reservations drawer
│           └── Icons.jsx          # SVG icon collection
├── server.py                      # Flask REST API backend server
└── run_app.py                     # Launcher script (starts server & opens browser)
```

---

## Changing LLM with Just a Single Line of Code

Open [agent/chain.py](file:///c:/Users/satya/OneDrive/Desktop/langgraph/agent/chain.py) (or [agent/llm.py](file:///c:/Users/satya/OneDrive/Desktop/langgraph/agent/llm.py)) and edit line 18:

```python
# Change this SINGLE line to switch your model provider:
ACTIVE_LLM = "gemini"    # Options: "gemini" | "openai" | "anthropic" | "groq" | "ollama" | "deepseek"
```

You can also specify `LLM_PROVIDER=openai` in your `env/.env` file.

### How the LCEL Chain Works

The agent uses a LangChain Expression Language (LCEL) chain combining the model and parser:

```python
# The model and parser are kept combined in the chain:
chain = model.bind_tools(tools) | parser
```

- **Model**: Automatically instantiated based on `ACTIVE_LLM`.
- **Parser**: Standardizes output into an `AIMessage` with tool calls and content preserved for the LangGraph workflow.

---

## Security & API Key Handling

- **Zero Client-Side Keys**: The Gemini API key is loaded strictly by Python in `env/config.py` from `env/.env`.
- **Protected UI**: The React UI never requests, stores, or transmits the API key.
- **REST Endpoints**:
  - `POST /api/chat`: Runs the LangGraph agent for the active thread and returns the reply and executed tool events.
  - `GET /api/status`: Health check confirming backend model and key status without exposing secrets.
  - `GET /api/bookings`: Returns confirmed reservations from memory.
  - `POST /api/reset`: Resets or generates a new thread ID session.

---

## How to Run

### Option 1: One-Click Launcher (Recommended)
```powershell
.myenv\Scripts\python.exe run_app.py
```
This automatically starts the Python backend server on `http://127.0.0.1:5000` and opens the React UI in your default web browser.

### Option 2: Run Backend Server Manually
```powershell
.myenv\Scripts\python.exe server.py
```
Then visit `http://127.0.0.1:5000` in your web browser.

### Option 3: Terminal CLI Runner
```powershell
.myenv\Scripts\python.exe -m agent.cli
```
>>>>>>> d7ee9db (Initial commit: LangGraph travel assistant with React frontend and FastAPI server)
