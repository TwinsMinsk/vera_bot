from aiogram import Router, types, F, Bot
from app.services.memory import MemoryService
from app.services.llm import LLMService
from app.services.search import SearchService
from app.utils.text import format_text_html

router = Router()

@router.message(F.text)
async def handle_text(message: types.Message, memory_service: MemoryService, llm_service: LLMService, search_service: SearchService):
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_text = message.text

    # 1. Add user message to history
    await memory_service.add_message(user_id, {"role": "user", "content": user_text})

    # 2. Get history
    history = await memory_service.get_history(user_id)

    # 3. Generate response
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # --- Search Logic ---
    # Check if we need internet
    if search_service.needs_search(user_text):
        await message.bot.send_chat_action(chat_id=message.chat.id, action="find_location") # Fun visual fallback
        search_results = await search_service.search(user_text)
        if search_results:
            # Inject into history merely for this generation? 
            # Or append to System prompt? 
            # Appending to history as a System message specific to this turn is cleaner.
            # But history usually assumes sequential roles.
            # Standard pattern: Add an ephemeral system message or inject into last user message.
            # Let's inject into last user message context.
            context_msg = f"\n\n[Context from Internet Search]:\n{search_results}"
            
            # We already added user message. Let's update the last item in 'history' list locally?
            # Or better: construct a transient "System Context" message.
            system_context = {"role": "system", "content": f"Use this internet info if relevant:\n{search_results}"}
            # Insert before last user message? Or at the end?
            # LLM usually treats list sequentially.
            history.insert(-1, system_context) 
            # Wait, history last item is User. Inserting -1 puts it BEFORE user. Correct.
    # --------------------

    response_text = await llm_service.generate_response(history)

    # 4. Add assistant message to history (store RAW markdown logic if needed, but usually store raw)
    await memory_service.add_message(user_id, {"role": "assistant", "content": response_text})

    # 5. Format and Send response
    formatted_text = format_text_html(response_text)
    
    try:
        await message.answer(formatted_text, parse_mode="HTML")
    except Exception:
        # Fallback if HTML parsing fails (e.g. unclosed tags)
        await message.answer(response_text)  # fallback to default/None parse mode
