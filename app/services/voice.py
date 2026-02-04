import logging
import os
from typing import BinaryIO
from openai import AsyncOpenAI

from config import LLMConfig

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self, config: LLMConfig):
        # Whisper might need a different base_url if using Groq, 
        # but for now we assume OpenRouter or standard OpenAI compatible endpoint
        # If OpenRouter doesn't support audio, user might need to change base_url
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = "whisper-1" # Or appropriate model name for the provider

    async def transcribe(self, audio_file: BinaryIO) -> str:
        """Transcribe audio file to text."""
        try:
            transcript = await self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                response_format="text"
            )
            return transcript
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return ""
