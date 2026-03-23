import functools
from utils.logger import logger

def logged_tool(fn):
    """Decorator that logs every tool call and result automatically."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        all_args = {**{f"arg{i}": v for i, v in enumerate(args)}, **kwargs}
        preview = str(all_args)[:200]
        logger.info(f"[TOOL] → {fn.__name__}({preview})")
        try:
            result = fn(*args, **kwargs)
            logger.debug(f"[TOOL] ← {fn.__name__}: {str(result)[:300]}")
            return result
        except Exception as e:
            logger.error(f"[TOOL] ✗ {fn.__name__} failed: {e}")
            raise
    return wrapper
