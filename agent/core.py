import asyncio
from agent.memory import get_or_create_session, increment_turn, set_current_user, update_thinking_level
from agent.context import set_request_context
from agent.loop import run_agentic_loop
from agent.thinking_classifier import get_thinking_level
from memory.manager import save_episode
from memory.fact_extractor import extract_facts
from tools.file_sender import get_pending_files, clear_pending_files
from utils.logger import logger

# Tasks that warrant the full agentic loop
AGENTIC_TRIGGERS = [
    "create", "build", "write", "code", "implement", "develop",
    "fix", "debug", "refactor", "test",
    "extract", "convert", "process", "analyze",
    "research", "find the best", "compare",
    "automate", "script",
]


def _needs_agentic_loop(message: str) -> bool:
    m = message.lower()
    return any(t in m for t in AGENTIC_TRIGGERS)


async def process_message_stream(user_id: int, message: str, chat_id: int):
    set_current_user(user_id)
    set_request_context(user_id, chat_id)
    session = get_or_create_session(user_id, message)
    update_thinking_level(user_id, message)

    logger.debug(f"[user:{user_id}] ── NEW MESSAGE ──────────────────────────")
    logger.debug(f"[user:{user_id}] INPUT: {message}")

    use_loop = _needs_agentic_loop(message)
    logger.info(f"[user:{user_id}] mode={'agentic_loop' if use_loop else 'single_shot'}")

    try:
        if use_loop:
            # Stream step-by-step updates
            final_text = ""
            async for chunk in run_agentic_loop(session, message, user_id):
                final_text = chunk
                yield chunk           # live updates to Telegram
        else:
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
                final_text = response.text or "✅ Done."
            except Exception:
                final_text = "✅ Done."

            yield final_text

    except Exception as e:
        logger.error(f"[user:{user_id}] AGENT ERROR: {e}")
        yield f"❌ Error: {str(e)}"
        return

    logger.debug(f"[user:{user_id}] ── END ──────────────────────────────────")

    if final_text not in ("✅ Done.",):
        increment_turn(user_id)
        await asyncio.to_thread(save_episode, user_id, message, final_text)
        await asyncio.to_thread(extract_facts, str(user_id), message, final_text)


def pop_pending_files(chat_id: int) -> list[str]:
    files = get_pending_files(chat_id)
    clear_pending_files(chat_id)
    return files
