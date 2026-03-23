import json
import zoneinfo
from utils.tool_logger import logged_tool
from utils.logger import logger

@logged_tool
def configure_challenges(
    topic: str,
    schedules_json: str,
    timezone: str = "Africa/Cairo"
) -> str:
    """Configure daily challenge schedule based on user request.
    Call this when the user asks to set up, start, change, or configure a daily challenge.

    Args:
        topic: Challenge topic — one of: 'leetcode', 'competitive_programming', 'medical_lab', 'math', 'general'
        schedules_json: JSON string of schedule list. Example:
            '[{"time": "08:00", "difficulty": "Easy", "label": "Morning"},
              {"time": "21:00", "difficulty": "Medium", "label": "Evening"}]'
        timezone: IANA timezone string e.g. 'Africa/Cairo', 'UTC'. Default: Africa/Cairo

    Returns:
        Confirmation message with configured schedule.
    """
    from bot.daily_challenge import load_state, save_state
    from bot.challenge_scheduler import apply_challenge_schedules

    # Parse and validate schedules
    try:
        schedules = json.loads(schedules_json)
        if not isinstance(schedules, list):
            return "❌ schedules_json must be a JSON array."
    except json.JSONDecodeError as e:
        return f"❌ Invalid schedules JSON: {e}"

    # Validate timezone
    try:
        zoneinfo.ZoneInfo(timezone)
    except Exception:
        timezone = "Africa/Cairo"

    # Validate each slot
    valid = []
    for s in schedules:
        if "time" not in s:
            continue
        valid.append({
            "time":       s.get("time", "08:00"),
            "difficulty": s.get("difficulty", "Medium"),
            "label":      s.get("label", "Challenge"),
        })

    if not valid:
        return "❌ No valid schedule slots found. Each slot needs at least a 'time' field (HH:MM)."

    state = load_state()
    state["topic"]     = topic
    state["schedules"] = valid
    state["timezone"]  = timezone
    state["streak"]    = state.get("streak", 0)
    save_state(state)

    apply_challenge_schedules()

    lines = [f"✅ <b>Daily Challenge Configured!</b>\n\n📚 Topic: <b>{topic}</b>\n"]
    for s in valid:
        lines.append(f"⏰ {s['time']} — {s['difficulty']} ({s['label']})")
    lines.append(f"\n🌍 Timezone: {timezone}")
    lines.append("\nSay <b>'stop challenges'</b> to cancel or <b>'solved it'</b> when you finish.")
    return "\n".join(lines)


@logged_tool
def stop_challenges() -> str:
    """Stop all scheduled daily challenges.
    Call this when the user says 'stop challenges', 'cancel challenges', or 'no more challenges'.

    Returns:
        Confirmation that challenges are stopped.
    """
    from bot.daily_challenge import load_state, save_state
    from bot.challenge_scheduler import remove_challenge_jobs

    state = load_state()
    state["schedules"] = []
    save_state(state)
    remove_challenge_jobs()
    return "⏹️ All daily challenges stopped. Say 'start challenges' anytime to resume."


@logged_tool
def get_challenge_status() -> str:
    """Get current challenge configuration and streak.
    Call this when the user asks about their challenge status, streak, or current schedule.

    Returns:
        Current challenge config, streak, and schedule.
    """
    from bot.daily_challenge import load_state
    state = load_state()
    if not state.get("schedules"):
        return "No challenges configured. Ask me to set up a daily challenge!"

    topic     = state.get("topic", "general")
    streak    = state.get("streak", 0)
    schedules = state.get("schedules", [])
    tz        = state.get("timezone", "Africa/Cairo")
    last      = state.get("last_solved_date", "never")

    lines = [
        f"📊 <b>Challenge Status</b>\n",
        f"📚 Topic: <b>{topic}</b>",
        f"🔥 Streak: <b>{streak} day{'s' if streak != 1 else ''}</b>",
        f"✅ Last solved: {last}",
        f"🌍 Timezone: {tz}\n",
        "<b>Schedule:</b>",
    ]
    for s in schedules:
        lines.append(f"  ⏰ {s.get('time')} — {s.get('difficulty','Medium')} ({s.get('label','')})")
    return "\n".join(lines)


@logged_tool
def mark_challenge_solved() -> str:
    """Mark today's challenge as solved and update streak.
    Call this when the user says 'solved it', 'done', 'finished the challenge', 'got it'.

    Returns:
        Congratulations message with updated streak.
    """
    from bot.daily_challenge import mark_solved
    return mark_solved()


@logged_tool
def send_challenge_solution() -> str:
    """Queue sending the solution to today's last challenge.
    Call this when the user says 'show solution', 'give me the answer', 'reveal answer'.

    Returns:
        Acknowledgement that solution is being sent.
    """
    from bot.challenge_scheduler import queue_solution
    queue_solution()
    return "💡 Sending solution now..."
