# Booking Agent - LangGraph AI Travel & Booking Assistant

Agent built for online travel and ticket booking. A full-stack AI Assistant application powered by **LangGraph**, a switchable LLM provider (Groq by default; Gemini, OpenAI, Anthropic, Ollama, and DeepSeek supported), and a modern **React Frontend**.

---

## Architecture Overview

```
langgraph/
├── agent/                         # Python Backend Agent Core
│   ├── chain.py                   # LCEL Chain (model | parser) + env-based LLM switching
│   ├── graph.py                   # StateGraph definition & tool compilation
│   ├── llm.py                     # LLM Provider exports and chain integration
│   ├── state.py                   # AgentState message definitions
│   ├── cli.py                     # Command-line interface runner
│   ├── skills/                    # Python tool implementations
│   │   ├── booking.py             # get_booking_platforms, book_ticket, check_ticket_status, get_database_status
│   │   ├── browsing.py            # browse_web search & public URL retrieval
│   │   ├── gmail.py               # send_booking_email & send_email via Gmail SMTP
│   │   ├── context.py             # Signed-in user passed to tools via RunnableConfig
│   │   └── skill.md               # Tool capabilities specification
│   └── storage/                   # SQLite persistence
│       ├── booking_db.py          # Read/Write separated booking store (CQRS)
│       └── user_db.py             # Users & login sessions
├── env/
│   ├── .env                       # Backend-only API keys & settings (never exposed to UI)
│   ├── .env.example               # Template environment configuration
│   └── config.py                  # Environment loader & settings
├── frontend/                      # React Frontend UI
│   ├── index.html                 # Standalone React 18 SPA (the page served by server.py)
│   ├── package.json               # Node/Vite package configuration
│   ├── vite.config.js             # Vite configuration with API proxy
│   └── src/                       # Modular React components (Vite build of the same UI)
├── data/                          # SQLite databases (default DATA_DIR, gitignored)
├── server.py                      # Flask REST API backend server
├── run_app.py                     # Launcher script (starts server & opens browser)
├── Dockerfile / Procfile / render.yaml  # Deployment configs
└── requirements.txt
```

---

## Choosing the LLM Provider

Set the provider in `env/.env` (or as an environment variable on your host):

```env
LLM_PROVIDER=groq        # Options: gemini | openai | anthropic | groq | ollama | deepseek
```

`ACTIVE_LLM` is also accepted as the variable name. If neither is set, the default is `groq`.

Each provider reads its API key and an optional model override from the environment:

| Provider    | API key variable    | Model variable     | Default model          |
|-------------|---------------------|--------------------|------------------------|
| `groq`      | `GROQ_API_KEY`      | `GROQ_MODEL`       | `openai/gpt-oss-120b`  |
| `gemini`    | `GEMINI_API_KEY`    | `GEMINI_MODEL`     | `gemini-3.8-flash`     |
| `openai`    | `OPENAI_API_KEY`    | `OPENAI_MODEL`     | `gpt-4o`               |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL`  | `claude-sonnet-5-5`    |
| `ollama`    | — (local)           | `OLLAMA_MODEL`     | `llama3.2`             |
| `deepseek`  | `DEEPSEEK_API_KEY`  | `DEEPSEEK_MODEL`   | `deepseek-chat`        |

The defaults live in `DEFAULT_MODELS` in [agent/chain.py](agent/chain.py), and `GET /api/status` reports the provider and model actually in use.

> Gemini uses `langchain-google-genai` if it is installed, and otherwise falls back to Google's OpenAI-compatible endpoint. On a server without a key, the agent reports an error rather than waiting for keyboard input.

### How the LCEL Chain Works

The agent uses a LangChain Expression Language (LCEL) chain combining the model and parser:

```python
# The model and parser are kept combined in the chain:
chain = model.bind_tools(tools) | parser
```

- **Model**: Instantiated for the provider selected by `LLM_PROVIDER`.
- **Parser**: Standardizes output into an `AIMessage` with tool calls and content preserved for the LangGraph workflow.

---

## Security & API Key Handling

- **Zero Client-Side Keys**: LLM and Gmail credentials are loaded only by the Python backend from `env/.env` or the host environment.
- **Protected UI**: The React UI never requests, stores, or transmits API keys.
- **Same-Origin by Default**: The UI is served by the API server, so cross-origin requests are refused unless you list allowed origins in `CORS_ORIGINS`.
- **No Internal Fetches**: `browse_web` only fetches public `http(s)` addresses, and it re-checks every redirect, so the agent cannot be pointed at localhost, cloud metadata endpoints, or private networks.
- **No Leaked Errors**: Agent failures are logged on the server. The client only receives a generic message.

### REST Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/auth/register` / `login` / `logout` | — | Account management; returns a session token |
| `POST /api/auth/demo` | — | Creates a private guest account (if `ENABLE_DEMO_LOGIN` is on) |
| `GET /api/auth/me` | token | Current user |
| `POST /api/chat` | required | Runs the agent on the user's own conversation thread |
| `GET/POST /api/bookings` | required | Lists or registers the user's own bookings |
| `GET /api/pnr-status` | optional | PNR format detection for anyone; saved booking details only for their owner |
| `GET /api/database/status` | required | CQRS database metrics |
| `GET /api/status` | — | Health check (provider, model, key configured — never the key itself) |
| `GET /api/platforms` | — | Booking platform catalog with prefilled links |
| `POST /api/reset` | — | Generates a new thread ID |

Authenticated requests send `Authorization: Bearer <token>`.

---

## Accounts, Demo Login & Per-User Data

- **Accounts**: Passwords are stored as salted hashes (werkzeug), and new passwords must be at least 8 characters. Login sessions are random tokens. Only a hash of each token is stored, and sessions expire after 30 days.
- **Guest Demo Login**: The "⚡ 1-Click Demo" / "Instant Demo Access" buttons create a **new private guest account on every click**, so demo visitors never see each other's chats or bookings. To disable it, set:
  ```env
  ENABLE_DEMO_LOGIN=false
  ```
  It is on by default for local development and turned off in `render.yaml`.
- **Per-User Conversations**: Each chat thread is stored under the signed-in user's ID. Two users who send the same `thread_id` still get separate histories. The UI gives each browser tab a random thread ID.
- **Per-User Bookings**: Every booking records the user who created it. Booking lists, PNR lookups, `check_ticket_status`, and booking emails only see the signed-in user's bookings.
- **Tools Can't Be Spoofed**: The server passes the user's identity to tools through LangGraph's `RunnableConfig` ([agent/skills/context.py](agent/skills/context.py)). It is hidden from the model's tool schema, so the model cannot choose or change which user it acts for.
- **Visitor Mode**: Signed-out visitors see the informational landing page. `/api/chat` and booking writes return `401` with `requires_auth: true`.

---

## LangSmith Tracing Workflow

All functions across the backend, tools, chain, and server are decorated with `@traceable` from `langsmith` for end-to-end observability:

- **Tools**: `get_booking_platforms`, `book_ticket`, `check_ticket_status`, `get_database_status`, `browse_web`, `send_booking_email`, `send_email`
- **Chain & LCEL**: `build_chain`, `get_model`, `AgentOutputParser.invoke`
- **LangGraph Graph**: `build_agent_graph`, `chatbot_node`
- **Server Endpoints**: `chat`, `get_status`, `manage_bookings`, `reset_thread`, `serve_frontend`, auth endpoints

### LangSmith Configuration in `env/.env`
```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your_langsmith_api_key"
LANGSMITH_PROJECT="booking-agent"
```

---

## Gmail Email Integration Setup

The agent can email booking confirmations as responsive HTML boarding passes.

**Emails only go to the signed-in user's own account address.** If the agent is asked, or steered by text on a web page it reads, to email anyone else, the tool refuses with `Email Delivery Blocked`. This stops the server's Gmail account from being used to send mail to arbitrary people. Booking details are HTML-escaped before they are placed in the email. Local CLI runs (`agent.cli`) have no signed-in user and are not restricted.

> Guest demo accounts use a placeholder `@demo.mantabooking.local` address, so emails for them will not be delivered. Register a real account to receive emails.

### Step-by-Step Setup:
1. Ensure **2-Step Verification** is enabled on your Google Account.
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Create a new App Password (e.g. name it `BookingAgent`).
4. Copy the generated 16-character password.
5. In `env/.env`, add:
```env
GMAIL_SENDER_EMAIL=your_google_account@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

*Note: If credentials are not set, the agent runs in safe dry-run mode. It formats the full email and itinerary preview without sending anything.*

---

## Data Storage & Persistence (`DATA_DIR`)

All server state is stored in SQLite files inside `DATA_DIR` (default: `./data`, which is gitignored):

| File | Contents |
|------|----------|
| `bookings_master.db` | Bookings, replication log, users, login sessions |
| `checkpoints.db` | LangGraph conversation history (`SqliteSaver`) |

Because nothing is held only in memory, the server survives restarts and can run with **multiple gunicorn workers**. A login, chat thread, or booking created on one worker is visible on every other worker.

Point `DATA_DIR` at persistent storage in production:

```env
DATA_DIR=/var/data
```

- **Render**: `render.yaml` mounts a 1 GB persistent disk at `/var/data` and sets `DATA_DIR` to it. Render's regular filesystem is wiped on every deploy, and persistent disks require a paid instance type.
- **Docker**: The image sets `DATA_DIR=/app/data` and declares it as a volume. Mount a named volume to keep data across containers:
  ```bash
  docker run -p 5000:5000 --env-file env/.env -v mantabooking-data:/app/data mantabooking
  ```
  `.dockerignore` excludes `env/.env`, `data/`, and `*.db`, so secrets and local data are never baked into the image. Pass them at runtime instead.

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

### Production
```bash
gunicorn -w 2 --threads 4 --timeout 120 -b 0.0.0.0:$PORT server:app
```
The 120-second timeout leaves room for multi-step agent turns, which can exceed gunicorn's 30-second default.

### Environment Variables Summary

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_PROVIDER` | `groq` | Active LLM provider |
| `<PROVIDER>_API_KEY` / `<PROVIDER>_MODEL` | — | Provider credentials and model override |
| `DATA_DIR` | `./data` | Where SQLite data is stored |
| `ENABLE_DEMO_LOGIN` | `true` | Allow 1-click guest accounts |
| `CORS_ORIGINS` | *(empty)* | Comma-separated origins allowed cross-origin |
| `GMAIL_SENDER_EMAIL` / `GMAIL_APP_PASSWORD` | — | Gmail sending (dry-run if unset) |
| `TEMPERATURE` | `0.3` | Model temperature |

---

## MantaBooking — Multi-Mode Travel Hub & Helper

The platform is branded as **MantaBooking**, providing multi-category booking studios and an AI helper agent:
- **6 Dedicated Studios**: Flights, IRCTC Trains, Hotels, Movies, Cabs, and Events.
- **Direct Official Booking Guarantee**: Direct verified handoff links to official carriers (IRCTC, airlines, Booking.com, BookMyShow, Uber) — zero fake bookings or unauthorized payments.
- **PNR Transparency**: Internal search draft references (`AGT-XXXX`) are clearly distinguished from official carrier confirmation numbers (10-digit IRCTC PNRs and 6-char Airline GDS codes).

---

## Google Play Store & Android App Deployment

MantaBooking is packaged and prepared for publication on the **Google Play Store**:

### Project Structure for Android:
- **`android/`**: Complete native Android Studio Gradle project targeting **Android 14/15 (API 34/35)** with package `com.mantabooking.app`, custom WebView, and Chrome Custom Tabs.
- **`frontend/manifest.json`**: Standalone PWA manifest with adaptive icons and category definitions.
- **`frontend/sw.js`**: Service Worker with network-first page loads (new deploys show immediately) and offline caching.
- **`frontend/.well-known/assetlinks.json`**: Digital Asset Links verification for full-screen immersive TWA mode.
- **`frontend/privacy.html` & `playstore/PRIVACY_POLICY.md`**: Mandatory public Privacy Policy.
- **`playstore/STORE_LISTING.md`**: Complete metadata, short/long descriptions, category, content rating answers, and Google Data Safety questionnaire.
- **`playstore/DEPLOYMENT_GUIDE.md`**: Step-by-step cloud deployment & Google Play submission walkthrough.
- **`playstore/feature_graphic_1024x500.png` & `playstore/icon_512x512.png`**: Official Google Play visual assets.

### Quick Build & Publish Steps:
1. **Deploy Cloud Backend**: Deploy using the included [`render.yaml`](render.yaml) or [`Dockerfile`](Dockerfile) to Render.com or Railway, with a persistent disk for `DATA_DIR` (see above).
2. **Generate Signed `.aab`**:
   - *Via Cloud (Fastest)*: Enter your live URL at [PWABuilder.com](https://www.pwabuilder.com) and download the signed `.aab`.
   - *Via Android Studio*: Open `android/` and select **Build > Generate Signed Bundle / APK...**
3. **Publish to Google Play**: Upload your `.aab` in the [Google Play Console](https://play.google.com/console) and copy-paste details from [`playstore/STORE_LISTING.md`](playstore/STORE_LISTING.md).

---

## Read/Write Separated Database Architecture (CQRS)

Booking storage separates writes from reads (**Command Query Responsibility Segregation**):

```
                      ┌───────────────────────────┐
                      │    Client / AI Requests   │
                      └─────────────┬─────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           │                                                 │
    [WRITES / COMMANDS]                              [READS / QUERIES]
   (New Bookings, PNR Updates)                   (PNR Tracking, Itineraries)
           │                                                 │
           ▼                                                 ▼
┌─────────────────────────────┐               ┌─────────────────────────────┐
│    Primary Master DB        │               │   Read Replica Pool (x2)    │
│  • SQLite with WAL Mode     │               │  • In-process read caches   │
│  • Thread-Safe Reentrant Lock│<──────────────│  • Pull log before each read│
│  • LSN Replication Log      │  Catch-up via │  • Per-user filtered queries│
│  • DATA_DIR/bookings_master │  LSN log      │  • Round-Robin Query Router │
└─────────────────────────────┘               └─────────────────────────────┘
```

- **Primary Master Database (`PrimaryWriteDatabase`)**:
  - Handles all mutations (`save_booking`, `delete_booking`).
  - Disk-backed ACID SQLite store (`DATA_DIR/bookings_master.db`) with Write-Ahead Logging (`PRAGMA journal_mode=WAL`).
  - Appends every change to a `replication_log` table with a monotonic Log Sequence Number (LSN).
  - The internal reference (`AGT-XX-XXXXXX`) is always the primary key. Carrier PNRs are indexed, so several users can register the same PNR without overwriting each other.
- **Read Replica Pool (`ReadReplicaDatabase` x 2)**:
  - In-process read caches (`replica-reader-01`, `replica-reader-02`) serving query traffic (`list_bookings`, `search_pnr`, `get_booking`), indexed on `booking_id`, `internal_ref`, and `official_pnr`.
  - Every read API takes a `user_id` and only returns that user's records.
- **Replication**:
  - Before serving a read, a replica pulls any log entries newer than its last applied LSN, in order. Every process (e.g. each gunicorn worker) therefore converges on the same state, including writes made by other workers.
- **Observability Endpoint**:
  - `GET /api/database/status` (sign-in required): CQRS metrics, LSN, query latency, and replica health.
- **Agent Skill**:
  - `get_database_status`: The AI helper can inspect and report live database metrics on demand.
