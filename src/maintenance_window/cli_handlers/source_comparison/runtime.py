"""Load credentials and settings for live source comparison."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from maintenance_window.core.credentials import load_credentials
from maintenance_window.core.models import CredentialProfile
from maintenance_window.core.settings import load_runtime_settings
from maintenance_window.cli_handlers.source_comparison.defaults import (
    PROJECT_ROOT,
)
from maintenance_window.cli_handlers.source_comparison.models import (
    SourceComparisonRuntime,
)


LoadCredentials = Callable[
    [Path],
    tuple[dict[str, str], dict[str, CredentialProfile]],
]
LoadSettings = Callable[[argparse.Namespace], dict[str, object]]


def load_protocol_runtime_settings(
    args: argparse.Namespace,
) -> dict[str, object]:
    """Load split connection and protocol audit settings."""
    connection_path = Path(args.connection_settings).resolve()
    audit_path = getattr(args, "audit_settings", None)
    protocol = str(args.protocol).strip().lower()

    if audit_path is None:
        audit_path = (
            PROJECT_ROOT
            / "config"
            / "audits"
            / protocol
            / "state.json"
        )

    return load_runtime_settings(
        protocol=protocol,
        connection_path=connection_path,
        audit_path=Path(audit_path).resolve(),
    )


def build_source_comparison_runtime(
    args: argparse.Namespace,
    *,
    load_credentials_fn: LoadCredentials = load_credentials,
    load_settings_fn: LoadSettings = load_protocol_runtime_settings,
    project_root: Path = PROJECT_ROOT,
) -> SourceComparisonRuntime:
    """Load credentials and runtime settings once for the full run."""
    defaults, profiles = load_credentials_fn(
        Path(args.credentials).resolve()
    )

    return SourceComparisonRuntime(
        defaults=defaults,
        profiles=profiles,
        settings=load_settings_fn(args),
        project_root=project_root,
    )
