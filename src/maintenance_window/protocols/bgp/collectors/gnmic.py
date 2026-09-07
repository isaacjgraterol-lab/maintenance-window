from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from maintenance_window.core.audit_manifest import get_gnmi_paths
from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.core.output import build_raw_output_path


def _append_tls_options(command: list[str], gnmic_settings: dict[str, Any]) -> None:
    """Append gNMI TLS flags for Advanced Secure Mode."""
    if bool(gnmic_settings.get("skip_verify", False)):
        command.append("--skip-verify")

    for setting_name, flag in (
        ("tls_ca", "--tls-ca"),
        ("tls_cert", "--tls-cert"),
        ("tls_key", "--tls-key"),
        ("tls_server_name", "--tls-server-name"),
    ):
        value = str(gnmic_settings.get(setting_name) or "").strip()
        if value:
            command.extend([flag, value])


def collect_gnmic(
    device: Device,
    profile: CredentialProfile,
    settings: dict[str, Any],
    output_directory: Path,
) -> Path:
    """Collect BGP state using a one-time gNMIc subscription."""
    gnmic_settings = settings.get("gnmic", {})
    command_prefix = gnmic_settings.get("command_prefix", ["gnmic"])
    paths = get_gnmi_paths(settings, protocol="bgp")
    port = int(gnmic_settings.get("port", 57400))

    if not isinstance(command_prefix, list) or not command_prefix:
        raise ValueError("gnmic.command_prefix must be a non-empty list.")

    if not isinstance(paths, list) or not paths:
        raise ValueError("At least one BGP gNMI path must be configured.")

    command = [str(part) for part in command_prefix]
    command.extend(
        [
            "-a",
            f"{device.host}:{port}",
            "-u",
            profile.username,
            "-p",
            profile.password,
            "--format",
            str(gnmic_settings.get("format", "protojson")),
            "--encoding",
            str(gnmic_settings.get("encoding", "proto")),
        ]
    )

    insecure = bool(gnmic_settings.get("insecure", False))
    if insecure:
        command.append("--insecure")
    else:
        _append_tls_options(command, gnmic_settings)

    command.extend(["subscribe", "--mode", "once"])

    for path in paths:
        command.extend(["--path", str(path)])

    timeout = int(gnmic_settings.get("timeout_seconds", 60))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "gNMIc executable was not found. "
            f"Command prefix: {command_prefix}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"gNMIc timed out after {timeout} seconds "
            f"for {device.host}."
        ) from exc

    if completed.returncode != 0:
        error_text = completed.stderr.strip() or "Unknown gNMIc error"
        raise RuntimeError(f"gNMIc failed for {device.host}: {error_text}")

    if not completed.stdout.strip():
        raise RuntimeError(f"gNMIc returned no data for {device.host}.")

    output_path = build_raw_output_path(output_directory, device.host, "json")
    output_path.write_text(completed.stdout, encoding="utf-8")
    return output_path
