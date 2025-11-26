import aiofiles
import json
from pathlib import Path
from typing import Any


# --------------------------------------
# Base directory for persistent files
# --------------------------------------

here = Path(__file__).parent
files_dir = here / "files_dir"
files_dir.mkdir(exist_ok=True, parents=True)


# --------------------------------------
# Utility Helpers
# --------------------------------------

def _safe_filename(name: str) -> str:
    """
    Converts arbitrary strings (URLs, IDs, titles)
    into safe filesystem-friendly filenames.
    """
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in name)


# --------------------------------------
# Async Writes
# --------------------------------------

async def async_write_text(filename: str, content: str) -> Path:
    """
    Write a UTF-8 text file asynchronously.
    Returns the full file path.
    """
    safe = _safe_filename(filename)
    path = files_dir / safe

    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)

    return path


async def async_write_json(filename: str, data: Any) -> Path:
    """
    Write a JSON file asynchronously.
    """
    safe = _safe_filename(filename)
    path = files_dir / safe

    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    return path


# --------------------------------------
# Async Reads
# --------------------------------------

async def async_read_text(filename: str) -> str:
    """
    Read a UTF-8 text file asynchronously.
    """
    safe = _safe_filename(filename)
    path = files_dir / safe

    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return await f.read()


async def async_read_json(filename: str) -> Any:
    """
    Read and parse a JSON file asynchronously.
    """
    safe = _safe_filename(filename)
    path = files_dir / safe

    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content)