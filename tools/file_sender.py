from pathlib import Path
from typing import Dict, List

_pending: Dict[int, List[str]] = {}
_current_chat_id: int = 0

def set_current_chat_id(chat_id: int):
    global _current_chat_id
    _current_chat_id = chat_id

def get_pending_files(chat_id: int) -> List[str]:
    return _pending.get(chat_id, [])

def clear_pending_files(chat_id: int):
    _pending.pop(chat_id, None)

def send_file_to_user(file_path: str) -> str:
    """Send a file from the computer to the user via Telegram.

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
    _pending.setdefault(_current_chat_id, []).append(str(path))
    return f"✅ '{path.name}' ({size_mb:.2f} MB) will be sent momentarily."
