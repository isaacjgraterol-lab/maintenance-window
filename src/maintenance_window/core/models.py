from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Device:
    """Device loaded from the TXT inventory."""

    host: str

    @property
    def name(self) -> str:
        return self.host


@dataclass(frozen=True, slots=True)
class CredentialProfile:
    """Username/password profile selected by a connection adapter."""

    name: str
    profile_type: str
    username: str
    password: str = field(repr=False)
    description: str = ""
    authentication_backend: str = "local"
