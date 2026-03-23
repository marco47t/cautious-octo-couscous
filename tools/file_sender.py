from pathlib import Path
from typing import Dict, List
from agent.context import get_chat_id

_pending: Dict[int, List[str]] = {}

def get_pending_files(chat_id: int) -> List[str]:
    return _pending.get(chat_id, [])

def clear_pending_files(chat_id: int):
    _pending.pop(chat_id, None)

def send_file_to_user(file_path: str) -> str:
    """Send a file from the server to the user via Telegram.

    Args:
        file_path: Full absolute path to the file to send.

    Returns:
        Confirmation message or error.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return f"File not found: {file_path}"
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 50:
        return f"File too large ({size_mb:.1f} MB). Telegram limit is 50 MB."
    chat_id = get_chat_id()
    _pending.setdefault(chat_id, []).append(str(path))
    return f"✅ '{path.name}' ({size_mb:.2f} MB) will be sent momentarily."
