import uuid
from typing import Callable, Any
from utils.logger import logger

_pending: dict[str, dict] = {}

def register_action(func: Callable, args: dict, description: str) -> str:
    action_id = str(uuid.uuid4())[:8]
    _pending[action_id] = {"func": func, "args": args, "description": description}
    logger.info(f"[confirm] Registered action {action_id}: {description}")
    return action_id

def get_action(action_id: str) -> dict | None:
    return _pending.get(action_id)

def execute_action(action_id: str) -> str:
    action = _pending.pop(action_id, None)
    if not action:
        return "⚠️ Action expired or already executed."
    try:
        result = action["func"](**action["args"])
        logger.info(f"[confirm] Executed {action_id}: {action['description']}")
        return result
    except Exception as e:
        logger.error(f"[confirm] Execution failed {action_id}: {e}")
        return f"❌ Execution failed: {e}"

def cancel_action(action_id: str) -> str:
    action = _pending.pop(action_id, None)
    if action:
        logger.info(f"[confirm] Cancelled {action_id}: {action['description']}")
        return f"❌ Cancelled: {action['description']}"
    return "⚠️ Action not found or already handled."

def cleanup_pending():
    """Remove all pending actions (called on /reset)."""
    _pending.clear()
