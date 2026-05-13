from pathlib import Path
import hashlib
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def save_file_local(original_filename: str, file_bytes: bytes) -> Tuple[str, int, str]:
    """Save bytes to uploads directory, return (storage_path, size, sha256_checksum).

    storage_path is the absolute path string to the saved file.
    """
    # generate a deterministic filename using checksum + original name to avoid collisions
    sha = hashlib.sha256()
    sha.update(file_bytes)
    checksum = sha.hexdigest()

    safe_name = original_filename.replace(" ", "_")
    dest_name = f"{checksum}_{safe_name}"
    dest_path = UPLOADS_DIR / dest_name

    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    return str(dest_path), len(file_bytes), checksum
