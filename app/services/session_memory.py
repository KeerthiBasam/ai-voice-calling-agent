"""
Session memory backed by Redis.
Stores conversation history and booking state per call session.
Falls back to in-memory dict when Redis is not available (useful for quick testing).
"""

import json
import logging
from typing import Optional
from app.config import settings
from app.models.schemas import SessionContext, AgentState, ConversationTurn

logger = logging.getLogger(__name__)

# In-memory fallback (used when Redis is unavailable)
_memory_store: dict = {}


def _get_redis():
      """Return a Redis client, or None if Redis is not available."""
      try:
                import redis
                client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
                client.ping()
                return client
except Exception as e:
        logger.warning(f"Redis not available, using in-memory store: {e}")
        return None


def save_session(context: SessionContext) -> None:
      """Persist the full session context."""
      data = context.model_dump_json()
      r = _get_redis()
      if r:
                r.setex(f"session:{context.session_id}", settings.SESSION_TTL_SECONDS, data)
else:
        _memory_store[context.session_id] = data


def load_session(session_id: str) -> Optional[SessionContext]:
      """Load session context by ID. Returns None if not found."""
      r = _get_redis()
      if r:
                raw = r.get(f"session:{session_id}")
else:
        raw = _memory_store.get(session_id)

    if not raw:
              return None

    try:
              return SessionContext.model_validate_json(raw)
except Exception as e:
          logger.error(f"Failed to deserialize session {session_id}: {e}")
          return None


def get_or_create_session(session_id: str, caller_phone: str) -> SessionContext:
      """Load existing session or create a fresh one."""
      existing = load_session(session_id)
      if existing:
                return existing
            new_session = SessionContext(session_id=session_id, caller_phone=caller_phone)
    save_session(new_session)
    return new_session


def append_turn(session_id: str, role: str, content: str) -> None:
      """Add a single conversation turn to the session history."""
    ctx = load_session(session_id)
    if ctx:
              ctx.history.append(ConversationTurn(role=role, content=content))
              save_session(ctx)


def update_state(session_id: str, state: AgentState) -> None:
      """Update the current state in the session."""
    ctx = load_session(session_id)
    if ctx:
              ctx.state = state
              save_session(ctx)


def update_collected_info(session_id: str, info: dict) -> None:
      """Merge new collected info into the session."""
    ctx = load_session(session_id)
    if ctx:
              ctx.collected_info.update(info)
              save_session(ctx)


def delete_session(session_id: str) -> None:
      """Clean up session after call ends."""
    r = _get_redis()
    if r:
              r.delete(f"session:{session_id}")
else:
        _memory_store.pop(session_id, None)
  
