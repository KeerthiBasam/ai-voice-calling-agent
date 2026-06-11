"""
Basic tests for the AI Voice Calling Agent.
All tests run in MOCK_MODE so no real API keys are needed.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.tools.scheduler_tools import check_availability, book_appointment, get_available_slots
from app.tools.crm_tools import lookup_customer_by_phone, get_customer_context
from app.services.session_memory import get_or_create_session, load_session


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check():
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Scheduler tools
# ---------------------------------------------------------------------------

def test_check_availability_found():
      result = check_availability("tomorrow", "afternoon")
    assert "available" in result
    assert len(result["available_slots"]) > 0


def test_book_appointment_success():
      result = book_appointment(
          caller_phone="+15550001111",
          preferred_date="tomorrow",
          preferred_time="2:00 PM",
          name="Test User",
)
    assert result["success"] is True
    assert result["booking_id"] is not None
    assert "tomorrow" in result["confirmed_slot"]


def test_get_available_slots_returns_list():
      slots = get_available_slots()
    assert isinstance(slots, list)
    assert len(slots) > 0


# ---------------------------------------------------------------------------
# CRM tools
# ---------------------------------------------------------------------------

def test_crm_lookup_existing_customer():
      record = lookup_customer_by_phone("+15550001111")
    assert record is not None
    assert record.name == "Alice Johnson"


def test_crm_lookup_unknown_number():
      record = lookup_customer_by_phone("+19999999999")
    assert record is None


def test_get_customer_context_known():
      ctx = get_customer_context("+15550001111")
    assert "Alice" in ctx


def test_get_customer_context_unknown():
      ctx = get_customer_context("+10000000000")
    assert "New caller" in ctx


# ---------------------------------------------------------------------------
# Session memory
# ---------------------------------------------------------------------------

def test_session_create_and_load():
      session = get_or_create_session("test-session-123", "+15550001111")
    assert session.session_id == "test-session-123"
    loaded = load_session("test-session-123")
    assert loaded is not None
    assert loaded.caller_phone == "+15550001111"


# ---------------------------------------------------------------------------
# API endpoints (mock mode)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_transcript_endpoint():
      # First create a session
      get_or_create_session("api-test-session", "+15550001111")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
              response = await client.post("/agent/process", json={
                            "session_id": "api-test-session",
                            "transcript": "I want to book an appointment tomorrow afternoon",
                            "confidence": 0.95,
              })
          assert response.status_code == 200
    data = response.json()
    assert "text_response" in data
    assert data["text_response"] != ""


@pytest.mark.asyncio
async def test_booking_endpoint():
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/booking", json={
                              "session_id": "booking-test",
                              "caller_phone": "+15550002222",
                              "preferred_date": "tomorrow",
                              "preferred_time": "2:00 PM",
                              "reason": "Checkup",
                })
            assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_available_slots_endpoint():
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/booking/slots")
            assert response.status_code == 200
    assert "available_slots" in response.json()
