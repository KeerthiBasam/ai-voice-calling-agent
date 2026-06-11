"""
Mock appointment scheduling tools.
These simulate checking availability and booking appointments
against a simple JSON file store (data/appointments.json).
"""

import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the mock data store
DATA_FILE = Path("data/appointments.json")

# Predefined available slots (simulates a real calendar API)
AVAILABLE_SLOTS = [
      "tomorrow 9:00 AM",
      "tomorrow 11:00 AM",
      "tomorrow 2:00 PM",
      "tomorrow 4:30 PM",
      "day after tomorrow 10:00 AM",
      "day after tomorrow 3:00 PM",
]


def _load_appointments() -> list:
      """Load appointments from the JSON file store."""
      if not DATA_FILE.exists():
                DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
                DATA_FILE.write_text(json.dumps([]))
                return []
            try:
                      return json.loads(DATA_FILE.read_text())
except Exception:
        return []


def _save_appointments(appointments: list) -> None:
      """Persist appointments to the JSON file store."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(appointments, indent=2))


def check_availability(preferred_date: str, preferred_time: str) -> dict:
      """
          Tool: Check if a slot is available.
              Returns availability status and alternative slots.
                  """
    query = f"{preferred_date.lower()} {preferred_time.lower()}"

    # Check if requested slot matches any available slot
    is_available = any(query in slot.lower() or preferred_time.lower() in slot.lower()
                                              for slot in AVAILABLE_SLOTS)

    # Filter available slots to suggest
    suggestions = [
              slot for slot in AVAILABLE_SLOTS
              if preferred_date.lower() in slot.lower()
    ] or AVAILABLE_SLOTS[:3]

    logger.info(f"[SCHEDULER] Availability check: date='{preferred_date}' time='{preferred_time}' available={is_available}")

    return {
              "available": is_available,
              "requested_slot": f"{preferred_date} {preferred_time}",
              "available_slots": suggestions,
    }


def book_appointment(
      caller_phone: str,
      preferred_date: str,
      preferred_time: str,
      reason: str = "General appointment",
      name: Optional[str] = None,
) -> dict:
      """
          Tool: Book an appointment and persist it to the JSON store.
              Returns booking confirmation with a booking ID.
                  """
    availability = check_availability(preferred_date, preferred_time)

    if not availability["available"]:
              return {
                            "success": False,
                            "booking_id": None,
                            "confirmed_slot": None,
                            "message": f"Sorry, {preferred_date} at {preferred_time} is not available. Try one of: {', '.join(availability['available_slots'])}",
              }

    booking_id = f"BK-{uuid.uuid4().hex[:8].upper()}"
    confirmed_slot = f"{preferred_date} at {preferred_time}"

    record = {
              "booking_id": booking_id,
              "phone": caller_phone,
              "name": name or "Unknown",
              "slot": confirmed_slot,
              "reason": reason,
              "booked_at": datetime.utcnow().isoformat(),
    }

    appointments = _load_appointments()
    appointments.append(record)
    _save_appointments(appointments)

    logger.info(f"[SCHEDULER] Booked: {booking_id} for {caller_phone} at {confirmed_slot}")

    return {
              "success": True,
              "booking_id": booking_id,
              "confirmed_slot": confirmed_slot,
              "message": f"Appointment confirmed for {confirmed_slot}. Your booking ID is {booking_id}.",
    }


def get_available_slots() -> list:
      """Tool: Return the current list of all available time slots."""
    return AVAILABLE_SLOTS
