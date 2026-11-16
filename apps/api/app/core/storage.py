from pathlib import Path
from uuid import uuid4

from app.core.config import settings

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "application/octet-stream",
}

def upload_root() -> Path:
    root = Path(settings.upload_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def new_upload_path(filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato não permitido.")
    return upload_root() / f"{uuid4().hex}{suffix}"

def has_video_signature(filename: str, header: bytes) -> bool:
    suffix = Path(filename).suffix.lower()
    if suffix in {".mp4", ".mov"}:
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if suffix in {".webm", ".mkv"}:
        return header.startswith(bytes.fromhex("1A45DFA3"))
    return False
