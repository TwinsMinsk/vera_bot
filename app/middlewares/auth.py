from typing import Callable, Dict, Any, Awaitable, List
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: List[int]):
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            if user and user.id not in self.admin_ids:
                await event.answer("Я работаю только для своей хозяйки 💅")
                return
        
        return await handler(event, data)
