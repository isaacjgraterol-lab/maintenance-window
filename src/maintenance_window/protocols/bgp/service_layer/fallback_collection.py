from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.service_layer.explicit_collection import (
    collect_with_source,
)


CollectionResult = tuple[list[BgpSession], Path, str]
ExplicitCollector = Callable[..., CollectionResult]
AUTO_COLLECTOR_ORDER = ("pyez", "gnmic", "ssh")


def _collect_with_optional_auth_backend(
    collect_with_source_fn: ExplicitCollector,
    *,
    source: str,
    auth_backend: str,
    common: dict[str, Any],
) -> CollectionResult:
    try:
        return collect_with_source_fn(
            source=source,
            auth_backend=auth_backend,
            **common,
        )
    except TypeError:
        return collect_with_source_fn(
            source=source,
            **common,
        )


def collect_live(
    source: str,
    device: Device,
    defaults: dict[str, object],
    profiles: dict[str, CredentialProfile],
    settings: dict[str, Any],
    project_root: Path,
    *,
    auth_backend: str = "auto",
    collect_with_source_fn: ExplicitCollector = collect_with_source,
) -> CollectionResult:
    """Collect with the fallback policy associated with the requested source."""
    common = {
        "device": device,
        "defaults": defaults,
        "profiles": profiles,
        "settings": settings,
        "project_root": project_root,
    }

    if source == "ssh":
        return _collect_with_optional_auth_backend(
            collect_with_source_fn,
            source="ssh",
            auth_backend=auth_backend,
            common=common,
        )

    if source in {"pyez", "gnmic"}:
        try:
            return _collect_with_optional_auth_backend(
                collect_with_source_fn,
                source=source,
                auth_backend=auth_backend,
                common=common,
            )
        except Exception as error:
            display_name = "PyEZ" if source == "pyez" else "gNMIc"
            print(
                f"{display_name} failed for {device.host}; trying SSH. "
                f"Reason: {error}"
            )

        return _collect_with_optional_auth_backend(
            collect_with_source_fn,
            source="ssh",
            auth_backend=auth_backend,
            common=common,
        )

    if source == "auto":
        errors: list[str] = []

        for candidate_source in AUTO_COLLECTOR_ORDER:
            try:
                return _collect_with_optional_auth_backend(
                    collect_with_source_fn,
                    source=candidate_source,
                    auth_backend=auth_backend,
                    common=common,
                )
            except Exception as error:
                message = (
                    f"{candidate_source} failed for {device.host}. "
                    f"Reason: {error}"
                )
                errors.append(message)
                print(message)

        raise RuntimeError(
            f"All BGP collectors failed for {device.host}. "
            f"Errors: {' | '.join(errors)}"
        )

    raise ValueError(f"Unsupported BGP live source: {source}")
