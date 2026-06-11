"""
Mock CRM tools.
Lookup customer records by phone number from a local JSON store.
In a real system this would call a CRM API (Salesforce, HubSpot, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Optional
from app.models.schemas import CRMRecord

logger = logging.getLogger(__name__)

CRM_FILE = Path("data/crm.json")

# Seed data — simulates existing customer records
DEFAULT_CRM_DATA = [
      {
                "phone": "+15550001111",
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "last_appointment": "2026-05-10",
                "notes": "Prefers morning appointments",
      },
      {
                "phone": "+15550002222",
                "name": "Bob Smith",
                "email": "bob@example.com",
                "last_appointment": "2026-04-22",
                "notes": "Returning customer",
      },
      {
                "phone": "+15550003333",
                "name": "Carol White",
                "email": "carol@example.com",
                "last_appointment": None,
                "notes": "New customer",
      },
]


def _load_crm() -> list:
      """Load CRM records. Seeds defaults on first run."""
      if not CRM_FILE.exists():
                CRM_FILE.parent.mkdir(parents=True, exist_ok=True)
                CRM_FILE.write_text(json.dumps(DEFAULT_CRM_DATA, indent=2))
                return DEFAULT_CRM_DATA
            try:
                      return json.loads(CRM_FILE.read_text())
except Exception:
        return DEFAULT_CRM_DATA


def lookup_customer_by_phone(phone: str) -> Optional[CRMRecord]:
      """
          Tool: Look up a customer by their phone number.
              Returns a CRMRecord or None if not found.
                  """
    records = _load_crm()
    # Normalize phone for comparison
    normalized = phone.strip().replace(" ", "")
    for record in records:
              if record["phone"].replace(" ", "") == normalized:
                            logger.info(f"[CRM] Found customer: {record['name']} for phone {phone}")
                            return CRMRecord(**record)

          logger.info(f"[CRM] No record found for phone {phone}")
    return None


def get_customer_context(phone: str) -> str:
      """
          Returns a short text summary of the customer for the LLM prompt context.
              Used to personalize the agent's greeting.
                  """
    record = lookup_customer_by_phone(phone)
    if not record:
              return "New caller. No prior appointment history."

    context = f"Caller name: {record.name}."
    if record.last_appointment:
              context += f" Last appointment: {record.last_appointment}."
          if record.notes:
                    context += f" Notes: {record.notes}."
                return context
