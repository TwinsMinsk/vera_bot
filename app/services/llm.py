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
        self._image_model = config.image_model
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

    async def generate_response(self, history: List[Dict[str, str]], mode: str = "cute") -> str:
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

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=self._model,
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

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Generate image using image model (e.g. Flux)."""
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            # Note: For many image models, we don't need modalities if using chat endpoint proxy
            # but some providers might need it. Let's try without first as it's more standard for dedicated models.
            response = await self._client.chat.completions.create(
                model=self._image_model,
                messages=messages,
                extra_headers=self._headers
            )
            
            # 1. Check message object directly for image data
            msg = response.choices[0].message
            
            # Case from some OpenRouter providers: msg.image_url or msg.image
            if hasattr(msg, 'image'):
                return base64.b64decode(msg.image)
            
            # 2. Check content for base64 or URL
            content = msg.content
            if not content:
                # Some providers return it in choice['image_url'] or similar
                # But OpenAI SDK might not parse it into choice.message.content
                raw_choice = response.choices[0].model_dump()
                if 'image_url' in raw_choice:
                    url = raw_choice['image_url']
                    return await self._download_image(url)
                logger.error(f"Empty content from image model. Raw response: {response}")
                return None

            # Content is base64?
            if "data:image" in content and "base64," in content:
                base64_data = content.split("base64,")[1].split('"')[0].split("'")[0]
                return base64.b64decode(base64_data)
            
            # Content is a direct URL?
            if content.startswith("http"):
                # Clean URL (sometimes it's in markdown or has quotes)
                url = content.strip().strip('"').strip("'")
                if "(" in url and ")" in url: # Markdown [link](url)
                    url = url.split("(")[1].split(")")[0]
                return await self._download_image(url)
            
            logger.warning(f"Could not find image in response content: {content[:100]}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return None

    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL."""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                if response.status_code == 200:
                    return response.content
                logger.error(f"Failed to download image from {url}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
        return None

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
