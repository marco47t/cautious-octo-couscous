import urllib.request
import json
from utils.tool_logger import logged_tool
from utils.logger import logger


@logged_tool
def research_best_approach(task: str, context: str = "") -> str:
    """Research the best approach, libraries, and patterns for a given task.
    Call this BEFORE writing code or creating tools for non-trivial tasks.

    Args:
        task: What you're trying to accomplish.
        context: Additional context like language, constraints, environment.

    Returns:
        Recommended approaches, libraries, and gotchas.
    """
    from google import genai
    from google.genai import types
    from config import GEMINI_API_KEY

    RESEARCH_MODEL = "gemini-3.1-flash-lite-preview"

    prompt = f"""You are a senior software engineer. Give a concise technical recommendation.

Task: {task}
Context: {context or 'Python, Linux server environment'}

Provide:
1. Best library/approach to use (with pip install command if needed)
2. Key gotchas or common mistakes to avoid
3. A minimal working code skeleton (10-20 lines max)

Be specific and practical. No fluff."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=RESEARCH_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="high"),
                max_output_tokens=800,
            )
        )
        return resp.text or "No recommendation generated."
    except Exception as e:
        return f"❌ Research failed: {e}"
