from aiogram import Router, types, F
from app.services.memory import MemoryService
from app.services.llm import LLMService

router = Router()

@router.message(F.text)
async def handle_text(message: types.Message, memory_service: MemoryService, llm_service: LLMService):
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_text = message.text

    # 1. Add user message to history
    await memory_service.add_message(user_id, {"role": "user", "content": user_text})

    # 2. Get history
    history = await memory_service.get_history(user_id)

    # 3. Generate response
    # Send "typing" action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    response_text = await llm_service.generate_response(history)

    # 4. Add assistant message to history
    await memory_service.add_message(user_id, {"role": "assistant", "content": response_text})

    # 5. Send response
    await message.answer(response_text)
