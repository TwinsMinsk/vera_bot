import json
import logging
from typing import List, Dict, Optional
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class NotesService:
    """CRUD операции для заметок пользователя в Redis."""
    
    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    def _key(self, user_id: int) -> str:
        return f"notes:{user_id}"

    async def add_note(self, user_id: int, text: str) -> int:
        """Добавить заметку. Возвращает ID заметки."""
        key = self._key(user_id)
        
        # Получить текущий counter
        counter_key = f"notes_counter:{user_id}"
        note_id = await self._redis.incr(counter_key)
        
        note = {"id": note_id, "text": text}
        await self._redis.rpush(key, json.dumps(note, ensure_ascii=False))
        
        return note_id

    async def get_notes(self, user_id: int) -> List[Dict]:
        """Получить все заметки пользователя."""
        key = self._key(user_id)
        raw_notes = await self._redis.lrange(key, 0, -1)
        
        notes = []
        for raw in raw_notes:
            try:
                notes.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        
        return notes

    async def delete_note(self, user_id: int, note_id: int) -> bool:
        """Удалить заметку по ID. Возвращает True если удалена."""
        key = self._key(user_id)
        notes = await self.get_notes(user_id)
        
        # Найти и удалить
        for note in notes:
            if note.get("id") == note_id:
                await self._redis.lrem(key, 1, json.dumps(note, ensure_ascii=False))
                return True
        
        return False

    async def clear_notes(self, user_id: int) -> None:
        """Удалить все заметки пользователя."""
        key = self._key(user_id)
        counter_key = f"notes_counter:{user_id}"
        await self._redis.delete(key, counter_key)
