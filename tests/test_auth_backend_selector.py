from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintenance_window.core.credentials import (
    load_credentials,
    select_profile,
    select_profiles,
)
from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.service_layer.explicit_collection import (
    collect_with_source,
)


def _write_credentials(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _credentials_payload() -> dict[str, object]:
    return {
        "auth_mode": "profiles",
        "default_profiles": {
            "ssh": ["lab_local", "network_radius"],
            "pyez": ["lab_local", "network_radius"],
            "gnmic": ["gnmic_local"],
        },
        "profiles": {
            "lab_local": {
                "type": "username_password",
                "authentication_backend": "local",
                "username": "local_user",
                "password": "local_password",
            },
            "network_radius": {
                "type": "username_password",
                "authentication_backend": "radius",
                "username": "radius_user",
                "password": "radius_password",
            },
            "gnmic_local": {
                "type": "username_password",
                "authentication_backend": "local",
                "username": "gnmic_user",
                "password": "gnmic_password",
            },
        },
    }


def test_load_credentials_accepts_ordered_profile_lists(tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.json"
    _write_credentials(credentials_file, _credentials_payload())

    defaults, profiles = load_credentials(credentials_file)

    assert defaults["ssh"] == ["lab_local", "network_radius"]
    assert profiles["lab_local"].authentication_backend == "local"
    assert profiles["network_radius"].authentication_backend == "radius"


def test_select_profile_keeps_single_profile_compatibility(
    tmp_path: Path,
) -> None:
    credentials_file = tmp_path / "credentials.json"
    payload = _credentials_payload()
    payload["default_profiles"] = {"ssh": "network_radius"}
    _write_credentials(credentials_file, payload)

    defaults, profiles = load_credentials(credentials_file)

    selected = select_profile("ssh", defaults, profiles)

    assert selected.name == "network_radius"


def test_select_profiles_filters_by_auth_backend(tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.json"
    _write_credentials(credentials_file, _credentials_payload())

    defaults, profiles = load_credentials(credentials_file)

    auto_profiles = select_profiles("ssh", defaults, profiles)
    local_profiles = select_profiles(
        "ssh",
        defaults,
        profiles,
        auth_backend="local",
    )
    radius_profiles = select_profiles(
        "ssh",
        defaults,
        profiles,
        auth_backend="radius",
    )

    assert [profile.name for profile in auto_profiles] == [
        "lab_local",
        "network_radius",
    ]
    assert [profile.name for profile in local_profiles] == ["lab_local"]
    assert [profile.name for profile in radius_profiles] == [
        "network_radius",
    ]


def test_select_profiles_rejects_missing_backend_match(
    tmp_path: Path,
) -> None:
    credentials_file = tmp_path / "credentials.json"
    payload = _credentials_payload()
    payload["default_profiles"] = {"ssh": ["lab_local"]}
    _write_credentials(credentials_file, payload)

    defaults, profiles = load_credentials(credentials_file)

    with pytest.raises(ValueError, match="No credential profiles match"):
        select_profiles(
            "ssh",
            defaults,
            profiles,
            auth_backend="radius",
        )


def test_collect_with_source_tries_next_profile_after_failure(
    tmp_path: Path,
) -> None:
    device = Device(host="198.51.100.13")
    local_profile = CredentialProfile(
        name="lab_local",
        profile_type="username_password",
        username="local_user",
        password="local_password",
        authentication_backend="local",
    )
    radius_profile = CredentialProfile(
        name="network_radius",
        profile_type="username_password",
        username="radius_user",
        password="radius_password",
        authentication_backend="radius",
    )
    attempts: list[str] = []

    def fake_select_profiles(*_args: object, **_kwargs: object):
        return [local_profile, radius_profile]

    def fake_collect_ssh(
        *,
        device: Device,
        profile: CredentialProfile,
        settings: dict[str, object],
        output_directory: Path,
    ) -> Path:
        attempts.append(profile.name)
        if profile.name == "lab_local":
            raise RuntimeError("Authentication failed.")
        raw_file = output_directory / f"{device.host}.json"
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text("{}", encoding="utf-8")
        return raw_file

    def fake_parse_ssh(
        raw_file: Path,
        device_name: str,
    ) -> list[BgpSession]:
        return [
            BgpSession(
                device=device_name,
                neighbor="192.0.2.1",
                state="Established",
            )
        ]

    sessions, raw_file, actual_source = collect_with_source(
        source="ssh",
        device=device,
        defaults={"ssh": ["lab_local", "network_radius"]},
        profiles={
            "lab_local": local_profile,
            "network_radius": radius_profile,
        },
        settings={},
        project_root=tmp_path,
        select_profile_fn=fake_select_profiles,
        collect_ssh_fn=fake_collect_ssh,
        parse_ssh_fn=fake_parse_ssh,
    )

    assert attempts == ["lab_local", "network_radius"]
    assert actual_source == "ssh"
    assert raw_file.name == "198.51.100.13.json"
    assert sessions[0].state == "Established"
