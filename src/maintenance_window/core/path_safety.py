from __future__ import annotations

import re


_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)

_MW_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")


def _is_windows_reserved(value: str) -> bool:
    base = value.split(".", 1)[0].upper()
    return base in _WINDOWS_RESERVED_NAMES


def validate_mw_id(value: str) -> str:
    """Validate one operator-supplied maintenance-window identifier.

    MW IDs become directory names on Windows, so the public contract is
    intentionally strict and deterministic rather than silently rewriting
    operator input.
    """
    text = str(value).strip()
    if not text:
        raise ValueError("MW ID is required.")
    if text in {".", ".."}:
        raise ValueError("MW ID cannot be '.' or '..'.")
    if not _MW_ID_PATTERN.fullmatch(text):
        raise ValueError(
            "MW ID must start with a letter or number and may contain only "
            "letters, numbers, underscore, dash, and dot (maximum 100 characters)."
        )
    if text.endswith("."):
        raise ValueError("MW ID cannot end with a dot on Windows.")
    if _is_windows_reserved(text):
        raise ValueError(f"MW ID uses a reserved Windows name: {text}")
    return text


def safe_path_part(value: str, *, fallback: str = "unknown") -> str:
    """Return one Windows-safe path component for non-MW identifiers."""
    text = str(value).strip()
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join(
        "_" if char in invalid_chars or ord(char) < 32 else char
        for char in text
    )
    cleaned = cleaned.rstrip(" .")
    if cleaned in {"", ".", ".."}:
        return fallback
    if _is_windows_reserved(cleaned):
        cleaned = f"_{cleaned}"
    return cleaned or fallback
