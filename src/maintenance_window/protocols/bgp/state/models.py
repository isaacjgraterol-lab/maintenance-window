from __future__ import annotations

from dataclasses import asdict, dataclass


_STATE_MAP = {
    "ESTABL": "Established",
    "ESTABLISHED": "Established",
    "IDLE": "Idle",
    "CONNECT": "Connect",
    "ACTIVE": "Active",
    "OPENSENT": "OpenSent",
    "OPENCONFIRM": "OpenConfirm",
    "UNKNOWN": "Unknown",
}


def normalize_state(value: object) -> str:
    text = str(value).strip()
    if not text:
        return "Unknown"

    compact = text.replace("_", "").replace("-", "").replace(" ", "").upper()
    return _STATE_MAP.get(compact, text)


@dataclass(frozen=True, slots=True)
class BgpSession:
    device: str
    neighbor: str
    state: str

    @property
    def is_healthy(self) -> bool:
        return self.state == "Established"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
