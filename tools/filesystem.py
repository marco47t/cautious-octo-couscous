from pathlib import Path
from config import PC_SEARCH_ROOTS
from utils.logger import logger

def _is_safe(path: str) -> bool:
    resolved = Path(path).resolve()
    return any(str(resolved).startswith(str(Path(r).resolve())) for r in PC_SEARCH_ROOTS if r)

def search_files(filename: str) -> str:
    """Search for files on the computer by name or glob pattern (e.g. '*.pdf', 'notes.txt').

    Args:
        filename: Filename or glob pattern to search for.

    Returns:
        List of matching file paths with sizes.
    """
    found = []
    for root in PC_SEARCH_ROOTS:
        if not root:
            continue
        try:
            for match in Path(root).rglob(filename):
                if match.is_file():
                    found.append(match)
                if len(found) >= 20:
                    break
        except PermissionError:
            continue
        except Exception as e:
            logger.error(f"Search error in {root}: {e}")

    if not found:
        return f"No files found matching '{filename}'"
    result = f"Found {len(found)} file(s):\n"
    for f in found:
        result += f"- {f}  ({f.stat().st_size // 1024} KB)\n"
    return result

def read_file(file_path: str, max_chars: int = 5000) -> str:
    """Read the content of a text file from the computer.

    Args:
        file_path: Full absolute path to the file.
        max_chars: Max characters to read (default 5000).

    Returns:
        File content as a string.
    """
    if not _is_safe(file_path):
        return "Access denied: path is outside allowed directories."
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[Truncated — {len(content)} total chars]"
        return f"Content of {path.name}:\n\n{content}"
    except Exception as e:
        return f"Could not read file: {e}"

def list_directory(dir_path: str) -> str:
    """List files and folders inside a directory on the computer.

    Args:
        dir_path: Full path to the directory.

    Returns:
        Directory contents as a formatted list.
    """
    if not _is_safe(dir_path):
        return "Access denied: path is outside allowed directories."
    path = Path(dir_path)
    if not path.is_dir():
        return f"Not a directory: {dir_path}"
    items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
    out = f"Contents of {dir_path}:\n"
    for item in items[:50]:
        icon = "📄" if item.is_file() else "📁"
        out += f"{icon} {item.name}\n"
    return out
