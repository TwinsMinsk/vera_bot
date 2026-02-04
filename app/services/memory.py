import json
import logging
from typing import List, Dict, Optional
import redis.asyncio as redis

from config import RedisConfig

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, config: RedisConfig):
        self._redis = redis.from_url(config.url, decode_responses=True)
        self._ttl = 86400  # 24 hours

    async def add_message(self, user_id: int, message: Dict[str, str]):
        """Add a message to the user's chat history."""
        key = f"chat_history:{user_id}"
        try:
            await self._redis.rpush(key, json.dumps(message))
            # Build-in logic: keep only last 20 messages
            list_len = await self._redis.llen(key)
            if list_len > 20:
                await self._redis.lpop(key)
            
            # Reset TTL
            await self._redis.expire(key, self._ttl)
        except Exception as e:
            logger.error(f"Error adding message to Redis: {e}")

    async def get_history(self, user_id: int, limit: int = 5) -> List[Dict[str, str]]:
        """Get the last N messages from the user's chat history."""
        key = f"chat_history:{user_id}"
        try:
            # Get all messages first to check length, or just get slice
            # lrange parameters are start, end (inclusive)
            # To get last N: start = -N, end = -1
            raw_messages = await self._redis.lrange(key, -limit, -1)
            messages = [json.loads(msg) for msg in raw_messages]
            return messages
        except Exception as e:
            logger.error(f"Error getting history from Redis: {e}")
            return []

    async def clear_history(self, user_id: int):
        """Clear the user's chat history."""
        key = f"chat_history:{user_id}"
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Error clearing history in Redis: {e}")

    async def close(self):
        await self._redis.aclose()
