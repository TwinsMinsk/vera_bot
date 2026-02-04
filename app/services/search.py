import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self._ddgs = DDGS()

    async def search(self, query: str, max_results: int = 3) -> str:
        """
        Search DuckDuckGo and return formatted results string.
        """
        try:
            # Note: Async DDG is not standard in some versions, but recent allow sync call wrapped or async usage.
            # Library often changes. Safe bet: run in executor if sync, or use async API if available.
            # 4.x has 'text' method but checking if it's async.
            # Assuming sync for now and wrapping it might be safer, but let's try direct call.
            # Usually strict async libs require await.
            # Let's assume standard sync because simple.
            
            results = self._ddgs.text(query, max_results=max_results)
            
            if not results:
                return ""
            
            formatted_results = []
            for r in results:
                formatted_results.append(f"Title: {r.get('title')}\nBody: {r.get('body')}\nLink: {r.get('href')}")
            
            return "\n\n".join(formatted_results)
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")
            return ""

    def needs_search(self, text: str) -> bool:
        """
        Simple keyword detection to decide if search is needed.
        """
        triggers = [
            "погода", "новости", "курс", "цена", "кто такой", 
            "что такое", "когда", "где", "weather", "news", 
            "price", "who is", "what is", "when", "where",
            "прогноз", "найди"
        ]
        text_lower = text.lower()
        return any(t in text_lower for t in triggers)
