import json
from google import genai
from config import GEMINI_API_KEY
from memory.fact_store import init_db, upsert_fact
from utils.logger import logger

_client = genai.Client(api_key=GEMINI_API_KEY)
EXTRACT_MODEL = "gemini-3.1-flash-lite-preview"

_PROMPT = """Analyze this conversation and extract concrete, reusable facts about the user.

EXTRACT ONLY:
- Contact info: email, phone, username, social handles
- Identity: name, location, timezone, occupation, language
- Preferences: tone, format, style, habits
- Technical: tools, languages, platforms they use
- Explicit decisions or settings the user stated

DO NOT EXTRACT:
- Temporary actions or requests ("send an email", "search for X")
- Questions the user asked
- Time-sensitive data (weather, prices, news)
- Information about other people

Return ONLY a raw JSON array, no markdown. If no facts found, return [].
Schema: [{{"key": "snake_case_key", "value": "exact value", "fact": "User's X is Y.", "category": "contact|identity|preference|technical"}}]

Conversation:
User: {user_msg}
Assistant: {agent_msg}

JSON:"""

def extract_facts(user_id: str, user_message: str, agent_response: str) -> int:
    """Run Gemini extraction on an exchange, store results in SQLite. Returns count stored."""
    try:
        init_db()
        prompt = _PROMPT.format(
            user_msg=user_message[:600],
            agent_msg=agent_response[:600]
        )
        resp = _client.models.generate_content(model=EXTRACT_MODEL, contents=prompt)
        raw = (resp.text or "").strip().strip("```").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        if not raw or raw == "[]":
            return 0

        facts = json.loads(raw)
        if not isinstance(facts, list):
            return 0

        count = 0
        for f in facts:
            if all(k in f for k in ("key", "value", "fact")):
                upsert_fact(
                    user_id=str(user_id),
                    key=f["key"].lower().strip(),
                    value=f["value"].strip(),
                    full_fact=f["fact"].strip(),
                    category=f.get("category", "general"),
                )
                count += 1

        if count:
            logger.info(f"[facts] Extracted {count} fact(s) for user {user_id}")
        return count

    except json.JSONDecodeError:
        logger.debug("[facts] No facts extracted — LLM returned no JSON")
        return 0
    except Exception as e:
        logger.error(f"[facts] Extraction error: {e}")
        return 0
