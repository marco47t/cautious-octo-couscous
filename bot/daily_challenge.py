import json
import random
from datetime import date
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY
from utils.logger import logger

_client = genai.Client(api_key=GEMINI_API_KEY)
_STATE_FILE = "challenge_state.json"

# ── State ──────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    try:
        return json.loads(Path(_STATE_FILE).read_text())
    except Exception:
        return {}

def save_state(state: dict):
    Path(_STATE_FILE).write_text(json.dumps(state, indent=2))

def is_configured() -> bool:
    state = load_state()
    return bool(state.get("schedules"))

# ── Generation ─────────────────────────────────────────────────────────────────

_TOPIC_PROMPTS = {
    "leetcode": """Generate a LeetCode-style {difficulty} problem.
Format:
🧩 **{difficulty} Challenge**
**Problem:** [title]
**Description:** [clear problem statement]
**Input:** [format]
**Output:** [format]
**Example:**
  Input: [example]
  Output: [example]
**Hint:** [subtle hint, not the answer]""",

    "competitive_programming": """Generate an ICPC-style competitive programming problem, {difficulty} level.
Format:
🏆 **CP Challenge — {difficulty}**
**Problem:** [title]
**Statement:** [problem description]
**Input Format:** [format]
**Output Format:** [format]
**Sample:**
  Input: [sample]
  Output: [sample]
**Constraints:** [time/memory limits]""",

    "medical_lab": """Generate a medical laboratory science MCQ for a university student.
Topic: {topic}
Format:
🔬 **Lab Challenge**
**Question:** [question]
**A)** [option]
**B)** [option]
**C)** [option]
**D)** [option]
**Clinical Context:** [why this matters in practice]""",

    "math": """Generate a {difficulty} math problem suitable for a university student.
Format:
📐 **Math Challenge — {difficulty}**
**Problem:** [clear math problem]
**Context:** [real-world application if any]
**Hint:** [subtle hint]""",

    "general": """Generate an interesting {difficulty} brain teaser or logic puzzle.
Format:
🧠 **Brain Teaser**
**Puzzle:** [the puzzle]
**Hint:** [subtle hint]""",
}

_LAB_TOPICS = [
    "Hematology", "Clinical Chemistry", "Microbiology",
    "Blood Banking", "Urinalysis", "Histology", "Immunology"
]

def _build_prompt(topic: str, difficulty: str = "Medium") -> str:
    template = _TOPIC_PROMPTS.get(topic.lower(), _TOPIC_PROMPTS["general"])
    lab_topic = random.choice(_LAB_TOPICS)
    return template.format(difficulty=difficulty, topic=lab_topic)

async def generate_challenge(topic: str, difficulty: str = "Medium", slot_label: str = "") -> str:
    try:
        prompt = _build_prompt(topic, difficulty)
        resp = _client.models.generate_content(model="gemini-3.1-flash-lite-preview", contents=prompt)
        text = resp.text.strip()
        state = load_state()
        streak = state.get("streak", 0)
        streak_line = f"\n\n🔥 Streak: **{streak} day{'s' if streak != 1 else ''}**" if streak > 0 else ""
        header = f"⏰ <b>{slot_label}</b>\n\n" if slot_label else ""
        return f"{header}{text}{streak_line}"
    except Exception as e:
        logger.error(f"[challenge] Generation error: {e}")
        return f"❌ Could not generate challenge: {e}"

async def generate_solution(send_fn):
    """Generate and send the solution to today's last challenge."""
    state = load_state()
    last = state.get("last_challenge_text", "")
    last_topic = state.get("last_challenge_topic", "general")
    if not last:
        await send_fn("No challenge found to solve yet.", parse_mode="HTML")
        return
    try:
        if "lab" in last_topic.lower() or "medical" in last_topic.lower():
            prompt = f"Reveal the correct answer with full explanation:\n\n{last}\n\nExplain why each option is right or wrong."
        else:
            prompt = f"Provide a clean solution with explanation:\n\n{last}\n\nInclude: approach, Python code, time/space complexity."
        resp = _client.models.generate_content(model="gemini-3.1-flash-lite-preview", contents=prompt)
        await send_fn(f"💡 <b>Solution:</b>\n\n{resp.text.strip()[:3000]}", parse_mode="HTML")
    except Exception as e:
        await send_fn(f"❌ Could not generate solution: {e}", parse_mode="HTML")

def mark_solved() -> str:
    state = load_state()
    today = str(date.today())
    yesterday = str(date.fromordinal(date.today().toordinal() - 1))
    last = state.get("last_solved_date")
    if last == yesterday:
        state["streak"] = state.get("streak", 0) + 1
    elif last != today:
        state["streak"] = 1
    state["last_solved_date"] = today
    save_state(state)
    s = state["streak"]
    return f"✅ Marked as solved! 🔥 Streak: <b>{s} day{'s' if s != 1 else ''}</b>"
