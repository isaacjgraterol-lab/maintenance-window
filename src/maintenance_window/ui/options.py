"""UI options and operator-facing labels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtocolOption:
    value: str
    label: str
    available: bool


PROTOCOL_OPTIONS: tuple[ProtocolOption, ...] = (
    ProtocolOption("bgp", "BGP", True),
)


SOURCE_OPTIONS: tuple[str, ...] = ("pyez", "ssh", "gnmic", "manual")
SOURCE_LABELS: dict[str, str] = {
    "pyez": "PyEZ / NETCONF - Juniper Junos",
    "ssh": "SSH CLI JSON - Juniper Junos",
    "gnmic": "gNMI / OpenConfig - Juniper Junos validated",
    "manual": "Manual JSON/XML",
}
LIVE_SOURCE_OPTIONS: tuple[str, ...] = ("pyez", "ssh", "gnmic")
MODULE_OPTIONS: tuple[str, ...] = ("state", "session-health", "full")
DEVICE_MODE_OPTIONS: tuple[str, ...] = ("individual", "db")
AUTH_BACKEND_OPTIONS: tuple[str, ...] = ("radius", "auto", "local")
WORKER_OPTIONS: tuple[int, ...] = (1, 5, 10, 15, 20)
MANUAL_DB_LIMIT_OPTIONS: tuple[int, ...] = (50, 100, 200, 500)
MANUAL_INPUT_FORMAT_OPTIONS: tuple[str, ...] = ("auto", "json-file", "xml-file")
HEALTH_DEPTH_OPTIONS: tuple[str, ...] = (
    "auto",
    "state-only",
    "partial-health",
    "full-health",
)
CAPTURE_LEVEL_OPTIONS: tuple[str, ...] = ("basic",)

GNMIC_LIMITATION_MESSAGE = (
    "gNMI / OpenConfig is validated on Juniper Junos in v1.0.0. "
    "Cisco IOS XR and Nokia SR OS are future capability-driven research targets, not current support claims. "
    "gNMIc Basic captures BGP neighbor state plus AFI-SAFI state paths. "
    "Fields not exposed by the device OpenConfig/gNMI implementation are reported "
    "as NOT_EVALUATED; peer-as, last-established, established-transitions, "
    "and prefix counters depend on platform support."
)

AUTHOR_BANNER = "Built by Isaac J. Graterol - ChatGPT collaboration"
AUTHOR_EMAIL = "isaacjgraterol@gmail.com"
AUTHOR_LINKEDIN_URL = "https://www.linkedin.com/in/inggraterol"
AUTHOR_LINKEDIN_LABEL = "linkedin.com/in/inggraterol"
GUI_ADMIN_PASSWORD_ENV = "MW_GUI_ADMIN_PASSWORD"

SNAPSHOT_RESULT_MESSAGE = (
    "Snapshot captured successfully. No maintenance-window comparison was "
    "executed. Use Compare Existing MW after both before and after snapshots "
    "are available."
)
