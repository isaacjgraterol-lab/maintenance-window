from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from maintenance_window.core.credentials import select_profiles
from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp.collectors.gnmic import collect_gnmic
from maintenance_window.protocols.bgp.collectors.pyez import collect_pyez
from maintenance_window.protocols.bgp.collectors.ssh import collect_ssh
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.parsers.gnmic_json import (
    parse_gnmic_json,
)
from maintenance_window.protocols.bgp.parsers.pyez_xml import parse_pyez_xml
from maintenance_window.protocols.bgp.parsers.ssh_json import parse_ssh_json


ProfileSelector = Callable[..., CredentialProfile | Sequence[CredentialProfile]]
Collector = Callable[..., Path]
Parser = Callable[..., list[BgpSession]]
CollectionResult = tuple[list[BgpSession], Path, str]


def _normalize_selected_profiles(
    selected: CredentialProfile | Sequence[CredentialProfile],
) -> list[CredentialProfile]:
    if isinstance(selected, CredentialProfile):
        return [selected]

    return list(selected)


def _select_profile_candidates(
    transport: str,
    defaults: dict[str, object],
    profiles: dict[str, CredentialProfile],
    auth_backend: str,
    select_profile_fn: ProfileSelector,
) -> list[CredentialProfile]:
    try:
        selected = select_profile_fn(
            transport,
            defaults,
            profiles,
            auth_backend=auth_backend,
        )
    except TypeError:
        selected = select_profile_fn(
            transport,
            defaults,
            profiles,
        )

    profile_candidates = _normalize_selected_profiles(selected)

    if not profile_candidates:
        raise ValueError(
            f"No credential profiles selected for {transport}."
        )

    return profile_candidates


def _collect_with_profile_fallback(
    *,
    source: str,
    device: Device,
    profile_candidates: list[CredentialProfile],
    settings: dict[str, Any],
    output_directory: Path,
    collect_fn: Collector,
    parse_fn: Parser,
    parse_kwargs: dict[str, object] | None = None,
) -> CollectionResult:
    errors: list[str] = []

    for profile in profile_candidates:
        try:
            raw_file = collect_fn(
                device=device,
                profile=profile,
                settings=settings,
                output_directory=output_directory,
            )
            if parse_kwargs is None:
                sessions = parse_fn(raw_file, device.host)
            else:
                sessions = parse_fn(raw_file, **parse_kwargs)
            return sessions, raw_file, source
        except Exception as error:
            message = (
                f"{source} profile {profile.name} failed for "
                f"{device.host}. Reason: {error}"
            )
            errors.append(message)
            print(message)

    raise RuntimeError(
        f"All {source} credential profiles failed for {device.host}. "
        f"Errors: {' | '.join(errors)}"
    )


def collect_with_source(
    source: str,
    device: Device,
    defaults: dict[str, object],
    profiles: dict[str, CredentialProfile],
    settings: dict[str, Any],
    project_root: Path,
    *,
    auth_backend: str = "auto",
    select_profile_fn: ProfileSelector = select_profiles,
    collect_ssh_fn: Collector = collect_ssh,
    collect_pyez_fn: Collector = collect_pyez,
    collect_gnmic_fn: Collector = collect_gnmic,
    parse_ssh_fn: Parser = parse_ssh_json,
    parse_pyez_fn: Parser = parse_pyez_xml,
    parse_gnmic_fn: Parser = parse_gnmic_json,
) -> CollectionResult:
    """Collect through one explicit source without applying source fallback."""
    if source == "ssh":
        ssh_profiles = _select_profile_candidates(
            "ssh",
            defaults,
            profiles,
            auth_backend,
            select_profile_fn,
        )
        return _collect_with_profile_fallback(
            source="ssh",
            device=device,
            profile_candidates=ssh_profiles,
            settings=settings,
            output_directory=project_root / "outputs/raw/ssh",
            collect_fn=collect_ssh_fn,
            parse_fn=parse_ssh_fn,
        )

    if source == "pyez":
        pyez_profiles = _select_profile_candidates(
            "pyez",
            defaults,
            profiles,
            auth_backend,
            select_profile_fn,
        )
        return _collect_with_profile_fallback(
            source="pyez",
            device=device,
            profile_candidates=pyez_profiles,
            settings=settings,
            output_directory=project_root / "outputs/raw/pyez",
            collect_fn=collect_pyez_fn,
            parse_fn=parse_pyez_fn,
        )

    if source == "gnmic":
        gnmic_profiles = _select_profile_candidates(
            "gnmic",
            defaults,
            profiles,
            auth_backend,
            select_profile_fn,
        )
        return _collect_with_profile_fallback(
            source="gnmic",
            device=device,
            profile_candidates=gnmic_profiles,
            settings=settings,
            output_directory=project_root / "outputs/raw/gnmic",
            collect_fn=collect_gnmic_fn,
            parse_fn=parse_gnmic_fn,
            parse_kwargs={"fallback_device": device.host},
        )

    raise ValueError(f"Unsupported live source: {source}")
