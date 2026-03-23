# Holds per-request context accessible by tools without passing args through the call stack

_current_user_id: int = 0
_current_chat_id: int = 0

def set_request_context(user_id: int, chat_id: int):
    global _current_user_id, _current_chat_id
    _current_user_id = user_id
    _current_chat_id = chat_id

def get_user_id() -> int:
    return _current_user_id

def get_chat_id() -> int:
    return _current_chat_id
