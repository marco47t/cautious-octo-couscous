import asyncio
from utils.logger import logger

_pending_solution = asyncio.Event()
_bot_send_fn = None

def init_challenge_scheduler(send_fn):
    global _bot_send_fn
    _bot_send_fn = send_fn

def apply_challenge_schedules():
    """Read state and register cron jobs for each configured schedule slot."""
    from bot.daily_challenge import load_state
    from scheduler.manager import scheduler
    import zoneinfo

    remove_challenge_jobs()
    state = load_state()
    schedules = state.get("schedules", [])
    topic     = state.get("topic", "general")
    tz_str    = state.get("timezone", "Africa/Cairo")
    tz        = zoneinfo.ZoneInfo(tz_str)

    for i, slot in enumerate(schedules):
        time_str   = slot.get("time", "08:00")
        difficulty = slot.get("difficulty", "Medium")
        label      = slot.get("label", f"Challenge {i+1}")
        hour, minute = map(int, time_str.split(":"))

        job_id = f"challenge_slot_{i}"
        scheduler.add_job(
            _fire_challenge,
            "cron",
            hour=hour,
            minute=minute,
            timezone=tz,
            id=job_id,
            replace_existing=True,
            kwargs={"topic": topic, "difficulty": difficulty, "label": label}
        )
        logger.info(f"[challenge] Scheduled '{label}' at {time_str} {tz_str}")

def remove_challenge_jobs():
    from scheduler.manager import scheduler
    for job in scheduler.get_jobs():
        if job.id.startswith("challenge_slot_"):
            scheduler.remove_job(job.id)
    logger.info("[challenge] All challenge jobs removed")

async def _fire_challenge(topic: str, difficulty: str, label: str):
    """Called by scheduler at configured time — generates and sends challenge."""
    from bot.daily_challenge import generate_challenge, load_state, save_state
    if not _bot_send_fn:
        logger.error("[challenge] No send function registered")
        return
    text = await generate_challenge(topic, difficulty, label)
    await _bot_send_fn(text, parse_mode="HTML")

    # Save last challenge for solution generation
    state = load_state()
    state["last_challenge_text"] = text[:600]
    state["last_challenge_topic"] = topic
    state["checkin_done"] = False
    save_state(state)
