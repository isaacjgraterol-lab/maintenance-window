from __future__ import annotations

from pathlib import Path
from typing import Any

from maintenance_window.core.audit_manifest import get_ssh_command
from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.core.output import build_raw_output_path


def _configure_host_key_policy(client: object, ssh_settings: dict[str, Any], paramiko: object) -> None:
    """Apply Compatibility Mode or Advanced Secure Mode host-key behavior."""
    verify_host_key = bool(ssh_settings.get("verify_host_key", False))
    known_hosts_file = str(ssh_settings.get("known_hosts_file") or "").strip()

    if verify_host_key:
        client.load_system_host_keys()
        if known_hosts_file:
            client.load_host_keys(str(Path(known_hosts_file).expanduser()))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        return

    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def collect_ssh(
    device: Device,
    profile: CredentialProfile,
    settings: dict[str, Any],
    output_directory: Path,
) -> Path:
    """Collect BGP summary JSON using the Junos CLI over SSH."""
    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError(
            "Paramiko is not installed. Run: python -m pip install paramiko"
        ) from exc

    ssh_settings = settings.get("ssh", {})
    port = int(ssh_settings.get("port", 22))
    timeout = int(ssh_settings.get("timeout_seconds", 30))
    command = get_ssh_command(settings, protocol="bgp")

    client = paramiko.SSHClient()
    _configure_host_key_policy(client, ssh_settings, paramiko)

    try:
        client.connect(
            hostname=device.host,
            port=port,
            username=profile.username,
            password=profile.password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        raw_output = stdout.read().decode("utf-8", errors="replace").strip()
        error_output = stderr.read().decode("utf-8", errors="replace").strip()
        exit_status = stdout.channel.recv_exit_status()
    except Exception as exc:
        raise RuntimeError(
            f"SSH collection failed for {device.host}:{port}: {exc}"
        ) from exc
    finally:
        client.close()

    if exit_status != 0:
        raise RuntimeError(
            f"SSH command failed for {device.host}: "
            f"{error_output or f'exit status {exit_status}'}"
        )
    if not raw_output:
        raise RuntimeError(f"SSH command returned no data for {device.host}.")

    output_path = build_raw_output_path(output_directory, device.host, "json")
    output_path.write_text(raw_output, encoding="utf-8")
    return output_path
