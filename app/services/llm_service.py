"""
LLM service: generates agent responses using OpenAI chat completions.
In mock mode, returns scripted responses for local testing.
"""

import logging
from typing import List, Dict
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are {agent_name}, a friendly AI scheduling assistant making an outbound call.
Your goal is to help the caller book an appointment.

Guidelines:
- Be concise and conversational (this is a phone call, not a chat)
- Ask one question at a time
- Confirm booking details before finalizing
- If the user is confused or requests a human, acknowledge and offer to transfer
- Keep responses under 3 sentences unless collecting multiple details

Current context: {context}
"""


async def generate_response(
      history: List[Dict[str, str]],
      context: str,
      session_id: str,
) -> str:
      """
          Generate a conversational agent response.
              history: list of {"role": "user"|"assistant", "content": "..."}
                  context: brief summary of booking state / collected info
                      """
      if settings.MOCK_MODE:
                return _mock_response(history)

      try:
                from openai import AsyncOpenAI

          client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        system_content = SYSTEM_PROMPT.format(
                      agent_name=settings.AGENT_NAME,
                      context=context,
        )
        messages = [{"role": "system", "content": system_content}] + history

        completion = await client.chat.completions.create(
                      model=settings.OPENAI_MODEL,
                      messages=messages,
                      temperature=0.7,
                      max_tokens=200,
        )
        response = completion.choices[0].message.content.strip()
        logger.info(f"[LLM] session={session_id} response='{response[:80]}'")
        return response

except Exception as e:
        logger.error(f"LLM error for session {session_id}: {e}")
        return "I'm sorry, I'm having a little trouble right now. Could you repeat that?"


def _mock_response(history: List[Dict[str, str]]) -> str:
      """Rule-based mock responses for testing without an OpenAI key."""
    last_user_msg = ""
    for turn in reversed(history):
              if turn["role"] == "user":
                            last_user_msg = turn["content"].lower()
                            break

          if not history:
                    return "Hi there! This is Aria calling to help schedule your appointment. What day works best for you?"
                if "tomorrow" in last_user_msg or "afternoon" in last_user_msg:
                          return "Got it! I have an opening tomorrow at 2:00 PM and another at 4:30 PM. Which works better for you?"
                      if "2" in last_user_msg or "two" in last_user_msg:
                                return "Perfect, I'll book you in for tomorrow at 2:00 PM. Can I get your name to confirm the appointment?"
                            if "cancel" in last_user_msg:
                                      return "No problem, I won't make any changes. Is there anything else I can help you with?"
                                  if "human" in last_user_msg or "agent" in last_user_msg or "transfer" in last_user_msg:
                                            return "Of course! Let me transfer you to one of our team members right away."
                                        return "Could you tell me a bit more about what you're looking for? I want to make sure I find the right slot for you."
