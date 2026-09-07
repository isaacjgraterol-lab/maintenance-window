from __future__ import annotations

import re

_WEEK_DAY_RE = re.compile(r"^(?:(?P<weeks>\d+)w)?(?:(?P<days>\d+)d)?$", re.IGNORECASE)
_DAY_TIME_RE = re.compile(
    r"^(?:(?P<weeks>\d+)w)?(?:(?P<days>\d+)d)?\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?)$",
    re.IGNORECASE,
)


def _split_time_to_seconds(value: str) -> int | None:
    parts = value.split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None

    if len(numbers) == 3:
        hours, minutes, seconds = numbers
    elif len(numbers) == 2:
        hours = 0
        minutes, seconds = numbers
    else:
        return None

    if minutes >= 60 or seconds >= 60:
        return None

    return hours * 3600 + minutes * 60 + seconds


def parse_bgp_uptime_to_seconds(value: object | None) -> int | None:
    """Parse common Junos BGP elapsed-time strings into seconds.

    The XML/JSON `junos:seconds` attribute remains the preferred value when it is
    available.  This helper is used only as a fallback when raw data has elapsed
    text but no seconds attribute.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.isdigit():
        return int(text)

    compact = text.replace(" ", "")
    match = _WEEK_DAY_RE.match(compact)
    if match and (match.group("weeks") or match.group("days")):
        weeks = int(match.group("weeks") or 0)
        days = int(match.group("days") or 0)
        return weeks * 7 * 86400 + days * 86400

    match = _DAY_TIME_RE.match(compact)
    if match:
        weeks = int(match.group("weeks") or 0)
        days = int(match.group("days") or 0)
        time_seconds = _split_time_to_seconds(match.group("time"))
        if time_seconds is None:
            return None
        return weeks * 7 * 86400 + days * 86400 + time_seconds

    # Pure time without day/week prefix: HH:MM:SS or MM:SS.
    if ":" in text:
        return _split_time_to_seconds(text)

    return None
