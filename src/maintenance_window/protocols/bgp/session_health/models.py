from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BgpFamilyHealthCounters:
    """Per-family/table BGP counters already present in raw output."""

    table: str
    family: str
    rib_state: list[str] = field(default_factory=list)
    send_state: str | None = None
    active_prefix_count: int | None = None
    received_prefix_count: int | None = None
    accepted_prefix_count: int | None = None
    suppressed_prefix_count: int | None = None
    advertised_prefix_count: int | None = None

    @property
    def key(self) -> str:
        return self.table

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BgpSessionHealthRecord:
    """Peer-level BGP health data extracted from raw snapshot output."""

    device: str
    neighbor: str
    peer_state: str
    peer_as: int | None = None
    elapsed_time_raw: str | None = None
    elapsed_time_seconds: int | None = None
    flap_count: int | None = None
    enabled: bool | None = None
    peer_type: str | None = None
    last_established_ns: int | None = None
    received_prefix_count: int | None = None
    accepted_prefix_count: int | None = None
    active_prefix_count: int | None = None
    suppressed_prefix_count: int | None = None
    advertised_prefix_count: int | None = None
    total_prefix_count: int | None = None
    source: str | None = None
    families: list[BgpFamilyHealthCounters] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        return self.device, self.neighbor

    @property
    def state(self) -> str:
        return self.peer_state

    @property
    def remote_as(self) -> int | None:
        return self.peer_as

    @property
    def uptime(self) -> str | None:
        return self.elapsed_time_raw

    @property
    def is_established(self) -> bool:
        return self.peer_state == "Established"

    @property
    def health(self) -> str:
        return "OK" if self.is_established else "CRITICAL"

    @property
    def reason(self) -> str:
        if self.is_established:
            return "peer_established"
        return f"peer_not_established:{self.peer_state}"

    def to_dict(self) -> dict[str, object]:
        return {
            "device": self.device,
            "source": self.source,
            "neighbor": self.neighbor,
            "remote_as": self.remote_as,
            "peer_as": self.peer_as,
            "state": self.state,
            "peer_state": self.peer_state,
            "is_established": self.is_established,
            "uptime": self.uptime,
            "elapsed_time_raw": self.elapsed_time_raw,
            "elapsed_time_seconds": self.elapsed_time_seconds,
            "flap_count": self.flap_count,
            "enabled": self.enabled,
            "peer_type": self.peer_type,
            "last_established_ns": self.last_established_ns,
            "active_prefix_count": self.active_prefix_count,
            "received_prefix_count": self.received_prefix_count,
            "accepted_prefix_count": self.accepted_prefix_count,
            "suppressed_prefix_count": self.suppressed_prefix_count,
            "advertised_prefix_count": self.advertised_prefix_count,
            "total_prefix_count": self.total_prefix_count,
            "families": [family.to_dict() for family in self.families],
            "health": self.health,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class BgpSessionHealthFinding:
    """One rule finding for a peer or family/table health comparison."""

    severity: str
    rule: str
    message: str
    before_value: object | None = None
    after_value: object | None = None
    table: str | None = None
    family: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BgpFamilyHealthResult:
    """Before/after health result for one peer family/table."""

    device: str
    neighbor: str
    table: str
    family: str
    result: str
    before: BgpFamilyHealthCounters | None
    after: BgpFamilyHealthCounters | None
    findings: list[BgpSessionHealthFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "device": self.device,
            "neighbor": self.neighbor,
            "table": self.table,
            "family": self.family,
            "result": self.result,
            "before": self.before.to_dict() if self.before else None,
            "after": self.after.to_dict() if self.after else None,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True, slots=True)
class BgpSessionHealthResult:
    """Before/after health result for one BGP peer."""

    device: str
    neighbor: str
    result: str
    before: BgpSessionHealthRecord | None
    after: BgpSessionHealthRecord | None
    findings: list[BgpSessionHealthFinding] = field(default_factory=list)
    family_results: list[BgpFamilyHealthResult] = field(default_factory=list)
    coverage: str = "FULL"
    not_evaluated_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "device": self.device,
            "neighbor": self.neighbor,
            "result": self.result,
            "before": self.before.to_dict() if self.before else None,
            "after": self.after.to_dict() if self.after else None,
            "findings": [finding.to_dict() for finding in self.findings],
            "families": [item.to_dict() for item in self.family_results],
            "coverage": self.coverage,
            "not_evaluated_checks": list(self.not_evaluated_checks),
        }


@dataclass(frozen=True, slots=True)
class BgpSessionHealthComparison:
    """Device-level BGP session-health comparison result."""

    mw_id: str
    device: str
    before_stage: str
    after_stage: str
    result: str
    before_raw_file: Path | None
    after_raw_file: Path | None
    peer_results: list[BgpSessionHealthResult]
    fail_reasons: list[str] = field(default_factory=list)
    before_source_requested: str = "unknown"
    after_source_requested: str = "unknown"
    before_source_actual: str = "unknown"
    after_source_actual: str = "unknown"

    @property
    def peers_total(self) -> int:
        return len(self.peer_results)

    @property
    def peers_failed(self) -> int:
        return sum(1 for item in self.peer_results if item.result == "FAIL")

    @property
    def peers_warning(self) -> int:
        return sum(1 for item in self.peer_results if item.result == "WARNING")

    @property
    def peers_unhealthy(self) -> int:
        return sum(1 for item in self.peer_results if item.result == "UNHEALTHY")

    @property
    def peers_passed(self) -> int:
        return sum(1 for item in self.peer_results if item.result == "PASS")

    @property
    def peers_not_evaluated(self) -> int:
        return sum(
            1
            for item in self.peer_results
            if item.result == "NOT_EVALUATED"
            or item.coverage == "NOT_EVALUATED"
        )

    @property
    def peers_partial(self) -> int:
        return sum(1 for item in self.peer_results if item.coverage == "PARTIAL")

    @property
    def coverage(self) -> str:
        if not self.peer_results:
            return "NOT_EVALUATED"
        if all(item.coverage == "NOT_EVALUATED" for item in self.peer_results):
            return "NOT_EVALUATED"
        if any(item.coverage != "FULL" for item in self.peer_results):
            return "PARTIAL"
        return "FULL"

    @property
    def families_total(self) -> int:
        return sum(len(item.family_results) for item in self.peer_results)

    @property
    def families_warning(self) -> int:
        return sum(
            1
            for item in self.peer_results
            for family in item.family_results
            if family.result == "WARNING"
        )

    @property
    def families_failed(self) -> int:
        return sum(
            1
            for item in self.peer_results
            for family in item.family_results
            if family.result == "FAIL"
        )

    @property
    def families_not_evaluated(self) -> int:
        return sum(
            1
            for item in self.peer_results
            for family in item.family_results
            if family.result == "NOT_EVALUATED"
        )
