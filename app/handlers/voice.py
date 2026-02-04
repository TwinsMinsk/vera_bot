import os
from aiogram import Router, types, F, Bot
from app.services.memory import MemoryService
from app.services.llm import LLMService
from app.services.voice import VoiceService

router = Router()

@router.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot, memory_service: MemoryService, llm_service: LLMService, voice_service: VoiceService):
    if not message.from_user or not message.voice:
        return

    user_id = message.from_user.id
    file_id = message.voice.file_id

    # 1. Download voice file
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    # Save to temp file
    temp_file_name = f"data/voice_{user_id}_{message.message_id}.ogg"
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    await bot.download_file(file_path, temp_file_name)

    # 2. Transcribe
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing") # or record_voice/upload_voice
    
    with open(temp_file_name, "rb") as audio_file:
        transcribed_text = await voice_service.transcribe(audio_file)

    # Delete temp file
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)

    if not transcribed_text:
        await message.answer("Не удалось распознать голосовое сообщение.")
        return

    # 3. Process as text
    # Add to history (User)
    await memory_service.add_message(user_id, {"role": "user", "content": transcribed_text})
    
    # Get history
    history = await memory_service.get_history(user_id)
    
    # Generate response
    response_text = await llm_service.generate_response(history)
    
    # Add to history (Assistant)
    await memory_service.add_message(user_id, {"role": "assistant", "content": response_text})
    
    # Send response
    await message.answer(f"🎤 <i>{transcribed_text}</i>\n\n{response_text}")
