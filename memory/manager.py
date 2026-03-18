import uuid
from datetime import datetime, timezone
from memory.embedder import embed
from memory.vector_store import store_exchange, similarity_search
from utils.logger import logger

# Cosine distance: 0 = identical, 1 = orthogonal
# Only inject memories with distance < threshold (i.e. genuinely relevant)
RELEVANCE_THRESHOLD = 0.45
TOP_K = 4

def save_exchange(user_id: int, user_message: str, agent_response: str):
    """Embed and store a full conversation exchange in ChromaDB."""
    try:
        text = f"User: {user_message}\nAssistant: {agent_response}"
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
    except Exception as e:
        logger.error(f"Failed to save exchange: {e}")

def get_relevant_context(user_id: int, query: str) -> str:
    """
    Embed the query, search ChromaDB for semantically similar past exchanges,
    filter by relevance threshold, and return a formatted context block.
    Returns empty string if no relevant memories found.
    """
    try:
        query_embedding = embed(query)
        results = similarity_search(user_id, query_embedding, n_results=TOP_K)
        relevant = [r for r in results if r["distance"] < RELEVANCE_THRESHOLD]

        if not relevant:
            return ""

        lines = ["📌 Relevant context from past conversations (use if helpful):\n"]
        for r in relevant:
            ts = r["metadata"].get("timestamp", "")[:10]  # just the date
            lines.append(f"[{ts}]\n{r['text']}\n")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        return ""
