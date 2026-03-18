import asyncio
from agent.memory import get_or_create_session
from tools.file_sender import set_current_chat_id, get_pending_files, clear_pending_files
from utils.logger import logger

async def process_message(user_id: int, message: str, chat_id: int) -> tuple[str, list[str]]:
    set_current_chat_id(chat_id)
    try:
        session = get_or_create_session(user_id)
        response = await asyncio.to_thread(session.send_message, message)
        text = response.text or "✅ Done."
        files = get_pending_files(chat_id)
        clear_pending_files(chat_id)
        return text, files
    except Exception as e:
        logger.error(f"Agent error for user {user_id}: {e}")
        return f"❌ Error: {str(e)}", []
