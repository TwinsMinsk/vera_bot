import os
from typing import List
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass
class BotConfig:
    token: str
    admin_ids: List[int]

@dataclass
class RedisConfig:
    url: str

@dataclass
class LLMConfig:
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "deepseek/deepseek-chat"
    vision_model: str = "google/gemini-2.0-flash-lite-preview-02-05"
    thinker_model: str = "deepseek/deepseek-r1"
    image_model: str = "black-forest-labs/flux-schnell"
    system_prompt_path: str = "persona_prompt.md"

@dataclass
class VoiceConfig:
    api_key: str
    model: str = "whisper-large-v3-turbo"

@dataclass
class SearchConfig:
    api_key: str

@dataclass
class Config:
    bot: BotConfig
    redis: RedisConfig
    llm: LLMConfig
    voice: VoiceConfig
    search: SearchConfig

def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set")

    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = [int(id_str) for id_str in admin_ids_str.split(",") if id_str.strip()]

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        raise ValueError("OPENROUTER_API_KEY is not set")
        
    groq_key = os.getenv("GROQ_API_KEY") # Optional check removed to avoid logic conflict if user wants incomplete config locally
    
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    # Strict check if we want to enforce it
    # if not tavily_key: raise ValueError("TAVILY_API_KEY is not set")
        
    return Config(
        bot=BotConfig(token=bot_token, admin_ids=admin_ids),
        redis=RedisConfig(url=redis_url),
        llm=LLMConfig(api_key=openrouter_key),
        voice=VoiceConfig(api_key=groq_key or ""),
        search=SearchConfig(api_key=tavily_key)
    )
