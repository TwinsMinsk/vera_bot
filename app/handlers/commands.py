import re
import html
import base64
import logging
from aiogram import Router, types, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from app.services.memory import MemoryService
from app.services.llm import LLMService
from app.services.notes import NotesService

logger = logging.getLogger(__name__)

router = Router()


# ============ /start ============
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! 👋 Я твой личный помощник.\n\n"
        "Напиши мне что-нибудь или используй /help для списка команд!"
    )


# ============ /help ============
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
<b>📚 Доступные команды:</b>

<b>Основные:</b>
/start — Приветствие
/clear — Очистить историю диалога
/help — Эта справка

<b>🧠 Режимы ИИ:</b>
/mode — Выбрать режим общения
/think &lt;вопрос&gt; — Режим глубокого мышления
/setmodel — Выбрать модель ИИ

<b>🖼 Изображения:</b>
/image &lt;описание&gt; — Сгенерировать картинку
<i>Отправь фото — получишь описание</i>

<b>📝 Заметки:</b>
/note &lt;текст&gt; — Создать заметку
/notes — Показать все заметки
/delnote &lt;id&gt; — Удалить заметку

<b>🌍 Перевод:</b>
/translate &lt;текст&gt; — Перевести текст
"""
    await message.answer(help_text, parse_mode="HTML")


# ============ /clear ============
@router.message(Command("clear"))
async def cmd_clear(message: types.Message, memory_service: MemoryService):
    if not message.from_user:
        return
    await memory_service.clear_history(message.from_user.id)
    await message.answer("История диалога очищена! 🧹")


# ============ /mode ============
@router.message(Command("mode"))
async def cmd_mode(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🐰 Милый", callback_data="mode_cute"),
            InlineKeyboardButton(text="💼 Профи", callback_data="mode_pro"),
        ]
    ])
    await message.answer("Выбери режим общения:", reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith("mode_"))
async def callback_mode(callback: types.CallbackQuery, memory_service: MemoryService):
    if not callback.from_user or not callback.data:
        return
    
    mode = callback.data.replace("mode_", "")
    user_id = callback.from_user.id
    
    # Сохраняем режим в Redis
    key = f"user_mode:{user_id}"
    await memory_service._redis.set(key, mode)
    
    mode_names = {"cute": "🐰 Милый", "pro": "💼 Профи"}
    await callback.message.edit_text(f"Режим изменён на: {mode_names.get(mode, mode)}")
    await callback.answer()


# ============ /think ============
@router.message(Command("think"))
async def cmd_think(message: types.Message, llm_service: LLMService, memory_service: MemoryService):
    if not message.from_user or not message.text:
        return
    
    # Извлечь вопрос после /think
    question = message.text.replace("/think", "").strip()
    if not question:
        await message.answer("Напиши вопрос после /think\nПример: /think Почему небо голубое?")
        return
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Используем R1 для глубокого мышления
    response = await llm_service.generate_response_r1(question)
    
    # Форматируем ответ (R1 возвращает теги <think>)
    formatted = format_r1_response(response)
    
    try:
        await message.answer(formatted, parse_mode="HTML")
    except Exception:
        await message.answer(response)


def format_r1_response(text: str) -> str:
    """Форматирует ответ R1: <think> -> спойлер."""
    # Ищем <think>...</think>
    think_pattern = r"<think>(.*?)</think>"
    match = re.search(think_pattern, text, re.DOTALL)
    
    if match:
        think_content = match.group(1).strip()
        # Удаляем теги think из основного текста
        main_text = re.sub(think_pattern, "", text, flags=re.DOTALL).strip()
        
        # Безопасное экранирование
        safe_think = html.escape(think_content)[:1000]  # Ограничим размер
        safe_main = html.escape(main_text)
        
        return f"<tg-spoiler>💭 {safe_think}...</tg-spoiler>\n\n{safe_main}"
    
    return html.escape(text)


# ============ /note ============
@router.message(Command("note"))
async def cmd_note(message: types.Message, notes_service: NotesService):
    if not message.from_user or not message.text:
        return
    
    text = message.text.replace("/note", "").strip()
    if not text:
        await message.answer("Напиши текст заметки после /note")
        return
    
    note_id = await notes_service.add_note(message.from_user.id, text)
    await message.answer(f"✅ Заметка #{note_id} сохранена!")


# ============ /notes ============
@router.message(Command("notes"))
async def cmd_notes(message: types.Message, notes_service: NotesService):
    if not message.from_user:
        return
    
    notes = await notes_service.get_notes(message.from_user.id)
    
    if not notes:
        await message.answer("📭 У тебя нет заметок.\nСоздай: /note <текст>")
        return
    
    lines = ["<b>📝 Твои заметки:</b>\n"]
    for note in notes:
        safe_text = html.escape(note.get("text", ""))[:100]
        lines.append(f"<b>#{note.get('id')}</b>: {safe_text}")
    
    await message.answer("\n".join(lines), parse_mode="HTML")


# ============ /delnote ============
@router.message(Command("delnote"))
async def cmd_delnote(message: types.Message, notes_service: NotesService):
    if not message.from_user or not message.text:
        return
    
    try:
        note_id = int(message.text.replace("/delnote", "").strip())
    except ValueError:
        await message.answer("Укажи ID заметки: /delnote 1")
        return
    
    deleted = await notes_service.delete_note(message.from_user.id, note_id)
    
    if deleted:
        await message.answer(f"🗑 Заметка #{note_id} удалена!")
    else:
        await message.answer(f"Заметка #{note_id} не найдена")


# ============ /translate ============
@router.message(Command("translate"))
async def cmd_translate(message: types.Message, llm_service: LLMService):
    if not message.from_user or not message.text:
        return
    
    text = message.text.replace("/translate", "").strip()
    if not text:
        await message.answer("Напиши текст для перевода после /translate")
        return
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    translation = await llm_service.translate(text)
    await message.answer(f"🌍 <b>Перевод:</b>\n{html.escape(translation)}", parse_mode="HTML")


# ============ /setmodel ============
@router.message(Command("setmodel"))
async def cmd_setmodel(message: types.Message):
    # Список моделей для выбора
    models = {
        "DeepSeek Chat (V3)": "deepseek/deepseek-chat",
        "DeepSeek R1 (Thinker)": "deepseek/deepseek-r1",
        "Gemini 2.0 Flash Lite": "google/gemini-2.0-flash-lite-preview-02-05",
        "GPT-4o Mini": "openai/gpt-4o-mini",
        "Claude 3.5 Haiku": "anthropic/claude-3-5-haiku"
    }
    
    keyboard_buttons = []
    for name, model_id in models.items():
        # Используем короткий callback data, так как есть лимит 64 байта
        # Поэтому будем сохранять маппинг или использовать хэш, но пока просто передадим ID, 
        # надеясь что влезает.
        # OpenRouter ID длинные, поэтому лучше использовать short aliases
        pass

    # Упростим: используем алиасы в callback_data
    buttons = [
        [InlineKeyboardButton(text="🧠 DeepSeek V3", callback_data="model_deepseek/deepseek-chat")],
        [InlineKeyboardButton(text="🤔 DeepSeek R1", callback_data="model_deepseek/deepseek-r1")],
        [InlineKeyboardButton(text="⚡ Gemini 2.0 Flash Exp", callback_data="model_google/gemini-2.0-flash-exp:free")],
        [InlineKeyboardButton(text="🤖 GPT-4o Mini", callback_data="model_openai/gpt-4o-mini")],
        [InlineKeyboardButton(text="📝 Claude 3.5 Haiku", callback_data="model_anthropic/claude-3-5-haiku")],
        [InlineKeyboardButton(text="❌ Сбросить (по умолчанию)", callback_data="model_reset")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🛠 <b>Выберите языковую модель:</b>", reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(lambda c: c.data and c.data.startswith("model_"))
async def callback_setmodel(callback: types.CallbackQuery, memory_service: MemoryService):
    if not callback.from_user or not callback.data:
        return
    
    model = callback.data.replace("model_", "")
    user_id = callback.from_user.id
    key = f"user_model:{user_id}"

    if model == "reset":
        await memory_service._redis.delete(key)
        await callback.message.edit_text("🔄 Модель сброшена на стандартную (из конфига).")
    else:
        await memory_service._redis.set(key, model)
        await callback.message.edit_text(f"✅ Установлена модель:\n<code>{model}</code>", parse_mode="HTML")
    
    await callback.answer()
