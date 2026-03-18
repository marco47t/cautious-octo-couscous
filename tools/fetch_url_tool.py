import urllib.request
import urllib.error
import html
import re
from utils.logger import logger

def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Fetch and extract readable text content from any public webpage or URL.

    Args:
        url: Full URL to fetch (must start with http:// or https://).
        max_chars: Maximum characters to return (default 4000).

    Returns:
        Cleaned text content of the page.
    """
    if not url.startswith(("http://", "https://")):
        return "Invalid URL — must start with http:// or https://"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PersonalAgent/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Strip scripts, styles, tags
        raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = html.unescape(raw)
        raw = re.sub(r"\s{2,}", " ", raw).strip()

        if len(raw) > max_chars:
            raw = raw[:max_chars] + f"\n\n[Truncated — {len(raw)} total chars]"

        return f"Content from {url}:\n\n{raw}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} error fetching {url}: {e.reason}"
    except Exception as e:
        logger.error(f"fetch_url error: {e}")
        return f"Failed to fetch {url}: {e}"
