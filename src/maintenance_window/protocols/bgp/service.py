"""Public facade for BGP file parsing, live collection, and comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maintenance_window.core.credentials import select_profiles
from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp.collectors.gnmic import collect_gnmic
from maintenance_window.protocols.bgp.collectors.pyez import collect_pyez
from maintenance_window.protocols.bgp.collectors.ssh import collect_ssh
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.parsers.gnmic_json import parse_gnmic_json
from maintenance_window.protocols.bgp.parsers.json_auto import parse_json_bgp_file
from maintenance_window.protocols.bgp.parsers.pyez_xml import parse_pyez_xml
from maintenance_window.protocols.bgp.parsers.ssh_json import parse_ssh_json
from maintenance_window.protocols.bgp.service_layer.explicit_collection import (
    collect_with_source as _collect_with_source,
)
from maintenance_window.protocols.bgp.service_layer.fallback_collection import (
    collect_live as _collect_live,
)
from maintenance_window.protocols.bgp.service_layer.file_input import (
    parse_input_file as _parse_input_file,
)
from maintenance_window.protocols.bgp.service_layer.live_comparison import (
    compare_live_sources as _compare_live_sources,
)
from maintenance_window.protocols.bgp.source_comparison.comparison import compare_bgp_sources
from maintenance_window.protocols.bgp.source_comparison.models import BgpSourceComparison


def parse_input_file(
    path: Path,
    source: str,
    fallback_device: str,
) -> list[BgpSession]:
    return _parse_input_file(
        path=path,
        source=source,
        fallback_device=fallback_device,
        parse_json_fn=parse_json_bgp_file,
        parse_xml_fn=parse_pyez_xml,
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
) -> tuple[list[BgpSession], Path, str]:
    return _collect_with_source(
        source=source,
        device=device,
        defaults=defaults,
        profiles=profiles,
        settings=settings,
        project_root=project_root,
        auth_backend=auth_backend,
        select_profile_fn=select_profiles,
        collect_ssh_fn=collect_ssh,
        collect_pyez_fn=collect_pyez,
        collect_gnmic_fn=collect_gnmic,
        parse_ssh_fn=parse_ssh_json,
        parse_pyez_fn=parse_pyez_xml,
        parse_gnmic_fn=parse_gnmic_json,
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
) -> tuple[list[BgpSession], Path, str]:
    return _collect_live(
        source=source,
        device=device,
        defaults=defaults,
        profiles=profiles,
        settings=settings,
        project_root=project_root,
        auth_backend=auth_backend,
        collect_with_source_fn=collect_with_source,
    )


def compare_live_sources(
    left_source: str,
    right_source: str,
    device: Device,
    defaults: dict[str, object],
    profiles: dict[str, CredentialProfile],
    settings: dict[str, Any],
    project_root: Path,
) -> tuple[BgpSourceComparison, dict[str, Path], dict[str, str]]:
    return _compare_live_sources(
        left_source=left_source,
        right_source=right_source,
        device=device,
        defaults=defaults,
        profiles=profiles,
        settings=settings,
        project_root=project_root,
        collect_with_source_fn=collect_with_source,
        compare_bgp_sources_fn=compare_bgp_sources,
    )
