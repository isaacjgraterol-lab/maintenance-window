from __future__ import annotations


_SOURCE_ALIASES = {
    "gnmi": "gnmic",
    "gnmic": "gnmic",
    "openconfig": "gnmic",
    "pyez": "pyez",
    "netconf": "pyez",
    "ssh": "ssh",
    "cli": "ssh",
    "manual": "manual",
    "local db": "manual",
    "local-db": "manual",
    "unknown": "unknown",
    "": "unknown",
}


def normalize_source_name(value: object) -> str:
    """Normalize source metadata used by official MW comparisons."""
    text = str(value or "").strip().lower()
    return _SOURCE_ALIASES.get(text, text)


def validate_same_actual_source(
    before_source: object,
    after_source: object,
) -> None:
    """Reject cross-source PRE/POST comparisons.

    Cross-source checks remain available through the dedicated source
    comparison workflow. Official maintenance-window results must compare
    evidence produced by the same collection method.
    """
    before = normalize_source_name(before_source)
    after = normalize_source_name(after_source)
    if before == after:
        return

    raise ValueError(
        "Official before/after BGP comparison requires the same "
        f"source_actual for both snapshots ({before!r} != {after!r}). "
        "Use the dedicated source-comparison workflow for cross-source "
        "diagnostics."
    )
