"""
Text-to-Speech service.
In mock mode, returns a placeholder audio URL.
In real mode, calls the ElevenLabs API to synthesize speech.
"""

import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def synthesize_speech(text: str, session_id: str) -> str:
      """
          Convert text to speech audio.
              Returns a URL or base64 audio string.
                  In mock mode returns a placeholder URL.
                      """
      if settings.MOCK_MODE:
                logger.info(f"[MOCK TTS] session={session_id} text='{text[:60]}...'")
                # Return a placeholder URL — in production this would point to hosted audio
                return "https://mock-tts-audio.example.com/audio.mp3"

      # Real ElevenLabs TTS call
      try:
                import httpx

          url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}"
        headers = {
                      "xi-api-key": settings.ELEVENLABS_API_KEY,
                      "Content-Type": "application/json",
        }
        payload = {
                      "text": text,
                      "model_id": "eleven_monolingual_v1",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
                      response = await client.post(url, json=payload, headers=headers)
                      response.raise_for_status()

        # Return audio bytes as base64 (you'd normally store to S3 or stream)
        import base64
        audio_b64 = base64.b64encode(response.content).decode("utf-8")
        logger.info(f"[TTS] session={session_id} audio generated ({len(response.content)} bytes)")
        return f"data:audio/mpeg;base64,{audio_b64}"

except Exception as e:
        logger.error(f"TTS error for session {session_id}: {e}")
        return ""
