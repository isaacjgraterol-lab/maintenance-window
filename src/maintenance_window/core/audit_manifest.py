from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


DEFAULT_BGP_SSH_COMMAND = "show bgp summary | display json | no-more"
DEFAULT_BGP_PYEZ_RPC = "get_bgp_summary_information"
DEFAULT_BGP_GNMI_PATH = (
    "/network-instances/network-instance/protocols/protocol/bgp/"
    "neighbors/neighbor/state/session-state"
)
DEFAULT_BGP_GNMI_BASIC_PATHS = (
    "/network-instances/network-instance/protocols/protocol/bgp/"
    "neighbors/neighbor/state",
    "/network-instances/network-instance/protocols/protocol/bgp/"
    "neighbors/neighbor/afi-safis/afi-safi/state",
)

_SOURCE_ALIASES = {
    "gnmi": ("gnmi", "gnmic"),
    "gnmic": ("gnmic", "gnmi"),
}


def _protocol_settings(
    settings: dict[str, Any],
    protocol: str,
) -> dict[str, Any]:
    protocols = settings.get("protocols", {})
    if not isinstance(protocols, dict):
        return {}

    payload = protocols.get(protocol, {})
    return payload if isinstance(payload, dict) else {}


def _source_names(source: str) -> tuple[str, ...]:
    normalized = source.strip().lower()
    return _SOURCE_ALIASES.get(normalized, (normalized,))


def _source_config(
    protocol_settings: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    sources = protocol_settings.get("sources", {})
    if not isinstance(sources, dict):
        return {}

    for source_name in _source_names(source):
        payload = sources.get(source_name)
        if isinstance(payload, dict):
            return payload
    return {}


def _enabled(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("enabled", True))
    return True


def _items_from_source_config(source_config: dict[str, Any]) -> list[dict[str, Any]]:
    if not source_config or not _enabled(source_config):
        return []

    raw_items = source_config.get("items", [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict) and _enabled(item):
            items.append(item)
    return items


def iter_source_items(
    settings: dict[str, Any],
    *,
    protocol: str,
    source: str,
) -> Iterable[dict[str, Any]]:
    """Yield enabled manifest items for one protocol/source.

    This supports the new manifest format under
    ``protocols.<protocol>.sources.<source>.items``. It intentionally does not
    execute anything; collectors decide how to use the returned declaration.
    """
    protocol_payload = _protocol_settings(settings, protocol)
    yield from _items_from_source_config(_source_config(protocol_payload, source))


def first_source_item(
    settings: dict[str, Any],
    *,
    protocol: str,
    source: str,
    name: str | None = None,
) -> dict[str, Any] | None:
    """Return the first enabled manifest item, optionally matching by name."""
    items = list(
        iter_source_items(settings, protocol=protocol, source=source)
    )
    if name is None:
        return items[0] if items else None

    for item in items:
        if str(item.get("name", "")).strip().lower() == name.lower():
            return item
    return None


def get_ssh_command(
    settings: dict[str, Any],
    *,
    protocol: str = "bgp",
    item_name: str = "bgp_summary",
    default: str = DEFAULT_BGP_SSH_COMMAND,
) -> str:
    """Resolve the SSH command from manifest settings or legacy settings."""
    protocol_payload = _protocol_settings(settings, protocol)

    item = first_source_item(
        settings,
        protocol=protocol,
        source="ssh",
        name=item_name,
    ) or first_source_item(
        settings,
        protocol=protocol,
        source="ssh",
    )
    if item is not None and item.get("command"):
        return str(item["command"])

    return str(protocol_payload.get("ssh_command", default))


def get_pyez_rpc_name(
    settings: dict[str, Any],
    *,
    protocol: str = "bgp",
    item_name: str = "bgp_summary",
    default: str = DEFAULT_BGP_PYEZ_RPC,
) -> str:
    """Resolve the PyEZ RPC method name from manifest or legacy settings."""
    protocol_payload = _protocol_settings(settings, protocol)

    item = first_source_item(
        settings,
        protocol=protocol,
        source="pyez",
        name=item_name,
    ) or first_source_item(
        settings,
        protocol=protocol,
        source="pyez",
    )
    if item is not None and item.get("rpc"):
        return str(item["rpc"])

    return str(protocol_payload.get("pyez_rpc", default))


def get_gnmi_paths(
    settings: dict[str, Any],
    *,
    protocol: str = "bgp",
    default: list[str] | None = None,
) -> list[str]:
    """Resolve gNMI/gNMIc paths from manifest settings or legacy settings."""
    protocol_payload = _protocol_settings(settings, protocol)
    paths: list[str] = []

    for item in iter_source_items(settings, protocol=protocol, source="gnmic"):
        if item.get("path"):
            paths.append(str(item["path"]))
        raw_paths = item.get("paths")
        if isinstance(raw_paths, list):
            paths.extend(str(path) for path in raw_paths if str(path).strip())

    if paths:
        return paths

    legacy_paths = protocol_payload.get("gnmic_paths")
    if isinstance(legacy_paths, list):
        return [str(path) for path in legacy_paths if str(path).strip()]

    return list(default or DEFAULT_BGP_GNMI_BASIC_PATHS)


def combine_audit_with_evidence(
    audit_settings: dict[str, Any],
    evidence_settings: dict[str, Any],
) -> dict[str, Any]:
    """Merge an analysis manifest with its reusable evidence manifest.

    ``audit_settings`` describes what a module analyzes.
    ``evidence_settings`` describes what is captured from devices.

    Runtime collectors need the evidence ``sources`` and legacy convenience
    keys, while reports still need to know the requested module/scope.  This
    function keeps module metadata from the analysis manifest and capture
    metadata from the evidence manifest.
    """
    normalized_evidence = normalize_audit_settings(evidence_settings)
    combined = deepcopy(normalized_evidence)

    evidence_module = combined.get("module")
    evidence_capture_level = combined.get("capture_level")

    for key, value in audit_settings.items():
        if key == "sources":
            continue
        combined[key] = deepcopy(value)

    if evidence_module is not None:
        combined["evidence_module"] = evidence_module
    if evidence_capture_level is not None:
        combined["evidence_capture_level"] = evidence_capture_level

    combined.setdefault("reusable_evidence", True)
    combined.setdefault("no_per_module_recapture", True)

    return normalize_audit_settings(combined)


def _source_items_from_manifest(
    audit_settings: dict[str, Any],
    source: str,
) -> list[dict[str, Any]]:
    runtime_settings = {"protocols": {"_audit": audit_settings}}
    return list(
        iter_source_items(
            runtime_settings,
            protocol="_audit",
            source=source,
        )
    )


def normalize_audit_settings(
    audit_settings: dict[str, Any],
) -> dict[str, Any]:
    """Return a runtime-safe copy of audit settings.

    New module manifests are preserved, but legacy collector keys are derived
    from the manifest so existing collectors and tests can keep working during
    the transition:

    - ``ssh_command`` from the SSH item command.
    - ``pyez_rpc`` from the PyEZ item RPC.
    - ``gnmic_paths`` from the gNMI/gNMIc item path(s).
    """
    normalized = deepcopy(audit_settings)

    if not isinstance(normalized.get("sources"), dict):
        return normalized

    ssh_items = _source_items_from_manifest(normalized, "ssh")
    if "ssh_command" not in normalized:
        for item in ssh_items:
            if item.get("command"):
                normalized["ssh_command"] = str(item["command"])
                break

    pyez_items = _source_items_from_manifest(normalized, "pyez")
    if "pyez_rpc" not in normalized:
        for item in pyez_items:
            if item.get("rpc"):
                normalized["pyez_rpc"] = str(item["rpc"])
                break

    gnmi_paths: list[str] = []
    for item in _source_items_from_manifest(normalized, "gnmic"):
        if item.get("path"):
            gnmi_paths.append(str(item["path"]))
        raw_paths = item.get("paths")
        if isinstance(raw_paths, list):
            gnmi_paths.extend(str(path) for path in raw_paths if str(path).strip())

    if "gnmic_paths" not in normalized and gnmi_paths:
        normalized["gnmic_paths"] = gnmi_paths

    return normalized
