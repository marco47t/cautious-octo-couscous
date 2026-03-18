from datetime import datetime, timezone
import zoneinfo

def get_current_datetime(timezone_name: str = "UTC") -> str:
    """Get the current date and time, optionally in a specific timezone.

    Args:
        timezone_name: IANA timezone string e.g. 'Africa/Cairo', 'US/Eastern', 'UTC'. Default is UTC.

    Returns:
        Formatted current date and time with timezone info.
    """
    try:
        tz = zoneinfo.ZoneInfo(timezone_name)
        now = datetime.now(tz)
        return (
            f"🕐 Current time in {timezone_name}:\n"
            f"Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"Time: {now.strftime('%H:%M:%S %Z')}\n"
            f"Unix timestamp: {int(now.timestamp())}"
        )
    except zoneinfo.ZoneInfoNotFoundError:
        now = datetime.now(timezone.utc)
        return (
            f"⚠️ Unknown timezone '{timezone_name}', showing UTC instead.\n"
            f"Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"Time: {now.strftime('%H:%M:%S UTC')}"
        )
