import importlib.util
import sys
from pathlib import Path
from utils.logger import logger

DYNAMIC_DIR = Path("tools/dynamic")

def load_all_dynamic_tools() -> list:
    """Load all previously created dynamic tools from disk."""
    tools = []
    for path in DYNAMIC_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"tools.dynamic.{path.stem}"] = module
            spec.loader.exec_module(module)
            func = getattr(module, path.stem, None)
            if func and callable(func):
                tools.append(func)
                logger.info(f"[dynamic_loader] Loaded: {path.stem}")
        except Exception as e:
            logger.error(f"[dynamic_loader] Failed to load {path.stem}: {e}")
    return tools
