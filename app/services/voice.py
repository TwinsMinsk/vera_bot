import logging
import os
import subprocess
from typing import BinaryIO
from openai import AsyncOpenAI

from config import VoiceConfig

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self, config: VoiceConfig):
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = config.model

    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text using Groq.
        Converts .ogg to .mp3 using ffmpeg first if needed.
        """
        mp3_path = audio_path.replace(".ogg", ".mp3")
        
        try:
            # 1. Convert OGG to MP3 using ffmpeg
            # Groq supports: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm.
            # But documentation often recommends standard formats. 
            # If input is .ogg (Telegram voice), let's ensure it's standard Opus/Vorbis.
            # Usually simple conversion ensures compatibility.
            
            # -y : overwrite output
            # -i : input
            # -vn : no video
            # -acodec libmp3lame : force mp3
            process = subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path, "-vn", "-acodec", "libmp3lame", "-q:a", "4", mp3_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if process.returncode != 0:
                logger.error(f"FFmpeg conversion failed: {process.stderr.decode()}")
                # Try sending original file as fallback
                mp3_path = audio_path
            
            # 2. Transcribe
            with open(mp3_path, "rb") as audio_file:
                transcript = await self._client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                    response_format="text"
                )
            
            return transcript

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return ""
        finally:
            # Cleanup mp3 file if it was created and is different from input
            if mp3_path != audio_path and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except:
                    pass
