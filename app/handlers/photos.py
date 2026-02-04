import os
import base64
import html
from aiogram import Router, types, Bot, F
from app.services.memory import MemoryService
from app.services.llm import LLMService
from app.utils.text import format_text_html

router = Router()


@router.message(F.photo)
async def handle_photo(
    message: types.Message, 
    bot: Bot, 
    memory_service: MemoryService, 
    llm_service: LLMService
):
    """Обработчик фотографий для Vision анализа."""
    if not message.from_user or not message.photo:
        return

    user_id = message.from_user.id
    caption = message.caption or ""

    # Получаем фото в максимальном разрешении (последний элемент)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    # Скачиваем в память
    file_data = await bot.download_file(file.file_path)
    image_bytes = file_data.read()
    
    # Конвертируем в base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Анализируем изображение
    analysis = await llm_service.analyze_image(image_base64, caption)

    # Добавляем в историю
    user_msg = f"[Фото]" + (f": {caption}" if caption else "")
    await memory_service.add_message(user_id, {"role": "user", "content": user_msg})
    await memory_service.add_message(user_id, {"role": "assistant", "content": analysis})

    # Форматируем и отправляем
    formatted = format_text_html(analysis)
    
    try:
        await message.answer(f"🖼 <b>Анализ изображения:</b>\n\n{formatted}", parse_mode="HTML")
    except Exception:
        await message.answer(f"🖼 Анализ изображения:\n\n{analysis}")
