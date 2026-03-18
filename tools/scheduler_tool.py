import uuid
from datetime import datetime, timedelta, timezone
from scheduler.manager import scheduler, _fire_reminder
from utils.logger import logger

def schedule_reminder(message: str, delay_seconds: int = 0, delay_minutes: int = 0, delay_hours: int = 0, at_time_utc: str = "") -> str:
    """Schedule a reminder to be sent to the user via Telegram at a future time.

    Args:
        message: The reminder text to send.
        delay_seconds: Seconds from now to send the reminder (e.g. 30).
        delay_minutes: Minutes from now to send the reminder (e.g. 30).
        delay_hours: Hours from now to send the reminder (e.g. 2).
        at_time_utc: Exact UTC datetime string in format 'YYYY-MM-DD HH:MM' (optional, overrides delay).

    Returns:
        Confirmation with job ID and scheduled time.
    """
    try:
        job_id = str(uuid.uuid4())[:8]
        if at_time_utc:
            run_at = datetime.strptime(at_time_utc, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        else:
            run_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay_seconds,
                minutes=delay_minutes,
                hours=delay_hours
            )

        scheduler.add_job(
            _fire_reminder,
            trigger="date",
            run_date=run_at,
            args=[message],
            id=job_id,
            replace_existing=False,
        )
        formatted = run_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"✅ Reminder scheduled (ID: `{job_id}`)\n📅 Time: {formatted}\n💬 Message: {message}"
    except Exception as e:
        return f"Failed to schedule reminder: {e}"


def list_reminders() -> str:
    """List all pending scheduled reminders.

    Returns:
        Formatted list of upcoming reminders with IDs and times.
    """
    jobs = scheduler.get_jobs()
    if not jobs:
        return "No pending reminders."
    out = f"📋 *{len(jobs)} pending reminder(s):*\n\n"
    for job in jobs:
        run_time = job.next_run_time.strftime("%Y-%m-%d %H:%M UTC") if job.next_run_time else "unknown"
        msg = job.args[0] if job.args else ""
        out += f"🔹 ID: `{job.id}` — {run_time}\n   💬 {msg}\n\n"
    return out

def cancel_reminder(job_id: str) -> str:
    """Cancel a scheduled reminder by its ID.

    Args:
        job_id: The ID of the reminder to cancel (from list_reminders).

    Returns:
        Confirmation or error message.
    """
    try:
        scheduler.remove_job(job_id)
        return f"✅ Reminder `{job_id}` cancelled."
    except Exception as e:
        return f"Could not cancel reminder: {e}"
