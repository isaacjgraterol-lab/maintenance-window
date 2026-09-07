from __future__ import annotations

from pathlib import Path
from typing import Any

from maintenance_window.core.audit_manifest import get_pyez_rpc_name
from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.core.output import build_raw_output_path


def collect_pyez(
    device: Device,
    profile: CredentialProfile,
    settings: dict[str, Any],
    output_directory: Path,
) -> Path:
    """Collect BGP summary XML using Junos PyEZ over NETCONF."""
    try:
        from jnpr.junos import Device as JunosDevice
        from lxml import etree
    except ImportError as exc:
        raise RuntimeError(
            "PyEZ is not installed. Run: python -m pip install junos-eznc"
        ) from exc

    pyez_settings = settings.get("pyez", {})
    timeout = int(pyez_settings.get("timeout_seconds", 60))
    port = int(pyez_settings.get("port", 830))
    rpc_name = get_pyez_rpc_name(settings, protocol="bgp")
    verify_host_key = bool(pyez_settings.get("verify_host_key", False))

    try:
        with JunosDevice(
            host=device.host,
            user=profile.username,
            passwd=profile.password,
            port=port,
            gather_facts=False,
            normalize=True,
            auto_probe=0,
            hostkey_verify=verify_host_key,
        ) as connection:
            rpc = getattr(connection.rpc, rpc_name)
            reply = rpc(dev_timeout=timeout)
            xml_text = etree.tostring(reply, encoding="unicode", pretty_print=True)
    except Exception as exc:
        raise RuntimeError(
            f"PyEZ/NETCONF failed for {device.host}:{port}: {exc}"
        ) from exc

    output_path = build_raw_output_path(output_directory, device.host, "xml")
    output_path.write_text(xml_text, encoding="utf-8")
    return output_path
