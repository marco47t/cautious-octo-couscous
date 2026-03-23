import subprocess
import shlex
from utils.logger import logger
from utils.tool_logger import logged_tool

ALLOWED_PREFIXES = [
    "ls", "pwd", "echo", "cat", "head", "tail", "grep",
    "df", "free", "uptime", "ps", "whoami", "hostname",
    "python --version", "python3 --version",
    "pip list", "pip show",
    "git status", "git log --oneline", "git branch", "git diff",
    "ip addr", "systemctl status",
    "du -sh", "env",
]

def _run_command_direct(command: str) -> str:
    """Internal: execute whitelisted command without confirmation."""
    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout or result.stderr or "(no output)"
        return f"```\n$ {command}\n\n{output[:2000]}\n```"
    except subprocess.TimeoutExpired:
        return "⏱️ Command timed out after 15 seconds."
    except Exception as e:
        return f"❌ Failed: {e}"

@logged_tool
def run_shell_command(command: str) -> str:
    """Run a whitelisted shell command on the server — requires confirmation.

    Args:
        command: Shell command to run (e.g. 'df -h', 'git status', 'ps aux').

    Returns:
        Confirmation request or rejection message.
    """
    cmd_lower = command.strip().lower()
    if not any(cmd_lower.startswith(p) for p in ALLOWED_PREFIXES):
        allowed = "\n".join(f"- {p}" for p in ALLOWED_PREFIXES)
        return f"❌ Command not in whitelist.\n\nAllowed:\n{allowed}"

    from bot.confirmation import register_action
    action_id = register_action(
        func=_run_command_direct,
        args={"command": command},
        description=f"Run shell command: `{command}`"
    )
    return (
        f"💻 Ready to run command:\n"
        f"```\n$ {command}\n```\n\n"
        f"CONFIRM_ID:{action_id}"
    )
