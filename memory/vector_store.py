import chromadb
from utils.logger import logger

DB_PATH = "memory_db"
_client = chromadb.PersistentClient(path=DB_PATH)

def get_collection(user_id: int):
    return _client.get_or_create_collection(
        name=f"user_{user_id}",
        metadata={"hnsw:space": "cosine"}
    )

def store_exchange(user_id: int, exchange_id: str, text: str, embedding: list[float], metadata: dict):
    try:
        col = get_collection(user_id)
        col.add(
            ids=[exchange_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
    except Exception as e:
        logger.error(f"Vector store error: {e}")

def similarity_search(user_id: int, query_embedding: list[float], n_results: int = 5) -> list[dict]:
    try:
        col = get_collection(user_id)
        count = col.count()
        if count == 0:
            return []
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {"text": doc, "distance": dist, "metadata": meta}
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            )
        ]
    except Exception as e:
        logger.error(f"Similarity search error: {e}")
        return []

def get_total_exchanges(user_id: int) -> int:
    return get_collection(user_id).count()
