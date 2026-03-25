import subprocess
import sys
import tempfile
import os
from pathlib import Path
from utils.logger import logger
from utils.tool_logger import logged_tool


@logged_tool
def run_python_code(code: str, timeout: int = 15) -> str:
    """Execute Python code and return stdout, stderr, and exit code.
    Use this to test code you've written before giving it to the user.

    Args:
        code: Python code string to execute.
        timeout: Max seconds to run (default 15).

    Returns:
        Execution result with stdout, stderr, and exit code.
    """
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp = f.name

        result = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=timeout
        )

        output = []
        if result.stdout.strip():
            output.append(f"stdout:\n{result.stdout.strip()[:1000]}")
        if result.stderr.strip():
            output.append(f"stderr:\n{result.stderr.strip()[:500]}")
        output.append(f"exit_code: {result.returncode}")

        status = "✅ Success" if result.returncode == 0 else "❌ Failed"
        return f"{status}\n\n" + "\n\n".join(output)

    except subprocess.TimeoutExpired:
        return f"❌ Timed out after {timeout}s"
    except Exception as e:
        return f"❌ Runner error: {e}"
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


@logged_tool
def run_shell_test(command: str, timeout: int = 30) -> str:
    """Run a shell command to verify something works (install check, file exists, etc).
    Use this to confirm dependencies are installed or validate outputs.

    Args:
        command: Shell command to run.
        timeout: Max seconds.

    Returns:
        stdout, stderr, exit code.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        out = result.stdout.strip()[:500]
        err = result.stderr.strip()[:300]
        status = "✅" if result.returncode == 0 else "❌"
        parts = [f"{status} exit_code={result.returncode}"]
        if out:
            parts.append(f"stdout: {out}")
        if err:
            parts.append(f"stderr: {err}")
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return f"❌ Timed out after {timeout}s"
    except Exception as e:
        return f"❌ {e}"
