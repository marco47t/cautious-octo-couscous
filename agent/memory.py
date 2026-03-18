from typing import Dict
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from agent.system_prompt import SYSTEM_PROMPT

client = genai.Client(api_key=GEMINI_API_KEY)

_sessions: Dict[int, object] = {}

def get_or_create_session(user_id: int):
    if user_id not in _sessions:
        from tools.registry import get_tools
        _sessions[user_id] = client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=get_tools(),
            )
        )
    return _sessions[user_id]

def clear_session(user_id: int):
    _sessions.pop(user_id, None)
