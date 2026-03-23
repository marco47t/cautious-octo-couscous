import re
import uuid
from datetime import datetime, timezone
from memory.embedder import embed
from memory.vector_store import store_exchange, similarity_search
from utils.logger import logger

# Only block storing time-sensitive exchanges — retrieval is now tool-driven
TIME_SENSITIVE_PATTERNS = [
    r"\bweather\b", r"\btemperature\b", r"\bforecast\b",
    r"\btime\b", r"\bdate\b", r"\btoday\b", r"\bnow\b",
    r"\bnews\b", r"\bprice\b", r"\bstock\b", r"\blatest\b",
]
GREETING_PATTERN = r"^(hi|hello|hey|thanks|ok|okay|yes|no|sure|alright)[\s!.]*$"
MIN_EXCHANGE_LENGTH = 120

def _is_time_sensitive(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in TIME_SENSITIVE_PATTERNS)

def _is_trivial(text: str) -> bool:
    return bool(re.match(GREETING_PATTERN, text.lower().strip()))

def _clean(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()

def save_episode(user_id: int, user_message: str, agent_response: str):
    """Store a conversation exchange in ChromaDB for episodic retrieval."""
    if _is_trivial(user_message) or _is_time_sensitive(user_message):
        logger.debug(f"[memory] Skipped episode storage (trivial/time-sensitive)")
        return

    text = f"User: {_clean(user_message)}\nAssistant: {_clean(agent_response)}"
    if len(text) < MIN_EXCHANGE_LENGTH:
        logger.debug(f"[memory] Skipped episode storage ({len(text)} chars too short)")
        return

    try:
        embedding = embed(text)
        store_exchange(
            user_id=user_id,
            exchange_id=str(uuid.uuid4()),
            text=text,
            embedding=embedding,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": str(user_id),
            },
        )
        logger.debug(f"[memory] Saved episode for user {user_id} ({len(text)} chars)")
    except Exception as e:
        logger.error(f"[memory] Failed to save episode: {e}")

def retrieve_episodes(user_id: int, query: str, threshold: float = 0.45) -> str:
    """Direct episodic retrieval — called by the retrieve_memory tool."""
    try:
        query_embedding = embed(query)
        results = similarity_search(user_id, query_embedding, n_results=3)
        relevant = [r for r in results if r["distance"] < threshold]

        logger.debug(
            f"[memory] retrieve_episodes for user {user_id}: "
            f"'{query[:60]}' → {len(results)} results, {len(relevant)} passed threshold"
        )
        for r in relevant:
            logger.debug(f"[memory]   distance={r['distance']:.3f} | {r['text'][:120]}")

        if not relevant:
            return ""

        lines = []
        for r in relevant:
            ts = r["metadata"].get("timestamp", "")[:10]
            lines.append(f"[{ts}]\n{r['text']}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.error(f"[memory] retrieve_episodes error: {e}")
        return ""
