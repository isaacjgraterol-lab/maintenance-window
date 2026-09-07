from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from maintenance_window.core.models import CredentialProfile


SUPPORTED_AUTH_MODES = frozenset({"profiles"})
SUPPORTED_AUTHENTICATION_BACKENDS = frozenset({"local", "radius"})
SUPPORTED_AUTH_BACKEND_SELECTORS = frozenset({"auto", "local", "radius"})
SUPPORTED_TRANSPORTS = frozenset({"ssh", "pyez", "gnmic"})

CredentialDefaults = dict[str, str | list[str]]


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8-sig") as file_handle:
        return json.load(file_handle)


def _normalize_backend(value: object) -> str:
    backend = str(value or "local").strip().lower()

    if backend not in SUPPORTED_AUTHENTICATION_BACKENDS:
        raise ValueError(
            "Unsupported authentication backend "
            f"{backend!r}. Supported backends: "
            f"{sorted(SUPPORTED_AUTHENTICATION_BACKENDS)}"
        )

    return backend


def _normalize_auth_backend_selector(value: object) -> str:
    selector = str(value or "auto").strip().lower()

    if selector not in SUPPORTED_AUTH_BACKEND_SELECTORS:
        raise ValueError(
            "Unsupported auth backend selector "
            f"{selector!r}. Supported values: "
            f"{sorted(SUPPORTED_AUTH_BACKEND_SELECTORS)}"
        )

    return selector


def _normalize_default_profile_value(
    transport: str,
    value: object,
) -> str | list[str]:
    if isinstance(value, str):
        profile_name = value.strip()
        if not profile_name:
            raise ValueError(
                "Default credential profile cannot be empty for "
                f"{transport}."
            )
        return profile_name

    if isinstance(value, list):
        profile_names: list[str] = []

        for item in value:
            profile_name = str(item).strip()
            if not profile_name:
                raise ValueError(
                    "Default credential profile list contains an empty "
                    f"value for {transport}."
                )
            profile_names.append(profile_name)

        if not profile_names:
            raise ValueError(
                "Default credential profile list cannot be empty for "
                f"{transport}."
            )

        return profile_names

    raise ValueError(
        "Default credential profile must be a string or list of strings "
        f"for {transport}."
    )


def load_credentials(
    path: Path,
) -> tuple[CredentialDefaults, dict[str, CredentialProfile]]:
    """
    Load explicit credential profiles for connection adapters.

    RADIUS-backed profiles still contain a username and password. The
    application sends those credentials through SSH, NETCONF/PyEZ, or gNMIc;
    the network device performs the RADIUS/AAA validation.

    ``default_profiles`` accepts either the original single-profile string or
    an ordered list of profiles. Lists are tried in order by collectors that
    support profile fallback.
    """
    payload = _read_json(path)

    if not isinstance(payload, dict):
        raise ValueError("Credentials file must contain a JSON object.")

    auth_mode = str(payload.get("auth_mode", "profiles")).strip().lower()

    if auth_mode not in SUPPORTED_AUTH_MODES:
        raise ValueError(
            f"Unsupported auth_mode={auth_mode!r}. "
            f"Supported modes: {sorted(SUPPORTED_AUTH_MODES)}"
        )

    default_profiles = payload.get("default_profiles", {})
    raw_profiles = payload.get("profiles", {})

    if not isinstance(default_profiles, dict):
        raise ValueError("default_profiles must be a JSON object.")

    if not isinstance(raw_profiles, dict):
        raise ValueError("profiles must be a JSON object.")

    profiles: dict[str, CredentialProfile] = {}

    for name, record in raw_profiles.items():
        if not isinstance(record, dict):
            raise ValueError(
                f"Credential profile {name!r} must be an object."
            )

        profile_name = str(name)
        profile_type = str(
            record.get("type", "username_password")
        ).strip()
        username = str(record.get("username", ""))
        password = str(record.get("password", ""))
        authentication_backend = _normalize_backend(
            record.get("authentication_backend", "local")
        )

        if not profile_type:
            raise ValueError(
                f"Credential profile {profile_name!r} has no type."
            )

        profiles[profile_name] = CredentialProfile(
            name=profile_name,
            profile_type=profile_type,
            username=username,
            password=password,
            description=str(record.get("description", "")),
            authentication_backend=authentication_backend,
        )

    normalized_defaults = {
        str(key).strip().lower(): _normalize_default_profile_value(
            str(key).strip().lower(),
            value,
        )
        for key, value in default_profiles.items()
    }

    return normalized_defaults, profiles


def _resolve_profile_names(
    transport: str,
    defaults: CredentialDefaults,
) -> list[str]:
    transport_name = transport.strip().lower()

    if transport_name not in SUPPORTED_TRANSPORTS:
        raise ValueError(
            f"Unsupported credential transport {transport_name!r}. "
            f"Supported transports: {sorted(SUPPORTED_TRANSPORTS)}"
        )

    profile_value = defaults.get(transport_name)

    if not profile_value:
        raise ValueError(
            "No default credential profile configured for "
            f"{transport_name}."
        )

    if isinstance(profile_value, str):
        return [profile_value]

    return list(profile_value)


def _validate_profile(
    profile_name: str,
    profiles: dict[str, CredentialProfile],
) -> CredentialProfile:
    try:
        profile = profiles[profile_name]
    except KeyError as exc:
        raise ValueError(
            f"Credential profile not found: {profile_name}"
        ) from exc

    if not profile.username or not profile.password:
        raise ValueError(
            f"Credential profile {profile_name!r} is incomplete."
        )

    return profile


def _filter_profiles_by_backend(
    candidates: Iterable[CredentialProfile],
    auth_backend: str,
) -> list[CredentialProfile]:
    selector = _normalize_auth_backend_selector(auth_backend)

    selected = [
        profile
        for profile in candidates
        if selector == "auto"
        or profile.authentication_backend == selector
    ]

    if not selected:
        raise ValueError(
            "No credential profiles match auth backend "
            f"{selector!r}."
        )

    return selected


def select_profiles(
    transport: str,
    defaults: CredentialDefaults,
    profiles: dict[str, CredentialProfile],
    *,
    auth_backend: str = "auto",
) -> list[CredentialProfile]:
    """Select ordered profiles for one connection adapter."""
    profile_names = _resolve_profile_names(transport, defaults)
    candidates = [
        _validate_profile(profile_name, profiles)
        for profile_name in profile_names
    ]

    return _filter_profiles_by_backend(
        candidates,
        auth_backend,
    )


def select_profile(
    transport: str,
    defaults: CredentialDefaults,
    profiles: dict[str, CredentialProfile],
) -> CredentialProfile:
    """Select and validate the first profile for one connection adapter."""
    return select_profiles(
        transport,
        defaults,
        profiles,
        auth_backend="auto",
    )[0]
