import re
from ddgs import DDGS
from utils.logger import logger
from utils.tool_logger import logged_tool

def _search(query: str, max_results: int) -> list:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))

def _rephrase(query: str) -> str:
    """Simple rephrasing for retry — add context words."""
    q = query.strip()
    if not q.endswith("?"):
        q = q + " explained"
    return q

@logged_tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for current information. Automatically retries with rephrased query if no results found.

    Args:
        query: The search query string.
        max_results: Number of results to return (default 5).

    Returns:
        Formatted search results with titles, URLs, and snippets.
    """
    try:
        results = _search(query, max_results)

        # Self-correction: retry with rephrased query if empty
        if not results:
            logger.info(f"[search] No results for '{query}', retrying with rephrased query...")
            rephrased = _rephrase(query)
            results = _search(rephrased, max_results)
            if results:
                logger.info(f"[search] Retry succeeded with '{rephrased}'")
            else:
                return f"No results found for: '{query}' (also tried: '{rephrased}')"

        out = f"Search results for: {query}\n\n"
        for i, r in enumerate(results, 1):
            out += f"{i}. {r['title']}\n   {r['href']}\n   {r['body'][:250]}\n\n"
        return out
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Search failed: {e}. Try a simpler or rephrased query."
