import asyncio
import threading

from agent.memory import get_or_create_session, increment_turn
from memory.manager import get_relevant_context, save_exchange
from tools.file_sender import set_current_chat_id, get_pending_files, clear_pending_files
from utils.logger import logger


async def process_message_stream(user_id: int, message: str, chat_id: int):
    """
    Uses send_message (blocking) in a thread — the only reliable approach
    when Gemini uses automatic tool calling. Yields the final text once ready.
    """
    set_current_chat_id(chat_id)
    session = get_or_create_session(user_id)

    context = await asyncio.to_thread(get_relevant_context, user_id, message)
    enriched = f"{context}\n\n[Current message]:\n{message}" if context else message

    try:
        response = await asyncio.to_thread(session.send_message, enriched)
        try:
            text = response.text
        except Exception:
            text = None
        text = text or "✅ Done."
    except Exception as e:
        logger.error(f"Agent error for user {user_id}: {e}")
        yield f"❌ Error: {str(e)}"
        return

    yield text  # single yield — handler edits placeholder with final text

    if text != "✅ Done.":
        increment_turn(user_id)
        await asyncio.to_thread(save_exchange, user_id, message, text)


def pop_pending_files(chat_id: int) -> list[str]:
    files = get_pending_files(chat_id)
    clear_pending_files(chat_id)
    return files
