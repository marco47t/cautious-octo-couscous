import asyncio
from agent.memory import get_or_create_session, increment_turn, set_current_user, update_thinking_level
from agent.context import set_request_context
from memory.manager import save_episode
from memory.fact_extractor import extract_facts
from tools.file_sender import get_pending_files, clear_pending_files
from tools.tool_builder import _pending_confirmations
from utils.logger import logger


async def process_message_stream(user_id: int, message: str, chat_id: int):
    set_current_user(user_id)                          # ← only addition
    set_request_context(user_id, chat_id)
    session = get_or_create_session(user_id, message)
    update_thinking_level(user_id, message)             # ← adjust per turn

    logger.debug(f"[user:{user_id}] ── NEW MESSAGE ──────────────────────────")
    logger.debug(f"[user:{user_id}] INPUT: {message}")

    try:
        response = await asyncio.to_thread(session.send_message, message)
        try:
            for candidate in (response.candidates or []):
                for part in (candidate.content.parts or []):
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        logger.info(f"[user:{user_id}] TOOL CALL → {fc.name}({dict(fc.args)})")
                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        logger.debug(f"[user:{user_id}] TOOL RESULT ← {fr.name}: {str(fr.response)[:300]}")
        except Exception:
            pass

        try:
            text = response.text
        except Exception:
            text = None
        text = text or "✅ Done."

    except Exception as e:
        logger.error(f"[user:{user_id}] AGENT ERROR: {e}")
        yield f"❌ Error: {str(e)}"
        return

    # ── Tool confirmation pending? Bypass Gemini's rewrite ──────────────
    if user_id in _pending_confirmations:
        pending = _pending_confirmations[user_id]
        ops_list = "\n".join(f"  • {op}" for op in pending["ops"])
        yield (
            f"⚠️ <b>Tool needs elevated permissions</b>\n\n"
            f"To create <code>{pending['function_name']}</code>, "
            f"I need to use:\n{ops_list}\n\n"
            f"Do you want to allow this?"
            f"||CONFIRMTOOLCREATION:{user_id}||"
        )
        return   # skip save_episode and increment_turn
    # ────────────────────────────────────────────────────────────────────

    logger.debug(f"[user:{user_id}] RESPONSE: {text[:500]}")
    logger.debug(f"[user:{user_id}] ── END ──────────────────────────────────")

    yield text

    if text not in ("✅ Done.",):
        increment_turn(user_id)
        await asyncio.to_thread(save_episode, user_id, message, text)
        await asyncio.to_thread(extract_facts, str(user_id), message, text)


def pop_pending_files(chat_id: int) -> list[str]:
    files = get_pending_files(chat_id)
    clear_pending_files(chat_id)
    return files
