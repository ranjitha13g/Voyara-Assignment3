# ✈️ Voyara — AI-Powered Journey Companion

Voyara is an agentic AI travel planner that takes your travel preferences through a conversational multi-step UI, uses Google Gemini to curate personalised trip packages, and delivers the results to your email — all from your browser on localhost.

---

[Watch the video](https://youtu.be/IgCcIvHCk88)

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Architecture & Flow](#architecture--flow)
- [Transport Subagent](#transport-subagent)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the App](#running-the-app)
- [Using the UI](#using-the-ui)
- [Logging](#logging)
- [Environment Variables](#environment-variables)
- [Tech Stack](#tech-stack)

---

## Features

- **4-step conversational wizard** — month, year, destination, trip type, email
- **India region selector** — Northern / Southern / Eastern / Western / Central / All
- **12 trip-type styles** — Beach, Trek, Hill Station, Wildlife, Heritage, Spiritual, Honeymoon, Family, Backpacking, Luxury, Snow, Island
- **Gemini-powered recommendations** — 5 curated packages with highlights, budget range, and real booking links
- **Transport Subagent** — per-package button to get Flights / Trains / Buses with fares, durations, and booking links
- **HTML email delivery** — beautifully formatted email sent automatically to the user (travel packages + optional transport plan)
- **Immersive UI** — full-viewport travel photography backgrounds that crossfade between steps
- **Structured logging** — every step of the agent flow printed to terminal and saved to a timestamped log file
- **Apache / Python HTTP server auto-detection** — startup script picks the right server automatically

---

## Project Structure

```
Assigenment3-1/
│
├── backend/
│   ├── agent.py          # FastAPI app + Gemini agent + email sender
│   └── logs/             # Auto-created; one log file per server startup
│
├── frontend/
│   └── index.html        # Single-page UI (no framework, pure HTML/CSS/JS)
│
├── .env                  # API keys and SMTP credentials (never commit this)
├── requirements.txt      # Python dependencies
└── start-servers.ps1     # One-click startup script (Windows PowerShell)
```

---

## Architecture & Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (localhost)                       │
│                                                                  │
│   Step 1: Travel Month & Year                                    │
│   Step 2: India (+ region) or International (+ country)         │
│   Step 3: Trip types  (beach, trek, hillstation, …)             │
│   Step 4: Email address                                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │  POST /plan-trip  (JSON)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend  :8000                         │
│                                                                  │
│   STEP 1  Build structured prompt from user inputs              │
│   STEP 2  Call Gemini API  (gemini-3-flash-preview)           │
│   STEP 3  Receive response  (~10–30 s)                          │
│   STEP 4  Parse 5 travel packages from JSON response            │
│   STEP 5  Compose rich HTML email                               │
│   STEP 6  Connect to Gmail SMTP (TLS)                           │
│   STEP 7  Deliver email → user's inbox                          │
│                                                                  │
│   Every step is logged to terminal + logs/travel_agent_*.log    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
              ┌─────────────────┴──────────────────┐
              ▼                                     ▼
   ┌────────────────────┐             ┌─────────────────────────┐
   │   Google Gemini    │             │   Gmail SMTP  :587       │
   │  (AI package gen)  │             │  (email delivery)        │
   └────────────────────┘             └─────────────────────────┘
                                                    │
                                                    ▼
                                        User's email inbox
```

Each package returned by Gemini includes:

| Field | Description |
|---|---|
| `name` | Package / trip name |
| `destination` | City, State / Country |
| `best_for` | Why this period is ideal |
| `highlights` | 3–5 activity/attraction bullets |
| `budget_per_person` | Estimated INR range |
| `links` | 2–3 booking/reference URLs |

---

## Transport Subagent

After travel packages are displayed, each package card has a **"View Transport Plan"** button. Clicking it opens a modal powered by a dedicated transport subagent.

### How it works

```
User clicks "View Transport Plan" on a package
           │
           ▼
   Modal opens — asks:
   - Your departure city
   - Email the plan? (optional)
           │
           │  POST /transport-plan
           ▼
   Transport Subagent (Gemini)
   - Finds flight options with fares + booking links
   - Finds train options (IRCTC, RailYatri)
   - Finds bus / road options (redBus, AbhiBus)
   - Gives seasonal travel tip + best-mode recommendation
           │
           ├──→  Results rendered in modal
           └──→  HTML email sent (if requested)
```

### API Endpoint

`POST /transport-plan`

```json
{
  "origin_city":  "Bangalore",
  "destination":  "Rishikesh, Uttarakhand",
  "travel_month": "June",
  "travel_year":  "2026",
  "email":        "user@example.com"   // optional — omit to skip email
}
```

Response includes `flights`, `trains`, `buses` arrays and a `summary` string.

### Transport log output

```
TRANSPORT SUBAGENT  ▶  Prompt built
  From     : Bangalore
  To       : Rishikesh, Uttarakhand
  Period   : June 2026
TRANSPORT SUBAGENT  ▶  Calling Gemini API
TRANSPORT SUBAGENT  ▶  Response received (18.4s, 3812 chars)
TRANSPORT SUBAGENT  ▶  Parsed: 2 flights, 3 trains, 2 buses
TRANSPORT SUBAGENT  ▶  Sending email to user@example.com
TRANSPORT SUBAGENT  ▶  Email delivered → user@example.com
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` |
| pip | Comes with Python |
| Google Gemini API key | [Get one free at Google AI Studio](https://aistudio.google.com/app/apikey) |
| Gmail account with App Password | Enable 2FA → [Create App Password](https://myaccount.google.com/apppasswords) |
| XAMPP *(optional)* | For Apache hosting; falls back to Python HTTP server |

---

## Setup

### 1. Clone / open the project

```
cd "Assigenment3-1"
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Edit the `.env` file in the project root:

```env
# Google Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Gmail SMTP (use an App Password, NOT your account password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx
```

> **Gmail App Password setup:**
> Google Account → Security → 2-Step Verification → App Passwords → Select app: Mail → Generate

---

## Running the App

### Option A — One-click startup (recommended)

```powershell
powershell -ExecutionPolicy Bypass -File start-servers.ps1
```

This script:
1. Starts the **FastAPI backend** on `http://localhost:8000` in a new window
2. Detects **XAMPP Apache** → deploys frontend to `htdocs/travel-planner/` → `http://localhost/travel-planner/`
3. Falls back to **Python HTTP server** on `http://localhost:8080` if XAMPP is absent
4. Opens the browser automatically

### Option B — Manual start

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn agent:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
python -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

### API Docs (Swagger UI)

Once the backend is running, visit:
```
http://localhost:8000/docs
```

---

## Using the UI

| Step | What to do |
|---|---|
| **1 — When** | Select travel month and year (2026–2030) |
| **2 — Where** | Choose *Within India* (then pick a region) or *International* (optionally enter a country) |
| **3 — What** | Click one or more trip-type pills (beach, trek, heritage, etc.) |
| **4 — Email** | Enter your email address |
| **Find Trip** | Voyara calls Gemini, generates 5 packages, emails them, and displays results on screen |

---

## Logging

Every request is fully traced. Log files are saved automatically at:

```
backend/logs/travel_agent_YYYYMMDD_HHMMSS.log
```

Example log output:

```
2026-04-23 09:37:17  INFO  NEW REQUEST  →  POST /plan-trip
2026-04-23 09:37:17  INFO  Month  : January   Year   : 2026
2026-04-23 09:37:17  INFO  Dest   : india   Region : Northern India
2026-04-23 09:37:17  INFO  Types  : ['beach', 'heritage']
2026-04-23 09:37:17  INFO  STEP 1  ▶  Gemini prompt built  (1228 chars)
2026-04-23 09:37:17  INFO  STEP 2  ▶  Calling Gemini API  (gemini-2.0-flash-preview)
2026-04-23 09:37:48  INFO  STEP 3  ▶  Response received  (31.01s, 4471 chars)
2026-04-23 09:37:48  INFO  STEP 4  ▶  Parsed 5 packages
2026-04-23 09:37:48  INFO  STEP 5  ▶  Composing HTML email
2026-04-23 09:37:52  INFO  STEP 7  ▶  Email delivered → mgautham16@gmail.com
2026-04-23 09:37:52  INFO  REQUEST COMPLETE  ✓
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google AI Studio API key |
| `SMTP_HOST` | No | Default: `smtp.gmail.com` |
| `SMTP_PORT` | No | Default: `587` |
| `SMTP_USER` | Yes | Gmail address used to send |
| `SMTP_PASS` | Yes | Gmail App Password (16-char) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI / LLM | Google Gemini `gemini-2.0-flash-preview` via `google-genai` SDK |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Email | Python `smtplib` (SMTP + STARTTLS) |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript (no framework) |
| Fonts | Google Fonts — Playfair Display + Inter |
| Background images | Unsplash (CDN, no download needed) |
| Web server | Apache via XAMPP *or* Python `http.server` |
| Logging | Python `logging` → stdout + timestamped file |
# Voyara-Assignment3
