import uuid
from datetime import datetime, timezone
from memory.embedder import embed
from memory.vector_store import store_exchange, similarity_search
from utils.logger import logger

RELEVANCE_THRESHOLD = 0.45
TOP_K = 4
MIN_EXCHANGE_LENGTH = 100  # skip storing very short/trivial exchanges

def save_exchange(user_id: int, user_message: str, agent_response: str):
    text = f"User: {user_message}\nAssistant: {agent_response}"

    # Skip trivial exchanges (greetings, very short Q&A)
    if len(text) < MIN_EXCHANGE_LENGTH:
        logger.debug(f"[memory] Skipped trivial exchange for user {user_id} ({len(text)} chars)")
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
        logger.debug(f"[memory] Saved exchange for user {user_id} ({len(text)} chars)")
    except Exception as e:
        logger.error(f"[memory] Failed to save exchange: {e}")

def get_relevant_context(user_id: int, query: str) -> str:
    try:
        query_embedding = embed(query)
        results = similarity_search(user_id, query_embedding, n_results=TOP_K)
        relevant = [r for r in results if r["distance"] < RELEVANCE_THRESHOLD]

        logger.debug(
            f"[memory] Query for user {user_id}: '{query[:60]}' → "
            f"{len(results)} results, {len(relevant)} above threshold"
        )
        for r in relevant:
            logger.debug(f"[memory]   distance={r['distance']:.3f} | {r['text'][:120]}")

        if not relevant:
            return ""

        lines = ["📌 Relevant context from past conversations (use if helpful):\n"]
        for r in relevant:
            ts = r["metadata"].get("timestamp", "")[:10]
            lines.append(f"[{ts}]\n{r['text']}\n")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"[memory] Failed to get context: {e}")
        return ""
