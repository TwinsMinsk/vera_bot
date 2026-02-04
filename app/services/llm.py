import logging
import base64
from typing import List, Dict, Optional
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
        self._vision_model = config.vision_model
        self._thinker_model = config.thinker_model
        self._system_prompt_path = config.system_prompt_path
        self._system_prompt = self._load_system_prompt()
        self._headers = {
            "HTTP-Referer": "https://verabot.local",
            "X-Title": "VeraBot"
        }

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

        return base_prompt


    async def generate_response(self, history: List[Dict[str, str]], mode: str = "cute", model_override: Optional[str] = None) -> str:
        """Generate response from LLM based on history."""
        
        # Adjust system prompt based on mode
        system_prompt = self._system_prompt
        if mode == "pro":
            system_prompt = (
                "Ты — строгий, профессиональный ассистент. "
                "Отвечай кратко, фактами, без эмодзи и ласкательных слов. "
                "Будь точным и информативным."
            )
        
        messages = [{"role": "system", "content": system_prompt}] + history
        
        # Determine model to use
        model_to_use = model_override if model_override else self._model

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                extra_headers=self._headers
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating response from LLM: {e}")
            return "Извини, произошла ошибка при обращении к моему мозгу..."

    async def generate_response_r1(self, question: str) -> str:
        """Generate response using DeepSeek R1 (thinker model)."""
        messages = [
            {"role": "system", "content": "Ты — умный помощник. Думай шаг за шагом."},
            {"role": "user", "content": question}
        ]

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=self._thinker_model,
                messages=messages,
                extra_headers=self._headers
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error with R1 model: {e}")
            return "Не удалось обработать запрос в режиме мышления..."

    async def analyze_image(self, image_base64: str, caption: str = "") -> str:
        """Analyze image using Vision model."""
        user_prompt = caption if caption else "Опиши это изображение подробно."
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]
            }
        ]

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=self._vision_model,
                messages=messages,
                extra_headers=self._headers
            )
            return response.choices[0].message.content or "Не удалось проанализировать изображение."
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return "Произошла ошибка при анализе изображения..."

    async def translate(self, text: str) -> str:
        """Translate text to Russian (or to English if Russian)."""
        # Detect language and translate
        messages = [
            {
                "role": "system", 
                "content": (
                    "Ты — переводчик. Определи язык текста. "
                    "Если текст на русском — переведи на английский. "
                    "Если на другом языке — переведи на русский. "
                    "Отвечай ТОЛЬКО переводом, без пояснений."
                )
            },
            {"role": "user", "content": text}
        ]

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                extra_headers=self._headers
            )
            return response.choices[0].message.content or text
        except Exception as e:
            logger.error(f"Error translating: {e}")
            return "Ошибка перевода..."
