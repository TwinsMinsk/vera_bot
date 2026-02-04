import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import load_config
from app.handlers import commands, messages, voice, photos
from app.services.memory import MemoryService
from app.services.llm import LLMService
from app.services.voice import VoiceService
from app.services.search import SearchService
from app.services.notes import NotesService
from app.middlewares.auth import WhitelistMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Установить меню команд бота."""
    commands_list = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="📚 Справка о командах"),
        BotCommand(command="clear", description="🧹 Очистить историю"),
        BotCommand(command="mode", description="🎭 Выбрать режим ИИ"),
        BotCommand(command="think", description="🧠 Режим глубокого мышления"),
        BotCommand(command="image", description="🎨 Сгенерировать картинку"),
        BotCommand(command="note", description="📝 Создать заметку"),
        BotCommand(command="notes", description="📋 Показать заметки"),
        BotCommand(command="delnote", description="🗑 Удалить заметку"),
        BotCommand(command="translate", description="🌍 Перевести текст"),
    ]
    await bot.set_my_commands(commands_list)


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
    voice_service = VoiceService(config.voice)
    search_service = SearchService(config.search)
    notes_service = NotesService(memory_service._redis)

    # Initialize Bot
    bot = Bot(
        token=config.bot.token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Set bot commands menu
    await set_bot_commands(bot)
    logger.info("Bot commands menu set successfully")
    
    # Initialize Dispatcher
    dp = Dispatcher()
    
    # Register Middleware
    dp.message.middleware(WhitelistMiddleware(config.bot.admin_ids))
    
    # Register Routers (order matters: commands first, then specific, then catch-all)
    dp.include_router(commands.router)
    dp.include_router(photos.router)
    dp.include_router(voice.router)
    dp.include_router(messages.router)  # catch-all for text should be last
    
    # Start polling with dependency injection
    logger.info("Starting bot...")
    try:
        await dp.start_polling(
            bot, 
            memory_service=memory_service,
            llm_service=llm_service,
            voice_service=voice_service,
            search_service=search_service,
            notes_service=notes_service,
            config=config
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
