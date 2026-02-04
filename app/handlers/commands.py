from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

# Import services (will be injected or instantiated)
from app.services.memory import MemoryService
from config import load_config

router = Router()

# We need a way to access services. 
# 1. Dependency Injection (middlewares) - Best practice
# 2. Global instances - Easier for small scripts
# For structurizartion, we can assume they are passed in bot.py -> dp.workflow_data
# But for now, let's instantiate them or get them from context if middleware is set up.
# Let's assume middleware injects 'memory_service', 'llm_service', 'config'

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я твой личный помощник. Чем могу помочь?")

@router.message(Command("clear"))
async def cmd_clear(message: types.Message, memory_service: MemoryService):
    if not message.from_user:
        return
        
    await memory_service.clear_history(message.from_user.id)
    await message.answer("История диалога очищена! Начинаем с чистого листа. 🧹")
