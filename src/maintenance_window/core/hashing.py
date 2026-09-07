from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    """
    Calculate SHA256 hash for a file.

    Used to identify duplicate manual uploads and keep an audit trail.
    """
    sha256 = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()
