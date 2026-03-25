import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY
from utils.logger import logger

_client = genai.Client(api_key=GEMINI_API_KEY)
CLASSIFIER_MODEL = "gemini-3.1-flash-lite-preview"

# ── Rule-based: always fixed regardless of message ──────────────────────────

ALWAYS_HIGH = [
    r"\bcreate[_\s]tool\b",
    r"\binstall[_\s]and[_\s]create\b",
    r"\bdebug\b", r"\brefactor\b",
    r"\barchitect\b", r"\bdesign\b",
    r"\balgorithm\b", r"\boptimize\b",
    r"\bsecurity\b", r"\bvulnerabilit",
    r"\banalyze\b.{0,30}\bcode\b",
    r"\bwrite.{0,20}(script|program|class|module)\b",
    r"\bcompare\b.{0,30}\b(approach|option|method)\b",
    r"\bwhy.{0,30}(not working|failing|broken|error)\b",
]

ALWAYS_MEDIUM = [
    r"\bsearch\b", r"\bfind\b", r"\bresearch\b",
    r"\bsummariz\b", r"\bexplain\b",
    r"\bemail\b", r"\breminder\b",
    r"\bschedule\b", r"\bfile\b",
    r"\bextract\b", r"\bconvert\b",
    r"\btranslat\b",
]

ALWAYS_LOW = [
    r"\b(hi|hello|hey|thanks|thank you|ok|okay|yes|no|sure)\b",
    r"\btime\b", r"\bdate\b", r"\bweather\b",
    r"\bstatus\b", r"\bping\b",
    r"^.{0,30}$",    # very short messages
]

_CLASSIFY_PROMPT = """Classify the complexity of this user request for an AI agent.
Reply with ONLY one word: low, medium, or high.

low    = simple lookup, greeting, yes/no, single fact, time/date/weather
medium = summarize, search, file operation, email, reminder, single tool use
high   = debug code, multi-step task, analysis, create/design something, complex reasoning

Request: {message}

Complexity:"""


def get_thinking_level(message: str) -> str:
    """Determine thinking level: low / medium / high."""
    msg_lower = message.lower()

    # Rule-based first — fastest path
    for pattern in ALWAYS_HIGH:
        if re.search(pattern, msg_lower):
            logger.debug(f"[thinking] high (rule: {pattern[:30]})")
            return "high"

    for pattern in ALWAYS_LOW:
        if re.search(pattern, msg_lower):
            logger.debug(f"[thinking] low (rule)")
            return "low"

    for pattern in ALWAYS_MEDIUM:
        if re.search(pattern, msg_lower):
            logger.debug(f"[thinking] medium (rule)")
            return "medium"

    # Ambiguous — ask a lightweight model
    try:
        resp = _client.models.generate_content(
            model=CLASSIFIER_MODEL,
            contents=_CLASSIFY_PROMPT.format(message=message[:300]),
            config=types.GenerateContentConfig(
                max_output_tokens=5,
                temperature=0.0,
            )
        )
        level = resp.text.strip().lower()
        if level in ("low", "medium", "high"):
            logger.debug(f"[thinking] {level} (classifier)")
            return level
    except Exception as e:
        logger.debug(f"[thinking] classifier failed: {e}")

    # Safe default
    return "medium"
