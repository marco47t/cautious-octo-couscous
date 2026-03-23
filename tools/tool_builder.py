import ast
import importlib.util
import inspect
import re
import sys
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY, GEMINI_HELPER_MODEL
from utils.logger import logger
from utils.tool_logger import logged_tool

_client = genai.Client(api_key=GEMINI_API_KEY)
DYNAMIC_DIR = Path("tools/dynamic")
DYNAMIC_DIR.mkdir(parents=True, exist_ok=True)

_BUILDER_PROMPT = """You are a Python tool builder. Write a single Python function that solves the task described.

Task: {task}
Function name: {function_name}

STRICT RULES:
- Write ONLY the function definition, nothing else
- No imports outside the function body
- Use only stdlib modules: urllib, json, re, os, datetime, math, hashlib, base64, csv, io
- The function must have a clear docstring with Args and Returns sections
- Handle ALL exceptions and return an error string on failure — never raise
- Return a formatted string result always
- No class definitions, no global variables, no print statements
- Function must be self-contained

Example of correct format:
def get_something(query: str) -> str:
    \"\"\"Get something from the web.

    Args:
        query: What to look up.

    Returns:
        Formatted result string.
    \"\"\"
    import urllib.request
    import json
    try:
        url = f"https://api.example.com/{{query}}"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        return f"Result: {{data}}"
    except Exception as e:
        return f"Error: {{e}}"

Write ONLY the function for this task:"""

def _sanitize_name(name: str) -> str:
    """Convert any string to a valid Python function name."""
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip().lower())
    name = re.sub(r"_+", "_", name).strip("_")
    if name[0].isdigit():
        name = "tool_" + name
    return name[:50]

def _validate_code(code: str, function_name: str) -> tuple[bool, str]:
    """Validate generated code is safe and syntactically correct."""
    # Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Must contain exactly one function definition with the right name
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not functions:
        return False, "No function definition found"
    if functions[0].name != function_name:
        return False, f"Function name mismatch: expected {function_name}, got {functions[0].name}"

    # Banned patterns — no file writes, no exec, no subprocess outside allowed
    banned = ["exec(", "eval(", "subprocess", "os.system", "open(", "__import__",
              "compile(", "globals(", "locals(", "shutil", "socket.bind"]
    for b in banned:
        if b in code:
            return False, f"Banned pattern detected: {b}"

    return True, "OK"

def _extract_function(raw: str, function_name: str) -> str:
    """Extract just the function definition from LLM output."""
    # Remove markdown code blocks
    raw = re.sub(r"```python\n?", "", raw)
    raw = re.sub(r"```\n?", "", raw)

    # Find the function definition
    match = re.search(rf"(def {function_name}\(.*?)\Z", raw, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: find any def statement
    match = re.search(r"(def \w+\(.*?)\Z", raw, re.DOTALL)
    if match:
        return match.group(1).strip()

    return raw.strip()

@logged_tool
def create_tool(function_name: str, task_description: str) -> str:
    """Dynamically create a new tool function when no existing tool can handle a task.
    Call this when the user asks for something you cannot do with existing tools.
    The created tool is immediately available to use in this session.

    Args:
        function_name: Snake_case name for the new tool e.g. 'get_bitcoin_price', 'convert_currency'.
        task_description: Clear description of what the function should do, including
                         what API or method to use if known.

    Returns:
        Success message with the created tool's signature, or error description.
    """
    function_name = _sanitize_name(function_name)
    tool_path = DYNAMIC_DIR / f"{function_name}.py"

    # Check if already exists
    if tool_path.exists():
        logger.info(f"[tool_builder] Tool {function_name} already exists, reloading")
        return _load_tool(function_name, tool_path)

    logger.info(f"[tool_builder] Building tool: {function_name}")

    # Generate with Gemini
    prompt = _BUILDER_PROMPT.format(
        task=task_description,
        function_name=function_name
    )
    try:
        resp = _client.models.generate_content(
            model=GEMINI_HELPER_MODEL,
            contents=prompt
        )
        raw_code = resp.text.strip()
    except Exception as e:
        return f"❌ Failed to generate tool code: {e}"

    # Extract and clean
    code = _extract_function(raw_code, function_name)

    # Validate
    valid, reason = _validate_code(code, function_name)
    if not valid:
        # Try once more with explicit correction
        logger.warning(f"[tool_builder] First attempt invalid ({reason}), retrying...")
        retry_prompt = f"{prompt}\n\nPrevious attempt had this error: {reason}\nFix it and try again:"
        try:
            resp = _client.models.generate_content(
                model=GEMINI_HELPER_MODEL,
                contents=retry_prompt
            )
            code = _extract_function(resp.text.strip(), function_name)
            valid, reason = _validate_code(code, function_name)
        except Exception:
            pass

        if not valid:
            return f"❌ Could not generate valid tool ({reason}). Try describing the task differently."

    # Write to file
    file_content = f'"""\nDynamically created tool: {function_name}\nTask: {task_description}\n"""\n\n{code}\n'
    tool_path.write_text(file_content)
    logger.info(f"[tool_builder] Written to {tool_path}")

    return _load_tool(function_name, tool_path)

def _load_tool(function_name: str, tool_path: Path) -> str:
    """Dynamically load a tool module and register it in the active session."""
    try:
        spec = importlib.util.spec_from_file_location(function_name, tool_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"tools.dynamic.{function_name}"] = module
        spec.loader.exec_module(module)

        func = getattr(module, function_name, None)
        if not func or not callable(func):
            return f"❌ Function {function_name} not found in generated module"

        # Get signature for confirmation message
        sig = inspect.signature(func)
        doc = (func.__doc__ or "").strip().split("\n")[0]

        # Register in active Gemini sessions
        _register_in_sessions(func)

        logger.info(f"[tool_builder] Loaded and registered: {function_name}{sig}")
        return (
            f"✅ Tool created and ready: <code>{function_name}{sig}</code>\n"
            f"📝 {doc}\n\n"
            f"I'll use it now to complete your request."
        )
    except Exception as e:
        logger.error(f"[tool_builder] Load error: {e}")
        return f"❌ Tool generated but failed to load: {e}"

def _register_in_sessions(func):
    """Inject a new tool into all active Gemini chat sessions."""
    try:
        from agent.memory import _sessions
        from utils.tool_logger import logged_tool as log_tool

        # Wrap with logging
        logged_func = log_tool(func)

        for user_id, session in _sessions.items():
            try:
                # Gemini SDK: add tool to existing session config
                existing_tools = session._config.tools or []
                if logged_func not in existing_tools:
                    existing_tools.append(logged_func)
                    session._config.tools = existing_tools
                logger.debug(f"[tool_builder] Injected {func.__name__} into session {user_id}")
            except Exception as e:
                logger.debug(f"[tool_builder] Could not inject into session {user_id}: {e}")
    except Exception as e:
        logger.debug(f"[tool_builder] Session registration error: {e}")

@logged_tool
def list_dynamic_tools() -> str:
    """List all dynamically created tools available in this session.
    Call this when the user asks what custom tools exist or what you've built.

    Returns:
        List of all dynamically created tools with their descriptions.
    """
    tools = list(DYNAMIC_DIR.glob("*.py"))
    tools = [t for t in tools if t.name != "__init__.py"]

    if not tools:
        return "No dynamic tools created yet."

    out = f"🔧 <b>Dynamic Tools ({len(tools)})</b>\n\n"
    for t in tools:
        try:
            spec = importlib.util.spec_from_file_location(t.stem, t)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            func = getattr(mod, t.stem, None)
            if func:
                doc = (func.__doc__ or "").strip().split("\n")[0]
                sig = inspect.signature(func)
                out += f"• <code>{t.stem}{sig}</code>\n  {doc}\n\n"
        except Exception:
            out += f"• {t.stem}\n\n"
    return out

@logged_tool
def delete_dynamic_tool(function_name: str) -> str:
    """Delete a dynamically created tool.
    Call this when the user asks to remove a custom tool.

    Args:
        function_name: Name of the tool to delete.

    Returns:
        Confirmation message.
    """
    tool_path = DYNAMIC_DIR / f"{function_name}.py"
    if not tool_path.exists():
        return f"Tool '{function_name}' not found."
    tool_path.unlink()
    sys.modules.pop(f"tools.dynamic.{function_name}", None)
    logger.info(f"[tool_builder] Deleted tool: {function_name}")
    return f"🗑️ Tool '{function_name}' deleted."
