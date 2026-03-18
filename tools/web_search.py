from duckduckgo_search import DDGS
from utils.logger import logger

def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information.

    Args:
        query: The search query string.
        max_results: Number of results to return (default 5).

    Returns:
        Formatted search results with titles, URLs, and snippets.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No results found for: {query}"
        out = f"Search results for: {query}\n\n"
        for i, r in enumerate(results, 1):
            out += f"{i}. {r['title']}\n   {r['href']}\n   {r['body'][:250]}\n\n"
        return out
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Search failed: {e}"
