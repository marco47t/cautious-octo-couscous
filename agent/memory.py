from typing import Dict
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from agent.system_prompt import build_system_prompt


client = genai.Client(api_key=GEMINI_API_KEY)
MAX_SESSION_TURNS = 10
_current_user_id: int | None = None

_sessions: Dict[int, object] = {}
_turn_counts: Dict[int, int] = {}


def set_current_user(user_id: int):       # ← only addition
    global _current_user_id
    _current_user_id = user_id


def _detect_context(message: str) -> str:
    m = message.lower()
    if any(w in m for w in ["code", "python", "function", "bug", "error", "script"]):
        return "code"
    if any(w in m for w in ["email", "send", "inbox", "message"]):
        return "email"
    if any(w in m for w in ["server", "cpu", "ram", "disk", "command", "shell", "process"]):
        return "server"
    if any(w in m for w in ["search", "find", "research", "news", "what is", "who is"]):
        return "research"
    return ""


def get_or_create_session(user_id: int, message: str = ""):
    from tools.registry import get_tools
    if user_id not in _sessions:
        context = _detect_context(message)
        _sessions[user_id] = client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(context),
                tools=get_tools(),
            )
        )
        _turn_counts[user_id] = 0
    return _sessions[user_id]


def increment_turn(user_id: int):
    _turn_counts[user_id] = _turn_counts.get(user_id, 0) + 1
    if _turn_counts[user_id] >= MAX_SESSION_TURNS:
        _sessions.pop(user_id, None)
        _turn_counts[user_id] = 0


def clear_session(user_id: int):
    _sessions.pop(user_id, None)
    _turn_counts.pop(user_id, None)
