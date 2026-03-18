import asyncio
import threading

from agent.memory import get_or_create_session, increment_turn
from memory.manager import get_relevant_context, save_exchange
from tools.file_sender import set_current_chat_id, get_pending_files, clear_pending_files
from utils.logger import logger


async def process_message_stream(user_id: int, message: str, chat_id: int):
    set_current_chat_id(chat_id)
    session = get_or_create_session(user_id)

    logger.debug(f"[user:{user_id}] ── NEW MESSAGE ──────────────────────────")
    logger.debug(f"[user:{user_id}] INPUT: {message}")

    context = await asyncio.to_thread(get_relevant_context, user_id, message)
    if context:
        logger.debug(f"[user:{user_id}] MEMORY INJECTED:\n{context[:800]}")
    else:
        logger.debug(f"[user:{user_id}] MEMORY: no relevant context found")

    enriched = f"{context}\n\n[Current message]:\n{message}" if context else message

    try:
        response = await asyncio.to_thread(session.send_message, enriched)

        # Log all tool calls from response candidates
        try:
            for candidate in (response.candidates or []):
                for part in (candidate.content.parts or []):
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        logger.info(f"[user:{user_id}] TOOL CALL → {fc.name}({dict(fc.args)})")
                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        logger.debug(f"[user:{user_id}] TOOL RESULT ← {fr.name}: {str(fr.response)[:400]}")
        except Exception as log_err:
            logger.debug(f"[user:{user_id}] Could not log tool parts: {log_err}")

        try:
            text = response.text
        except Exception:
            text = None

        text = text or "✅ Done."

    except Exception as e:
        logger.error(f"[user:{user_id}] AGENT ERROR: {e}")
        yield f"❌ Error: {str(e)}"
        return

    logger.debug(f"[user:{user_id}] RESPONSE: {text[:500]}")
    logger.debug(f"[user:{user_id}] ── END ──────────────────────────────────")

    yield text

    if text != "✅ Done.":
        increment_turn(user_id)
        await asyncio.to_thread(save_exchange, user_id, message, text)


def pop_pending_files(chat_id: int) -> list[str]:
    files = get_pending_files(chat_id)
    clear_pending_files(chat_id)
    return files
