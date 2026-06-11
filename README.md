# AI Voice Calling Agent

> **Portfolio project** — A practical prototype of an AI-powered outbound voice calling agent for appointment scheduling. Built with FastAPI, LangGraph, OpenAI, and Redis. Not a production system.
>
> ---
>
> ## What This Does
>
> This project simulates an outbound phone call agent that can:
>
> - Greet a caller and ask for their appointment preference
> - - Check mock availability against a predefined schedule
>   - - Book appointments and return a confirmation
>     - - Ask follow-up questions when information is missing
>       - - Trigger a human handoff for low-confidence or failed interactions
>         - - Store full conversation context in Redis (with in-memory fallback)
>           - - Generate spoken responses via ElevenLabs TTS (mock mode available)
>             - - Transcribe speech via OpenAI Whisper (mock mode available)
>              
>               - Everything runs locally with `MOCK_MODE=true` — no paid API keys required.
>              
>               - ---
>
> ## Tech Stack
>
> | Component | Technology |
> |---|---|
> | Backend API | FastAPI + Uvicorn |
> | Agent Workflow | LangGraph |
> | LLM | OpenAI GPT-4o (configurable) |
> | Speech-to-Text | OpenAI Whisper API |
> | Text-to-Speech | ElevenLabs API |
> | Voice Webhook | Twilio (simulated) |
> | Session Memory | Redis (+ in-memory fallback) |
> | Data Store | JSON files (mock CRM + bookings) |
> | Containerization | Docker + Docker Compose |
> | Testing | pytest + pytest-asyncio |
>
> ---
>
> ## Project Structure
>
> ```
> ai-voice-calling-agent/
> ├── app/
> │   ├── main.py                    # FastAPI app + all endpoints
> │   ├── config.py                  # Settings loaded from .env
> │   ├── graph/
> │   │   └── voice_agent_graph.py   # LangGraph workflow
> │   ├── services/
> │   │   ├── stt_service.py         # Speech-to-text (Whisper / mock)
> │   │   ├── tts_service.py         # Text-to-speech (ElevenLabs / mock)
> │   │   ├── llm_service.py         # LLM response generation (OpenAI / mock)
> │   │   └── session_memory.py      # Redis session store
> │   ├── tools/
> │   │   ├── scheduler_tools.py     # Check availability, book appointment
> │   │   └── crm_tools.py           # Customer lookup by phone
> │   └── models/
> │       └── schemas.py             # Pydantic request/response models
> ├── tests/
> │   └── test_agent.py              # Unit + integration tests
> ├── data/                          # Auto-created: appointments.json, crm.json
> ├── .env.example                   # Environment variable template
> ├── requirements.txt
> ├── Dockerfile
> ├── docker-compose.yml
> └── README.md
> ```
>
> ---
>
> ## LangGraph Workflow
>
> The agent is implemented as a LangGraph state machine. Each call flows through these nodes:
>
> ```
> receive_call
>     └─> transcribe_audio
>             └─> understand_intent
>                     ├─> [book/cancel intent]  call_scheduler_tool
>                     │                               └─> generate_response
>                     │                                       └─> synthesize_voice
>                     │                                               └─> end_call
>                     │
>                     └─> [unclear/human intent] human_handoff
>                                                     └─> end_call
> ```
>
> **Node descriptions:**
>
> - **receive_call** — Initializes session, loads CRM context for caller personalization
> - - **transcribe_audio** — Normalizes the transcript from Twilio's SpeechResult (or mock)
>   - - **understand_intent** — Rule-based NLU: detects book/cancel/human/unclear intent
>     - - **call_scheduler_tool** — Checks availability, books appointment if confirmed
>       - - **generate_response** — Calls OpenAI GPT-4o (or mock) to generate spoken response
>         - - **synthesize_voice** — Converts text to audio via ElevenLabs (or mock URL)
>           - - **human_handoff** — Generates transfer message, marks session for human queue
>             - - **end_call** — Persists final state
>              
>               - ---
>
> ## API Endpoints
>
> | Method | Path | Description |
> |---|---|---|
> | GET | `/health` | Health check |
> | POST | `/webhook/voice` | Simulated Twilio incoming call webhook |
> | POST | `/agent/process` | Process a text transcript (no Twilio needed) |
> | POST | `/booking` | Directly book an appointment |
> | GET | `/booking/slots` | List available slots |
> | POST | `/agent/handoff` | Trigger human handoff for a session |
> | GET | `/crm/{phone}` | Look up a caller in the mock CRM |
>
> Interactive API docs: `http://localhost:8000/docs`
>
> ---
>
> ## Sample Conversation Flow
>
> ```
> [Outbound call initiated]
>
> Agent:  "Hi there! This is Aria calling to help schedule your appointment.
>          What day works best for you?"
>
> User:   "I want to book an appointment for tomorrow afternoon."
>
> [LangGraph: understand_intent → book_appointment → call_scheduler_tool]
> [Scheduler checks: tomorrow 2:00 PM ✓ available]
>
> Agent:  "Got it! I have an opening tomorrow at 2:00 PM and another at 4:30 PM.
>          Which works better for you?"
>
> User:   "2 PM works."
>
> [LangGraph: confirm → book_appointment → BK-A3F92C1D created]
>
> Agent:  "Perfect, I've booked you in for tomorrow at 2:00 PM.
>          Your confirmation ID is BK-A3F92C1D. Is there anything else I can help you with?"
>
> User:   "No, that's all."
>
> Agent:  "Great! Have a wonderful day. Goodbye!"
>
> [Session saved to Redis → end_call]
> ```
>
> ---
>
> ## Setup
>
> ### Option 1: Local (no Docker)
>
> ```bash
> # 1. Clone the repo
> git clone https://github.com/KeerthiBasam/ai-voice-calling-agent.git
> cd ai-voice-calling-agent
>
> # 2. Create and activate a virtual environment
> python -m venv venv
> source venv/bin/activate    # Windows: venv\Scripts\activate
>
> # 3. Install dependencies
> pip install -r requirements.txt
>
> # 4. Create your .env file
> cp .env.example .env
> # MOCK_MODE=true is the default — no API keys needed for local testing
>
> # 5. Start Redis (optional — app falls back to in-memory if Redis is unavailable)
> docker run -d -p 6379:6379 redis:7-alpine
>
> # 6. Run the server
> uvicorn app.main:app --reload --port 8000
> ```
>
> ### Option 2: Docker Compose
>
> ```bash
> cp .env.example .env
> docker-compose up --build
> ```
>
> The API will be available at `http://localhost:8000`.
>
> ---
>
> ## Environment Variables
>
> | Variable | Default | Description |
> |---|---|---|
> | `MOCK_MODE` | `true` | Skip real API calls; use mock responses |
> | `DEBUG` | `true` | Enable debug logging |
> | `OPENAI_API_KEY` | — | Required when `MOCK_MODE=false` |
> | `OPENAI_MODEL` | `gpt-4o` | Configurable OpenAI model |
> | `ELEVENLABS_API_KEY` | — | Required when `MOCK_MODE=false` |
> | `ELEVENLABS_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | ElevenLabs voice |
> | `TWILIO_ACCOUNT_SID` | — | Required for live call testing |
> | `TWILIO_AUTH_TOKEN` | — | Required for live call testing |
> | `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
> | `AGENT_NAME` | `Aria` | Name used in agent greetings |
> | `CONFIDENCE_THRESHOLD` | `0.6` | STT confidence below this triggers handoff |
>
> ---
>
> ## Sample curl Commands
>
> **Health check:**
> ```bash
> curl http://localhost:8000/health
> ```
>
> **Process a transcript (main test endpoint):**
> ```bash
> curl -X POST http://localhost:8000/agent/process \
>   -H "Content-Type: application/json" \
>   -d '{
>     "session_id": "test-call-001",
>     "transcript": "I want to book an appointment for tomorrow afternoon",
>     "confidence": 0.95
>   }'
> ```
>
> **Simulate a Twilio webhook:**
> ```bash
> curl -X POST http://localhost:8000/webhook/voice \
>   -H "Content-Type: application/json" \
>   -d '{
>     "CallSid": "CA123456",
>     "From": "+15550001111",
>     "To": "+15559999999",
>     "CallStatus": "in-progress",
>     "SpeechResult": "I would like to schedule an appointment tomorrow morning",
>     "Confidence": 0.92
>   }'
> ```
>
> **Book an appointment directly:**
> ```bash
> curl -X POST http://localhost:8000/booking \
>   -H "Content-Type: application/json" \
>   -d '{
>     "session_id": "test-call-001",
>     "caller_phone": "+15550001111",
>     "preferred_date": "tomorrow",
>     "preferred_time": "2:00 PM",
>     "reason": "Annual checkup"
>   }'
> ```
>
> **Look up a caller in the mock CRM:**
> ```bash
> curl http://localhost:8000/crm/+15550001111
> ```
>
> **Get available slots:**
> ```bash
> curl http://localhost:8000/booking/slots
> ```
>
> ---
>
> ## Running Tests
>
> ```bash
> # All tests run in MOCK_MODE — no API keys needed
> pytest tests/ -v
> ```
>
> ---
>
> ## Limitations
>
> This is a **prototype**, not a production system. Known limitations:
>
> - **No real phone calls** — Twilio integration is simulated via webhook payloads. Connecting to real Twilio would require a public URL (e.g., via ngrok) and a Twilio account.
> - - **Rule-based intent detection** — The `understand_intent` node uses simple keyword matching. A production system would use LLM function-calling or a fine-tuned classifier.
>   - - **Mock scheduler** — Availability is based on a hardcoded list, not a real calendar API (Google Calendar, Calendly, etc.).
>     - - **No audio streaming** — The Twilio webhook flow here exchanges JSON. A real deployment would use TwiML + WebSockets for live audio.
>       - - **Single-turn graph** — The LangGraph workflow runs one pass per turn. Multi-turn dialogue is managed via Redis session state between calls.
>        
>         - ---
>
> ## Possible Improvements
>
> - Connect to a real calendar API (Google Calendar, Calendly)
> - - Replace rule-based NLU with LLM function-calling for intent detection
>   - - Add WebSocket support for real-time audio streaming with Twilio Media Streams
>     - - Add Twilio TwiML response generation for actual call control
>       - - Add authentication/rate limiting to the webhook endpoint
>         - - Replace the JSON CRM store with a real database (PostgreSQL, MongoDB)
>           - - Add a simple frontend dashboard to visualize active sessions
>            
>             - ---
>
> ## Why I Built This
>
> I wanted a hands-on project that combines several things I find interesting: conversational AI, real-time workflows, and the practical side of deploying LLM-powered agents. This prototype demonstrates a realistic voice agent architecture that I could extend toward production — it's intentionally kept small so every piece is explainable.
>
> ---
>
> *This is a personal portfolio project. It is not affiliated with or endorsed by Twilio, OpenAI, or ElevenLabs.*
> 
