import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import load_config
from app.handlers import commands, messages, voice
from app.services.memory import MemoryService
from app.services.llm import LLMService
from app.services.voice import VoiceService
from app.middlewares.auth import WhitelistMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Load config
    try:
        config = load_config()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Initialize Services
    memory_service = MemoryService(config.redis)
    llm_service = LLMService(config.llm)
    from app.services.search import SearchService
    voice_service = VoiceService(config.voice)
    search_service = SearchService(config.search)

    # Initialize Bot
    bot = Bot(
        token=config.bot.token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize Dispatcher
    dp = Dispatcher()
    
    # Register Middleware
    dp.message.middleware(WhitelistMiddleware(config.bot.admin_ids))
    
    # Register Routers
    dp.include_router(commands.router)
    dp.include_router(voice.router)
    dp.include_router(messages.router)
    
    # Start polling with dependency injection
    logger.info("Starting bot...")
    try:
        await dp.start_polling(
            bot, 
            memory_service=memory_service,
            llm_service=llm_service,
            voice_service=voice_service,
            search_service=search_service,
            config=config # Optional but good to have
        )
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        await bot.session.close()
        await memory_service.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
