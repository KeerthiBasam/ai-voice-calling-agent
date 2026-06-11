"""
Configuration settings for the AI Voice Calling Agent.
Loads from environment variables with sensible defaults for local development.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
      # App
      APP_NAME: str = "AI Voice Calling Agent"
      DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
      HOST: str = os.getenv("HOST", "0.0.0.0")
      PORT: int = int(os.getenv("PORT", "8000"))

    # OpenAI
      OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
      OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # ElevenLabs TTS
      ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
      ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    # Twilio
      TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
      TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
      TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Redis
      REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
      SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

    # Agent behavior
      AGENT_NAME: str = os.getenv("AGENT_NAME", "Aria")
      CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))

    # Mock mode — set to true to skip real API calls (great for local dev)
      MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"


settings = Settings()
