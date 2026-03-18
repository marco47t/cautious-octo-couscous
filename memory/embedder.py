import asyncio
from google import genai
from config import GEMINI_API_KEY

_client = genai.Client(api_key=GEMINI_API_KEY)
EMBED_MODEL = "gemini-embedding-001"

def embed(text: str) -> list[float]:
    result = _client.models.embed_content(model=EMBED_MODEL, contents=text)
    return result.embeddings[0].values

async def embed_async(text: str) -> list[float]:
    return await asyncio.to_thread(embed, text)
