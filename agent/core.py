import asyncio
import threading
from agent.memory import get_or_create_session
from tools.file_sender import set_current_chat_id, get_pending_files, clear_pending_files
from utils.logger import logger

# ── Streaming ──────────────────────────────────────────────────────────────

async def process_message_stream(user_id: int, message: str, chat_id: int):
    """
    Async generator that yields accumulated text as Gemini streams it.
    Bridges the synchronous google-genai SDK to async Telegram handler.
    """
    set_current_chat_id(chat_id)
    session = get_or_create_session(user_id)
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _worker():
        try:
            for chunk in session.send_message_stream(message):
                if chunk.text:
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk.text))
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    accumulated = ""
    while True:
        event_type, value = await queue.get()
        if event_type == "chunk":
            accumulated += value
            yield accumulated
        elif event_type == "done":
            break
        elif event_type == "error":
            logger.error(f"Stream error: {value}")
            yield accumulated + f"\n\n❌ Stream error: {value}"
            break

    thread.join(timeout=5)

# ── File queue helper ───────────────────────────────────────────────────────

def pop_pending_files(chat_id: int) -> list[str]:
    files = get_pending_files(chat_id)
    clear_pending_files(chat_id)
    return files
