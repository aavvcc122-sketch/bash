
import os, re, uuid, shutil
from pathlib import Path

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))

# Restrictive filename policy to avoid risky content
FORBIDDEN_PATTERNS = [
    r"tdata", r"\.session\b", r"\btelegram[-_ ]?desktop\b", r"\buser[-_ ]?data\b"
]
FORBIDDEN_EXTENSIONS = {".json", ".sqlite", ".db"}

ALLOWED_EXTENSIONS = {".zip", ".pdf", ".png", ".jpg", ".jpeg", ".txt", ".csv"}

def is_filename_allowed(name: str) -> bool:
    lname = name.lower()
    if any(re.search(p, lname) for p in FORBIDDEN_PATTERNS):
        return False
    ext = Path(lname).suffix
    if ext in FORBIDDEN_EXTENSIONS:
        return False
    if ext not in ALLOWED_EXTENSIONS:
        # keep strict allowlist
        return False
    return True

def save_upload(temp_file_path: str, original_name: str) -> tuple[str, int]:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix.lower()
    new_name = f"{uuid.uuid4().hex}{ext}"
    dst = STORAGE_DIR / new_name
    shutil.copyfile(temp_file_path, dst)
    size = dst.stat().st_size
    return str(dst), size

def price_to_str(cents: int) -> str:
    return f"{cents/100:.2f}"
