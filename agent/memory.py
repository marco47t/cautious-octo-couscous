from typing import Dict
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from agent.system_prompt import SYSTEM_PROMPT

client = genai.Client(api_key=GEMINI_API_KEY)

MAX_SESSION_TURNS = 10  # reset in-memory session after N turns to control tokens

_sessions: Dict[int, object] = {}
_turn_counts: Dict[int, int] = {}

def get_or_create_session(user_id: int):
    from tools.registry import get_tools
    if user_id not in _sessions:
        _sessions[user_id] = _new_session()
        _turn_counts[user_id] = 0
    return _sessions[user_id]

def _new_session():
    from tools.registry import get_tools
    return client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=get_tools(),
        )
    )

def increment_turn(user_id: int):
    _turn_counts[user_id] = _turn_counts.get(user_id, 0) + 1
    if _turn_counts[user_id] >= MAX_SESSION_TURNS:
        _sessions[user_id] = _new_session()
        _turn_counts[user_id] = 0

def clear_session(user_id: int):
    _sessions.pop(user_id, None)
    _turn_counts.pop(user_id, None)
