import asyncio
import threading

from agent.memory import get_or_create_session, increment_turn
from memory.manager import get_relevant_context, save_exchange
from tools.file_sender import set_current_chat_id, get_pending_files, clear_pending_files
from utils.logger import logger


async def process_message_stream(user_id: int, message: str, chat_id: int):
    set_current_chat_id(chat_id)
    session = get_or_create_session(user_id)

    # Retrieve semantically relevant past exchanges
    context = await asyncio.to_thread(get_relevant_context, user_id, message)
    enriched = f"{context}\n\n[Current message]:\n{message}" if context else message

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    full_chunks = []

    def _worker():
        try:
            for chunk in session.send_message_stream(enriched):
                if chunk.text:
                    full_chunks.append(chunk.text)
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

    # Persist exchange to vector DB + increment session turn counter
    if accumulated:
        increment_turn(user_id)
        await asyncio.to_thread(save_exchange, user_id, message, accumulated)


def pop_pending_files(chat_id: int) -> list[str]:
    files = get_pending_files(chat_id)
    clear_pending_files(chat_id)
    return files
