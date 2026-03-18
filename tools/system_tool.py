import psutil
import platform
from datetime import datetime, timezone, timedelta
from utils.logger import logger

def get_system_info() -> str:
    """Get current AWS server resource usage: CPU, RAM, disk, and uptime.

    Returns:
        Formatted system stats summary.
    """
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
        uptime = str(timedelta(seconds=int((datetime.now(timezone.utc) - boot_time).total_seconds())))
        net = psutil.net_io_counters()

        return (
            f"🖥️ *Server Status* ({platform.system()} {platform.release()})\n\n"
            f"⚡ CPU: {cpu}% ({psutil.cpu_count()} cores)\n"
            f"🧠 RAM: {ram.used // (1024**2)} MB / {ram.total // (1024**2)} MB ({ram.percent}%)\n"
            f"💾 Disk: {disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB ({disk.percent}%)\n"
            f"⏱️ Uptime: {uptime}\n"
            f"🌐 Network ↑ {net.bytes_sent // (1024**2)} MB  ↓ {net.bytes_recv // (1024**2)} MB"
        )
    except Exception as e:
        return f"Failed to get system info: {e}"

def get_top_processes(top_n: int = 10) -> str:
    """List the top N processes by CPU usage on the server.

    Args:
        top_n: Number of processes to show (default 10).

    Returns:
        Process list with PID, name, CPU%, and memory%.
    """
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                continue
        procs.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
        out = f"🔍 Top {top_n} processes by CPU:\n\n"
        for p in procs[:top_n]:
            out += f"`{p['pid']:6}` {p['name'][:20]:20} CPU:{p['cpu_percent']:5.1f}% MEM:{p['memory_percent']:.1f}%\n"
        return out
    except Exception as e:
        return f"Failed to list processes: {e}"
