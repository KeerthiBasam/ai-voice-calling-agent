"""
FastAPI application entry point.

Endpoints:
  GET  /health                  - Health check
    POST /webhook/voice           - Incoming Twilio voice webhook (simulated)
      POST /agent/process           - Process a transcript and get agent response
        POST /booking                 - Mock appointment booking
          POST /agent/handoff           - Trigger human handoff
          """

import uuid
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.models.schemas import (
    TwilioWebhookRequest,
    TranscriptRequest,
    AgentResponse,
    BookingRequest,
    BookingResponse,
    AgentState,
)
from app.graph.voice_agent_graph import voice_agent
from app.services import session_memory
from app.tools.scheduler_tools import book_appointment, get_available_slots
from app.tools.crm_tools import lookup_customer_by_phone

logging.basicConfig(
      level=logging.DEBUG if settings.DEBUG else logging.INFO,
      format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
      logger.info(f"Starting {settings.APP_NAME} (mock_mode={settings.MOCK_MODE})")
      yield
      logger.info("Shutting down.")


app = FastAPI(
      title=settings.APP_NAME,
      description="AI Voice Calling Agent - Portfolio project",
      version="0.1.0",
      lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
      return {
                "status": "ok",
                "app": settings.APP_NAME,
                "mock_mode": settings.MOCK_MODE,
      }


# ---------------------------------------------------------------------------
# Twilio voice webhook
# ---------------------------------------------------------------------------

@app.post("/webhook/voice")
async def twilio_voice_webhook(payload: TwilioWebhookRequest):
      """
          Simulates receiving an incoming Twilio call webhook.
              In a real deployment, Twilio POSTs call metadata here.
                  """
      session_id = payload.CallSid
      caller_phone = payload.From

    logger.info(f"Incoming call: session={session_id} from={caller_phone}")

    # Initialize session
    session_memory.get_or_create_session(session_id, caller_phone)

    transcript = payload.SpeechResult or ""
    confidence = payload.Confidence or 1.0

    # Run the LangGraph agent workflow
    initial_state = {
              "session_id": session_id,
              "caller_phone": caller_phone,
              "transcript": transcript,
              "confidence": confidence,
              "intent": "",
              "context": "",
              "history": [],
              "collected_info": {},
              "agent_text": "",
              "audio_url": "",
              "booking_result": None,
              "handoff_triggered": False,
              "current_state": AgentState.receive_call,
    }

    result = await voice_agent.ainvoke(initial_state)

    return AgentResponse(
              session_id=session_id,
              text_response=result.get("agent_text", ""),
              audio_url=result.get("audio_url"),
              state=result.get("current_state", AgentState.end_call),
              booking_confirmed=bool(result.get("booking_result", {}) and result["booking_result"].get("success")),
              handoff_triggered=result.get("handoff_triggered", False),
    )


# ---------------------------------------------------------------------------
# Process transcript (standalone endpoint for testing without Twilio)
# ---------------------------------------------------------------------------

@app.post("/agent/process", response_model=AgentResponse)
async def process_transcript(request: TranscriptRequest):
      """
          Process a text transcript through the agent workflow.
              Useful for testing the agent without a real phone call.
                  """
      session_id = request.session_id
      ctx = session_memory.load_session(session_id)
      caller_phone = ctx.caller_phone if ctx else "unknown"

    initial_state = {
              "session_id": session_id,
              "caller_phone": caller_phone,
              "transcript": request.transcript,
              "confidence": request.confidence or 1.0,
              "intent": "",
              "context": "",
              "history": [t.model_dump() for t in ctx.history] if ctx else [],
              "collected_info": ctx.collected_info if ctx else {},
              "agent_text": "",
              "audio_url": "",
              "booking_result": None,
              "handoff_triggered": False,
              "current_state": AgentState.receive_call,
    }

    result = await voice_agent.ainvoke(initial_state)

    return AgentResponse(
              session_id=session_id,
              text_response=result.get("agent_text", ""),
              audio_url=result.get("audio_url"),
              state=result.get("current_state", AgentState.end_call),
              booking_confirmed=bool(result.get("booking_result") and result["booking_result"].get("success")),
              handoff_triggered=result.get("handoff_triggered", False),
    )


# ---------------------------------------------------------------------------
# Mock appointment booking
# ---------------------------------------------------------------------------

@app.post("/booking", response_model=BookingResponse)
async def create_booking(request: BookingRequest):
      """Directly book an appointment (bypasses the agent workflow)."""
      result = book_appointment(
          caller_phone=request.caller_phone,
          preferred_date=request.preferred_date,
          preferred_time=request.preferred_time,
          reason=request.reason or "General appointment",
      )
      return BookingResponse(**result)


@app.get("/booking/slots")
async def available_slots():
      """Return the list of available appointment slots."""
      return {"available_slots": get_available_slots()}


# ---------------------------------------------------------------------------
# Human handoff
# ---------------------------------------------------------------------------

@app.post("/agent/handoff")
async def trigger_handoff(session_id: str):
      """
          Manually trigger a human handoff for an active session.
              In production this would notify a live agent queue.
                  """
      ctx = session_memory.load_session(session_id)
      if not ctx:
                raise HTTPException(status_code=404, detail="Session not found")

      session_memory.update_state(session_id, AgentState.human_handoff)
      session_memory.update_collected_info(session_id, {"handoff_triggered": True})

    logger.info(f"Human handoff triggered for session {session_id}")
    return {"status": "handoff_triggered", "session_id": session_id}


# ---------------------------------------------------------------------------
# CRM lookup (debug/demo)
# ---------------------------------------------------------------------------

@app.get("/crm/{phone}")
async def crm_lookup(phone: str):
      """Look up a caller by phone number in the mock CRM."""
      record = lookup_customer_by_phone(phone)
      if not record:
                return {"found": False, "phone": phone}
            return {"found": True, "record": record.model_dump()}


# ---------------------------------------------------------------------------
# Start server (for running directly with python app/main.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
      import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
