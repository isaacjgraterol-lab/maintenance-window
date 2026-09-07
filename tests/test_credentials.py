from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintenance_window.core.credentials import (
    load_credentials,
    select_profile,
)
from maintenance_window.core.models import CredentialProfile


def write_credentials(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_loads_radius_backed_profile(
    tmp_path: Path,
) -> None:
    credentials_file = tmp_path / "credentials.json"
    write_credentials(
        credentials_file,
        {
            "auth_mode": "profiles",
            "default_profiles": {
                "ssh": "radius_network",
                "pyez": "radius_network",
                "gnmic": "gnmic_local",
            },
            "profiles": {
                "radius_network": {
                    "type": "username_password",
                    "authentication_backend": "radius",
                    "username": "netops",
                    "password": "secret",
                },
                "gnmic_local": {
                    "type": "username_password",
                    "authentication_backend": "local",
                    "username": "gnmic",
                    "password": "secret",
                },
            },
        },
    )

    defaults, profiles = load_credentials(credentials_file)

    assert defaults["pyez"] == "radius_network"
    assert (
        profiles["radius_network"].authentication_backend
        == "radius"
    )


def test_selects_explicit_pyez_profile() -> None:
    profile = CredentialProfile(
        name="pyez_radius",
        profile_type="username_password",
        username="netops",
        password="secret",
        authentication_backend="radius",
    )

    selected = select_profile(
        "pyez",
        {"pyez": "pyez_radius"},
        {"pyez_radius": profile},
    )

    assert selected is profile


def test_pyez_requires_explicit_default_profile() -> None:
    profile = CredentialProfile(
        name="ssh_local",
        profile_type="username_password",
        username="netops",
        password="secret",
    )

    with pytest.raises(
        ValueError,
        match="No default credential profile configured for pyez",
    ):
        select_profile(
            "pyez",
            {"ssh": "ssh_local"},
            {"ssh_local": profile},
        )


def test_missing_exact_default_is_rejected() -> None:
    profile = CredentialProfile(
        name="ssh_local",
        profile_type="username_password",
        username="netops",
        password="secret",
    )

    with pytest.raises(
        ValueError,
        match="No default credential profile configured for gnmic",
    ):
        select_profile(
            "gnmic",
            {"ssh": "ssh_local"},
            {"ssh_local": profile},
        )


def test_unknown_authentication_backend_is_rejected(
    tmp_path: Path,
) -> None:
    credentials_file = tmp_path / "credentials.json"
    write_credentials(
        credentials_file,
        {
            "auth_mode": "profiles",
            "default_profiles": {"ssh": "invalid"},
            "profiles": {
                "invalid": {
                    "type": "username_password",
                    "authentication_backend": "tacacs",
                    "username": "netops",
                    "password": "secret",
                }
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="Unsupported authentication backend",
    ):
        load_credentials(credentials_file)


def test_profile_defaults_to_local_backend(
    tmp_path: Path,
) -> None:
    credentials_file = tmp_path / "credentials.json"
    write_credentials(
        credentials_file,
        {
            "auth_mode": "profiles",
            "default_profiles": {"ssh": "ssh_local"},
            "profiles": {
                "ssh_local": {
                    "type": "username_password",
                    "username": "netops",
                    "password": "secret",
                }
            },
        },
    )

    _defaults, profiles = load_credentials(credentials_file)

    assert profiles["ssh_local"].authentication_backend == "local"


def test_example_declares_explicit_transport_defaults() -> None:
    example_path = Path("auth/credentials.example.json")
    payload = json.loads(
        example_path.read_text(encoding="utf-8")
    )

    defaults = payload["default_profiles"]
    profiles = payload["profiles"]

    assert set(defaults) == {"ssh", "pyez", "gnmic"}
    assert (
        profiles["network_radius"]["authentication_backend"]
        == "radius"
    )


def test_gnmic_insecure_setting_belongs_to_connections() -> None:
    path = Path("config/connections/settings.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["gnmic"]["insecure"] is True


def test_load_credentials_accepts_utf8_bom(tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_bytes(
        b'\xef\xbb\xbf{"auth_mode":"profiles","default_profiles":{"ssh":"demo"},"profiles":{"demo":{"type":"username_password","username":"operator","password":"password"}}}'
    )
    defaults, profiles = load_credentials(credentials_file)
    assert defaults["ssh"] == "demo"
    assert profiles["demo"].username == "operator"
