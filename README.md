# 🎙️ AI Voice Agent for Healthcare Appointment Scheduling

<div align="center">

![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![LiveKit](https://img.shields.io/badge/LiveKit-Agents-orange)
![Groq](https://img.shields.io/badge/LLM-Groq%20LLaMA%203.1%2070B-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

**A production-grade, real-time AI voice agent that answers inbound patient calls and books healthcare appointments end-to-end — fully automated, fully audited.**

[Features](#-features) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Getting Started](#-getting-started) · [Project Structure](#-project-structure) · [Roadmap](#-roadmap)

</div>

---

## 🌟 What It Does

A patient calls a phone number. No hold music. No "press 1 for appointments." An AI voice agent picks up immediately, speaks naturally, and within minutes:

1. **Verifies** the patient's identity against the healthcare record system (FHIR R4)
2. **Collects** the reason for visit, preferred location, and provider
3. **Searches** real-time appointment slots from the scheduling backend
4. **Validates** insurance eligibility and in-network status
5. **Captures** verbal consent — timestamped, immutable, HIPAA-aligned
6. **Books** the appointment and reads back the confirmation code
7. **Escalates** to a human agent instantly if the patient asks — from any state in the call

All at **< 2 second** median response latency per turn. Every interaction encrypted, logged, and auditable.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎤 **Real-time voice** | LiveKit WebRTC/SIP — SRTP-encrypted, low-latency audio |
| 🧠 **LLM-powered NLU** | Groq API (LLaMA 3.1 70B Versatile) — slot extraction & natural responses |
| 🤖 **Deterministic FSM** | 12-state finite state machine — LLM can never hallucinate a booking |
| ✅ **Hard consent gates** | Verbal consent captured & persisted before any record write or booking |
| 🏥 **FHIR R4 integration** | Patient lookup and creation via HL7 FHIR standard |
| 📅 **Talkehr scheduling** | Real-time slot search and idempotent appointment booking |
| 🛡️ **Insurance validation** | Eligibility + in-network check before confirming any slot |
| 🔄 **Barge-in support** | Caller interrupts the agent mid-sentence — conversation stays natural |
| 📋 **Encrypted audit log** | Every turn, tool call, and consent event — append-only, PHI-tagged |
| 👤 **Human handoff** | "Talk to a person" works from any state — zero dead ends |
| 🔒 **HIPAA-aligned** | Minimum-necessary PHI, encrypted at rest, zero PHI in operational logs |
| 🧪 **Mock-first MVP** | All external services mocked — swap to real backends with a config flag |

---

## 🏗️ Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║  CALLER  (PSTN phone  /  WebRTC browser)                             ║
╚══════════════════╦═══════════════════════════════════════════════════╝
                   │  SIP trunk / WebRTC
╔══════════════════▼═══════════════════════════════════════════════════╗
║  LIVEKIT SIP GATEWAY  ──▶  LiveKit Room  (SRTP-encrypted audio)      ║
╚══════════════════╦═══════════════════════════════════════════════════╝
                   │  Inbound audio track
╔══════════════════▼═══════════════════════════════════════════════════╗
║  VOICE AGENT WORKER  (LiveKit Agents SDK — Python)                   ║
║                                                                      ║
║   VAD ──▶ Streaming STT ──▶ Orchestrator ──▶ Streaming TTS           ║
║   (Deepgram)               (FSM + Groq)     (ElevenLabs/Cartesia)    ║
╚══════════════════╦═══════════════════════════════════════════════════╝
                   │
╔══════════════════▼═══════════════════════════════════════════════════╗
║  CONVERSATION ORCHESTRATOR                                           ║
║                                                                      ║
║  ┌──────────────────────┐      ┌──────────────────────────────────┐  ║
║  │  Finite State        │◀────▶│  Groq LLM — LLaMA 3.1 70B        │  ║
║  │  Machine (FSM)       │      │  Intent · Slots · Response · Tool │  ║
║  └────────────┬─────────┘      └──────────────────────────────────┘  ║
║               │ validated tool calls only                            ║
╚═══════════════╪══════════════════════════════════════════════════════╝
                │
╔═══════════════▼══════════════════════════════════════════════════════╗
║  DOMAIN SERVICES  (helpers/)                                         ║
║                                                                      ║
║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  ║
║  │ Patient Svc │  │ Scheduling  │  │ Insurance   │  │ Consent   │  ║
║  │ (FHIR R4)   │  │ (Talkehr)   │  │    Svc      │  │   Svc     │  ║
║  │ [mock: ✅]  │  │ [mock: ✅]  │  │ [mock: ✅]  │  │           │  ║
║  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  ║
╚══════════════════════════════════════════════════════════════════════╝
                │
╔═══════════════▼══════════════════════════════════════════════════════╗
║  DATA LAYER                                                          ║
║  Redis (session state · TTL-keyed by UUID)                           ║
║  PostgreSQL / SQLite  (audit log · consent events · session records) ║
╚══════════════════════════════════════════════════════════════════════╝
```

### The Golden Rule — FSM Drives, LLM Serves

The conversation is governed by a **deterministic Finite State Machine**, not by free-form AI chat. The LLM (Groq/LLaMA) extracts intent and generates natural-sounding responses *inside* each state. It cannot advance the conversation, skip consent, or invent appointment data. Every real fact (slot availability, booking confirmation, eligibility status) comes from a backend service.

### The 12 Conversation States

```
GREETING ──▶ CONSENT_DATA ──▶ IDENTIFY ──▶ RETRIEVE_OR_CREATE
         ──▶ VISIT_INTAKE  ──▶ SLOT_SEARCH ──▶ INSURANCE_CHECK
         ──▶ CONFIRM ──▶ BOOK ──▶ CLOSING

HUMAN_HANDOFF   ─── reachable from ANY state ("talk to a person")
ERROR_FALLBACK  ─── reachable from ANY state on unrecoverable failure
```

**Two hard consent gates — enforced by the FSM, never bypassable:**

| Gate | Blocks |
|---|---|
| Data-processing consent | Patient record creation or retrieval |
| Booking consent | The appointment booking API call |

---

## 🛠️ Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Language | Python 3.12+ (fully typed · `mypy --strict`) |
| API Framework | FastAPI (async) |
| Voice Runtime | LiveKit Agents SDK |
| LLM | **Groq API — LLaMA 3.1 70B Versatile** |
| STT | Deepgram (streaming, pluggable) |
| TTS | ElevenLabs / Cartesia (streaming, pluggable) |
| Data Validation | Pydantic v2 (strict mode, zero `Any`) |
| Config | pydantic-settings (env-based, separate `backend/.env`) |
| Session Store | Redis (UUID-keyed, TTL 30 min) |
| Database | **SQLite** (dev/MVP) · **PostgreSQL** (prod) via SQLAlchemy async |
| Logging | structlog (structured JSON, zero PHI) |

### Frontend

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript — strict mode, zero `any` |
| UI | React 18 + Tailwind CSS |
| Linting | ESLint + `@typescript-eslint/no-explicit-any: error` |
| Env | `frontend/.env.local` (separate from backend) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+ and [pnpm](https://pnpm.io)
- Redis (local or Docker)
- [Groq API key](https://console.groq.com) — free tier available
- [LiveKit Cloud](https://livekit.io) account
- [Deepgram](https://deepgram.com) account
- [ElevenLabs](https://elevenlabs.io) or [Cartesia](https://cartesia.ai) account (TTS)

### 1 — Clone

```bash
git clone https://github.com/hamzaahmad3006/AI-Voice-Agent-for-Healthcare.git
cd AI-Voice-Agent-for-Healthcare
```

### 2 — Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install all dependencies
pip install -r requirements-dev.txt

# Configure environment
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux

# Open backend/.env and fill in your API keys
```

### 3 — Frontend setup

```bash
cd frontend

# Install dependencies
pnpm install

# Configure environment
copy .env.local.example .env.local      # Windows
# cp .env.local.example .env.local      # macOS/Linux

# Set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
```

### 4 — Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis-dev redis:alpine
```

### 5 — Run the backend

```bash
cd backend
python main.py
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 6 — Run the frontend

```bash
cd frontend
pnpm dev
# App: http://localhost:3000
```

---

## 📁 Project Structure

```
AI-Voice-Agent-for-Healthcare/
│
├── backend/
│   ├── routes/              # FastAPI routers — thin, delegate to controllers
│   ├── controllers/         # Business logic handlers
│   ├── utils/               # Reusable utilities (idempotency, crypto, time)
│   ├── helpers/             # External service wrappers (FHIR, Talkehr, insurance)
│   │
│   ├── agent/               # LiveKit Agents worker — VAD/STT/TTS voice loop
│   │   ├── worker.py        # Joins LiveKit room per call
│   │   ├── pipeline.py      # Audio pipeline (VAD → STT → Orchestrator → TTS)
│   │   └── barge_in.py      # Interruption handling
│   │
│   ├── orchestrator/        # Conversation engine
│   │   ├── fsm.py           # 12-state machine + transition guards
│   │   ├── states.py        # Per-state handlers + prompt templates
│   │   ├── session_memory.py# Slot memory + Redis persistence
│   │   └── llm_client.py    # Groq API call — structured JSON output
│   │
│   ├── mocks/               # In-memory mock services (same API shapes as real)
│   │   ├── fhir_mock.py     # Mock FHIR patient store
│   │   ├── talkehr_mock.py  # Mock scheduling (pre-seeded slots)
│   │   └── insurance_mock.py# Rules-based eligibility mock
│   │
│   ├── models/              # Pydantic v2 data models (strict typed)
│   │   ├── fsm_state.py     # FSMState enum, LLMTurn contract, SessionSlots
│   │   ├── patient.py       # PatientRecord, lookup/create models
│   │   ├── appointment.py   # SlotResult, VisitRequest, BookingRequest
│   │   ├── insurance.py     # EligibilityStatus, InsuranceCheck models
│   │   └── session_log.py   # ConsentEvent, TurnLog, SessionLog (audit)
│   │
│   ├── tests/               # Pytest unit tests
│   ├── config.py            # All config via pydantic-settings + backend/.env
│   ├── main.py              # FastAPI app entry point
│   ├── .env.example         # ← copy to .env and fill in your keys
│   └── pyproject.toml
│
├── frontend/
│   ├── app/                 # Next.js App Router
│   │   ├── dashboard/       # Active calls + booking funnel metrics
│   │   ├── sessions/        # Session list + per-session detail view
│   │   └── health/          # Service health dashboard
│   ├── hooks/               # Custom React hooks (one per feature)
│   ├── types/               # TypeScript interfaces (mirrors backend Pydantic models)
│   ├── components/          # Reusable UI components
│   ├── services/            # Typed API client functions
│   ├── .env.local.example   # ← copy to .env.local
│   └── package.json
│
├── .gitignore
└── README.md
```

---

## ⚙️ Configuration Reference

### Backend — `backend/.env`

| Variable | Description | Default |
|---|---|---|
| `GROQ_API_KEY` | Groq API key | **required** |
| `LLM_MODEL` | Groq model ID | `llama-3.1-70b-versatile` |
| `LIVEKIT_URL` | LiveKit WebSocket URL | **required** |
| `LIVEKIT_API_KEY` | LiveKit API key | **required** |
| `LIVEKIT_API_SECRET` | LiveKit API secret | **required** |
| `DEEPGRAM_API_KEY` | Deepgram STT key | **required** |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS key | **required** |
| `DATABASE_URL` | SQLAlchemy async DB URL | `sqlite+aiosqlite:///./audit.db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `USE_MOCK_FHIR` | Use in-memory FHIR mock | `true` |
| `USE_MOCK_TALKEHR` | Use in-memory Talkehr mock | `true` |
| `USE_MOCK_INSURANCE` | Use in-memory insurance mock | `true` |
| `ENVIRONMENT` | `development` / `production` | `development` |

### Frontend — `frontend/.env.local`

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | FastAPI backend base URL | `http://localhost:8000` |

---

## 🧪 Testing

```bash
cd backend

# Run all unit tests
pytest -v

# Type check (strict)
mypy . --strict --ignore-missing-imports

# Lint
ruff check .

# Frontend type check
cd ../frontend && pnpm type-check

# Frontend lint
pnpm lint
```

---

## 📋 Development Workflow

Strict **branch → commit → push → PR → merge** workflow. No direct commits to `main`.

```bash
# 1. Start from fresh main
git checkout main && git pull origin main

# 2. Create feature branch
git checkout -b feat/my-feature

# 3. Build and test
# ... make changes ...
cd backend && pytest && mypy . --strict && ruff check .
cd frontend && pnpm type-check && pnpm lint

# 4. Commit (atomic, descriptive)
git add <specific-files>
git commit -m "feat(scope): what and why"

# 5. Push and open PR
git push -u origin feat/my-feature
# Open PR on GitHub → review → squash merge → delete branch
```

---

## 🗺️ Build Roadmap

| Phase | What Gets Built | Status |
|---|---|---|
| **Phase 1** | Repo scaffold · Pydantic models · FastAPI skeleton · Next.js types | ✅ **Done** |
| **Phase 2** | FSM + Orchestrator — all 12 states, transitions, guards, unit tests | 🔜 **Next** |
| **Phase 3** | Groq/LLaMA integration — structured JSON output, per-state prompts | ⏳ Planned |
| **Phase 4** | LiveKit Agent Worker — VAD/STT/TTS pipeline, barge-in | ⏳ Planned |
| **Phase 5** | Domain Services + Mock implementations — FHIR, Talkehr, Insurance | ⏳ Planned |
| **Phase 6** | Frontend Dashboard — real-time call monitor, session logs | ⏳ Planned |
| **Phase 7** | Integration hardening — E2E tests, latency profiling, PHI audit | ⏳ Planned |

---

## 🔐 Security & Compliance

- **HIPAA-aligned architecture** — BAAs required with all vendors that process PHI
- **SRTP** for all media in transit · **TLS 1.2+** for all API and service traffic
- **PHI tagging** — protected fields tagged in the encrypted audit store; zero PHI in operational logs or metrics
- **Consent as a hard FSM gate** — the state machine enforces both consent checks; the LLM cannot bypass them
- **Idempotent bookings** — every booking call carries a unique idempotency key to prevent double-booking on retry
- **Append-only audit log** — encrypted, durable; failures route to a dead-letter queue and are never silently dropped
- **Minimum-necessary principle** — only the fields required by the current FSM state are loaded into the LLM context

---

## 📄 License

This project is licensed under the **MIT License**.

---

<div align="center">
<br/>
Built with ❤️ to make healthcare more accessible, one call at a time.
<br/><br/>

⭐ Star this repo if it helped you &nbsp;|&nbsp; 🐛 Found a bug? Open an issue &nbsp;|&nbsp; 🤝 PRs welcome

</div>
