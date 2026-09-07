from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maintenance_window.core.audit_manifest import (
    combine_audit_with_evidence,
    normalize_audit_settings,
)


CONNECTION_SETTINGS_KEYS = frozenset({"ssh", "pyez", "gnmic"})


def _load_json_object(
    path: Path,
    *,
    label: str,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} file not found: {path}")

    with path.open("r", encoding="utf-8-sig") as file_handle:
        payload = json.load(file_handle)

    if not isinstance(payload, dict):
        raise ValueError(f"{label} file must contain a JSON object.")

    return payload


def load_connection_settings(path: Path) -> dict[str, Any]:
    """Load settings for connection and collection adapters only."""
    payload = _load_json_object(
        path,
        label="Connection settings",
    )

    if "protocols" in payload:
        raise ValueError(
            "Connection settings must not contain protocol audit settings. "
            "Move them under config/audits/<protocol>/<module>.json."
        )

    invalid_sections = sorted(
        key
        for key, value in payload.items()
        if not isinstance(value, dict)
    )

    if invalid_sections:
        raise ValueError(
            "Each connection settings section must be a JSON object: "
            + ", ".join(invalid_sections)
        )

    return payload


def load_audit_settings(path: Path) -> dict[str, Any]:
    """Load one protocol audit module settings object."""
    return _load_json_object(
        path,
        label="Audit settings",
    )


def compose_runtime_settings(
    *,
    protocol: str,
    connection_settings: dict[str, Any],
    audit_settings: dict[str, Any],
) -> dict[str, Any]:
    """
    Compose the current in-memory collector settings contract.

    Connection and audit configuration remain separate on disk. The nested
    ``protocols`` mapping exists only until the collectors receive independent
    typed settings.
    """
    protocol_name = protocol.strip().lower()

    if not protocol_name:
        raise ValueError("Protocol name cannot be empty.")

    runtime_settings = {
        key: dict(value)
        for key, value in connection_settings.items()
    }
    runtime_settings["protocols"] = {
        protocol_name: normalize_audit_settings(audit_settings),
    }

    return runtime_settings




def _candidate_evidence_paths(
    *,
    protocol: str,
    audit_path: Path,
    reference: str,
) -> list[Path]:
    """Return possible evidence manifest paths for a user-facing reference."""
    text = reference.strip()
    if not text:
        return []

    protocol_root = audit_path.parent
    candidates: list[Path] = []

    def add_candidate(value: Path) -> None:
        path = value if value.is_absolute() else protocol_root / value
        if path not in candidates:
            candidates.append(path)

    normalized = text.replace("\\", "/")
    if normalized.endswith(".json") or "/" in normalized:
        add_candidate(Path(normalized))
        return candidates

    aliases = {
        "basic": "evidence_basic.json",
        "evidence_basic": "evidence_basic.json",
        f"{protocol}.evidence.basic": "evidence_basic.json",
        f"{protocol}.evidence_basic": "evidence_basic.json",
    }
    if normalized in aliases:
        add_candidate(Path(aliases[normalized]))
        return candidates

    if normalized.startswith(f"{protocol}.evidence."):
        level = normalized.removeprefix(f"{protocol}.evidence.").replace(".", "_")
        add_candidate(Path(f"evidence_{level}.json"))
        return candidates

    add_candidate(Path(f"{normalized}.json"))
    return candidates


def _resolve_audit_evidence(
    *,
    protocol: str,
    audit_path: Path,
    audit_settings: dict[str, Any],
) -> dict[str, Any]:
    """Load reusable evidence when an analysis manifest declares uses_evidence."""
    reference = audit_settings.get("uses_evidence")
    if not reference:
        return audit_settings
    if not isinstance(reference, str):
        raise ValueError("uses_evidence must be a string when present.")

    for candidate in _candidate_evidence_paths(
        protocol=protocol,
        audit_path=audit_path,
        reference=reference,
    ):
        if candidate.exists():
            evidence_settings = load_audit_settings(candidate)
            return combine_audit_with_evidence(
                audit_settings=audit_settings,
                evidence_settings=evidence_settings,
            )

    searched = ", ".join(
        str(path)
        for path in _candidate_evidence_paths(
            protocol=protocol,
            audit_path=audit_path,
            reference=reference,
        )
    )
    raise FileNotFoundError(
        f"Evidence settings {reference!r} not found. Searched: {searched}"
    )

def load_runtime_settings(
    *,
    protocol: str,
    connection_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    """Load split settings files and compose the runtime collector contract."""
    protocol_name = protocol.strip().lower()
    resolved_audit_path = audit_path.resolve()
    audit_settings = load_audit_settings(resolved_audit_path)
    audit_settings = _resolve_audit_evidence(
        protocol=protocol_name,
        audit_path=resolved_audit_path,
        audit_settings=audit_settings,
    )

    return compose_runtime_settings(
        protocol=protocol_name,
        connection_settings=load_connection_settings(connection_path),
        audit_settings=audit_settings,
    )
