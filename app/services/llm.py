import logging
import os
from typing import List, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from config import LLMConfig

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, config: LLMConfig):
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = config.model
        self._system_prompt_path = config.system_prompt_path
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        base_prompt = "You are a helpful assistant."
        try:
            with open(self._system_prompt_path, 'r', encoding='utf-8') as f:
                base_prompt = f.read().strip()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found at {self._system_prompt_path}. Using default.")
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")

        # Anti-Hallucination Injection
        anti_hallucination_rule = (
            "\n\n[ANTI-HALLUCINATION PROTOCOL]\n"
            "If the context contains 'SEARCH_FAILED' or does NOT contain relevant internet info, "
            "and the user asks for real-time facts (weather, prices, news), "
            "you MUST ADMIT you do not know. "
            "Do NOT make up data. Check the context carefully.\n"
            "[FORCE ANSWER]\n"
            "If specific context regarding weather or news IS provided in the user message, "
            "YOU MUST USE IT to answer the user question directly. Do not apologize about being an AI."
        )
        return base_prompt + anti_hallucination_rule

    async def generate_response(self, history: List[Dict[str, str]]) -> str:
        """Generate response from LLM based on history."""
        
        messages = [{"role": "system", "content": self._system_prompt}] + history

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                extra_headers={
                    "HTTP-Referer": "https://verabot.local", # Replace with actual URL if hosted
                    "X-Title": "VeraBot"
                }
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating response from LLM: {e}")
            return "Извини, произошла ошибка при обращении к моему мозгу..."
