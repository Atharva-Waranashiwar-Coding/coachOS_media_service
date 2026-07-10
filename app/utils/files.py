import re
from pathlib import PurePath

from app.core.exceptions import BadRequestError

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}


def sanitize_filename(value: str) -> str:
    """Remove client path components and preserve only a conservative filename."""
    name = PurePath(value.replace("\\", "/")).name.strip()
    if not name or name in {".", ".."}:
        raise BadRequestError("A valid filename is required.")
    stem, suffix = PurePath(name).stem, PurePath(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise BadRequestError("Unsupported video file extension.")
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not safe_stem:
        raise BadRequestError("A valid filename is required.")
    return f"{safe_stem[:220]}{suffix}"
