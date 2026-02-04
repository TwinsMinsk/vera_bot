import logging
import datetime
from tavily import TavilyClient
from config import SearchConfig

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, config: SearchConfig):
        # Handle empty key gracefully if needed, or fail fast
        self._client = TavilyClient(api_key=config.api_key) if config.api_key else None
        self._enabled = bool(config.api_key)

    async def search(self, query: str, max_results: int = 3) -> str:
        """
        Search Tavily and return context string.
        Returns "SEARCH_FAILED" if error or no results.
        """
        if not self._enabled:
            return "SEARCH_FAILED"

        try:
            # OPTIMIZATION: Clean query
            # 1. Remove current year to avoid stale SEO results like "Weather 2024" if we are in 2026?
            # Or user means "don't include 2025 if today is 2026". 
            # Safe logic: Remove current year string.
            current_year = str(datetime.datetime.now().year)
            query = query.replace(current_year, "")
            
            # 2. Add 'current' for weather/news
            if "погода" in query.lower() or "weather" in query.lower():
                query += " current"

            # Tavily is sync by default (python sdk). 
            # For async, we should use run_in_executor or verify if they added async support.
            # Assuming sync:
            response = self._client.search(query=query, search_depth="basic", max_results=max_results)
            logger.info(f"DEBUG TAVILY RESPONSE: {response}")
            
            results = response.get("results", [])
            if not results:
                return "SEARCH_FAILED"
            
            content_list = []
            for r in results:
                title = r.get('title', 'Unknown')
                body = r.get('content', '') # Tavily usually returns 'content'
                url = r.get('url', '')
                content_list.append(f"Source: {title} ({url})\nContent: {body}")
            
            return "\n\n".join(content_list)
        except Exception as e:
            logger.error(f"Error searching Tavily: {e}")
            return "SEARCH_FAILED"

    def needs_search(self, text: str) -> bool:
        """
        Simple keyword detection to decide if search is needed.
        """
        triggers = [
            "погода", "новости", "курс", "цена", "кто такой", 
            "что такое", "когда", "где", "weather", "news", 
            "price", "who is", "what is", "when", "where",
            "прогноз", "найди", "факты о", "сколько стоит",
            "bitcoin", "usd", "euro", "рубль"
        ]
        text_lower = text.lower()
        return any(t in text_lower for t in triggers)
