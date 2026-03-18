import subprocess
import shlex
from utils.logger import logger

ALLOWED_PREFIXES = [
    "ls", "pwd", "echo", "cat", "head", "tail", "grep",
    "df", "free", "uptime", "ps", "whoami", "hostname",
    "python --version", "python3 --version",
    "pip list", "pip show",
    "git status", "git log --oneline", "git branch", "git diff",
    "ip addr", "systemctl status",
    "du -sh", "env",
]

def run_shell_command(command: str) -> str:
    """Run a whitelisted read-only shell command on the AWS server.

    Args:
        command: Shell command to run (e.g. 'df -h', 'git status', 'ps aux').

    Returns:
        Command stdout/stderr output or a rejection message.
    """
    cmd_lower = command.strip().lower()
    if not any(cmd_lower.startswith(p) for p in ALLOWED_PREFIXES):
        allowed = "\n".join(f"- {p}" for p in ALLOWED_PREFIXES)
        return f"❌ Command not in whitelist.\n\nAllowed:\n{allowed}"
    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout or result.stderr or "(no output)"
        return f"```\n$ {command}\n\n{output[:2000]}\n```"
    except subprocess.TimeoutExpired:
        return "⏱️ Command timed out after 15 seconds."
    except Exception as e:
        logger.error(f"Shell error: {e}")
        return f"❌ Failed: {e}"
