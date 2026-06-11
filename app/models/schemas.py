"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class AgentState(str, Enum):
    receive_call = "receive_call"
    transcribe_audio = "transcribe_audio"
    understand_intent = "understand_intent"
    call_scheduler_tool = "call_scheduler_tool"
    generate_response = "generate_response"
    synthesize_voice = "synthesize_voice"
    human_handoff = "human_handoff"
    end_call = "end_call"


class TwilioWebhookRequest(BaseModel):
    """Simulates the payload Twilio sends on an incoming call."""
    CallSid: str
    From: str
    To: str
    CallStatus: str = "ringing"
    SpeechResult: Optional[str] = None
    Confidence: Optional[float] = None


class TranscriptRequest(BaseModel):
    session_id: str
    transcript: str
    confidence: Optional[float] = 1.0


class AgentResponse(BaseModel):
    session_id: str
    text_response: str
    audio_url: Optional[str] = None
    state: AgentState
    booking_confirmed: bool = False
    handoff_triggered: bool = False


class BookingRequest(BaseModel):
    session_id: str
    caller_phone: str
    preferred_date: str
    preferred_time: str
    reason: Optional[str] = "General appointment"


class BookingResponse(BaseModel):
    success: bool
    booking_id: Optional[str] = None
    confirmed_slot: Optional[str] = None
    message: str


class CRMRecord(BaseModel):
    phone: str
    name: str
    email: Optional[str] = None
    last_appointment: Optional[str] = None
    notes: Optional[str] = None


class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class SessionContext(BaseModel):
    session_id: str
    caller_phone: str
    state: AgentState = AgentState.receive_call
    history: List[ConversationTurn] = Field(default_factory=list)
    collected_info: dict = Field(default_factory=dict)
    booking_id: Optional[str] = None
    handoff_triggered: bool = False
