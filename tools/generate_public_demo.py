#!/usr/bin/env python3
"""Generate the sanitized public BGP demo through the real v1.0.0 engines.

This utility is for maintainers. It creates only documentation-address fixtures
and writes the public Summary TXT, Detail TXT, and Executive PDF examples.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from maintenance_window.protocols.bgp.full_report import reports as full_reports
from maintenance_window.protocols.bgp.parsers.pyez_xml import parse_pyez_xml
from maintenance_window.protocols.bgp.session_health.comparison import (
    compare_session_health_snapshots,
)
from maintenance_window.protocols.bgp.session_health.reports import session_health_to_dict
from maintenance_window.protocols.bgp.snapshot_comparison.comparison import (
    compare_bgp_snapshot_files,
)
from maintenance_window.protocols.bgp.snapshot_comparison.reports import (
    snapshot_comparison_to_dict,
)
from maintenance_window.protocols.bgp.snapshot_store.paths import build_snapshot_path
from maintenance_window.protocols.bgp.snapshot_store.payload import build_snapshot_payload
from maintenance_window.ui.executive_pdf import write_executive_pdf


MW_ID = "MW_DEMO_BGP_001"
DEVICES = ("192.0.2.10", "192.0.2.11")
BEFORE_CREATED = "2026-09-06T16:00:00+00:00"
AFTER_CREATED = "2026-09-06T16:10:00+00:00"

EXPECTED_FINDINGS = {
    "session_restart_detected": 1,
    "flap_count_increased": 1,
    "flap_count_reset": 1,
    "new_family_after": 1,
    "missing_family_after": 1,
    "prefix_delta": 1,
    "persistent_unhealthy_peer": 1,
}


def _family_xml(
    table: str,
    *,
    received: int,
    accepted: int | None = None,
    active: int | None = None,
    advertised: int | None = None,
) -> str:
    accepted = received if accepted is None else accepted
    active = received if active is None else active
    advertised = received if advertised is None else advertised
    return f"""
    <bgp-rib>
      <name>{table}</name>
      <bgp-rib-state>BGP restart is complete</bgp-rib-state>
      <send-state>in sync</send-state>
      <received-prefix-count>{received}</received-prefix-count>
      <accepted-prefix-count>{accepted}</accepted-prefix-count>
      <active-prefix-count>{active}</active-prefix-count>
      <suppressed-prefix-count>0</suppressed-prefix-count>
      <advertised-prefix-count>{advertised}</advertised-prefix-count>
    </bgp-rib>"""


def _peer_xml(
    neighbor: str,
    *,
    state: str,
    peer_as: int,
    uptime: int | None,
    flaps: int | None,
    families: list[str],
) -> str:
    elapsed = (
        f'<elapsed-time seconds="{uptime}">{uptime}</elapsed-time>'
        if uptime is not None
        else ""
    )
    flap = f"<flap-count>{flaps}</flap-count>" if flaps is not None else ""
    return f"""
  <bgp-peer>
    <peer-address>{neighbor}</peer-address>
    <peer-as>{peer_as}</peer-as>
    <peer-state>{state}</peer-state>
    {elapsed}
    {flap}
    {''.join(families)}
  </bgp-peer>"""


def _document(device: str, stage: str) -> str:
    if device == "192.0.2.10":
        if stage == "before":
            peers = [
                # Established at both endpoints, but uptime continuity proves an in-window restart.
                _peer_xml(
                    "198.51.100.1", state="Established", peer_as=64501,
                    uptime=3600, flaps=0,
                    families=[_family_xml("inet.0", received=1000)],
                ),
                # Existing unhealthy peer remains unhealthy; context, not a new State failure.
                _peer_xml(
                    "198.51.100.2", state="Idle", peer_as=64502,
                    uptime=None, flaps=None, families=[],
                ),
                # Exactly one meaningful prefix-loss rule in AFTER.
                _peer_xml(
                    "198.51.100.3", state="Established", peer_as=64503,
                    uptime=5000, flaps=0,
                    families=[
                        _family_xml(
                            "inet.0", received=1000, accepted=900,
                            active=850, advertised=800,
                        )
                    ],
                ),
                # Stable peer that will gain inet6.0 in AFTER.
                _peer_xml(
                    "198.51.100.4", state="Established", peer_as=64504,
                    uptime=4000, flaps=0,
                    families=[_family_xml("inet.0", received=200)],
                ),
            ]
        else:
            peers = [
                _peer_xml(
                    "198.51.100.1", state="Established", peer_as=64501,
                    uptime=3800, flaps=0,
                    families=[_family_xml("inet.0", received=1000)],
                ),
                _peer_xml(
                    "198.51.100.2", state="Idle", peer_as=64502,
                    uptime=None, flaps=None, families=[],
                ),
                _peer_xml(
                    "198.51.100.3", state="Established", peer_as=64503,
                    uptime=5600, flaps=0,
                    families=[
                        _family_xml(
                            "inet.0", received=980, accepted=900,
                            active=850, advertised=800,
                        )
                    ],
                ),
                _peer_xml(
                    "198.51.100.4", state="Established", peer_as=64504,
                    uptime=4600, flaps=0,
                    families=[
                        _family_xml("inet.0", received=200),
                        _family_xml("inet6.0", received=40),
                    ],
                ),
            ]
    else:
        if stage == "before":
            peers = [
                # inet6.0 will be missing in AFTER.
                _peer_xml(
                    "203.0.113.1", state="Established", peer_as=64511,
                    uptime=6000, flaps=0,
                    families=[
                        _family_xml("inet.0", received=300),
                        _family_xml("inet6.0", received=60),
                    ],
                ),
                # One flap increase.
                _peer_xml(
                    "203.0.113.2", state="Established", peer_as=64512,
                    uptime=7000, flaps=1,
                    families=[_family_xml("inet.0", received=500)],
                ),
                # One flap counter reset/decrease.
                _peer_xml(
                    "203.0.113.3", state="Established", peer_as=64513,
                    uptime=8000, flaps=5,
                    families=[_family_xml("inet.0", received=700)],
                ),
            ]
        else:
            peers = [
                _peer_xml(
                    "203.0.113.1", state="Established", peer_as=64511,
                    uptime=6600, flaps=0,
                    families=[_family_xml("inet.0", received=300)],
                ),
                _peer_xml(
                    "203.0.113.2", state="Established", peer_as=64512,
                    uptime=7600, flaps=2,
                    families=[_family_xml("inet.0", received=500)],
                ),
                _peer_xml(
                    "203.0.113.3", state="Established", peer_as=64513,
                    uptime=8600, flaps=1,
                    families=[_family_xml("inet.0", received=700)],
                ),
            ]

    return "<bgp-information>" + "".join(peers) + "\n</bgp-information>\n"


def _write_snapshot(
    *,
    snapshot_root: Path,
    raw_file: Path,
    device: str,
    stage: str,
    created_at: str,
) -> None:
    sessions = parse_pyez_xml(raw_file, device_name=device)
    payload = build_snapshot_payload(
        mw_id=MW_ID,
        stage=stage,
        device=device,
        source_requested="pyez",
        source_actual="pyez",
        raw_file=raw_file,
        sessions=sessions,
        created_at_utc=created_at,
    )
    path = build_snapshot_path(snapshot_root, MW_ID, stage, device)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _public_raw_path(device: str, stage: str) -> str:
    timestamp = "20260906_160000" if stage == "before" else "20260906_161000"
    return f"outputs/raw/pyez/{device}_{timestamp}.xml"


def _sanitize_state_report(report: dict[str, object], device: str) -> None:
    for stage in ("before", "after"):
        stage_data = report.get(stage)
        if not isinstance(stage_data, dict):
            continue
        stage_data["raw_file"] = _public_raw_path(device, stage)
        stage_data["snapshot_file"] = (
            f"outputs/snapshots/bgp/{MW_ID}/{stage}/{device}.json"
        )


def _sanitize_health_report(report: dict[str, object], device: str) -> None:
    report["before_raw_file"] = _public_raw_path(device, "before")
    report["after_raw_file"] = _public_raw_path(device, "after")


def build_demo_payload() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="maintenance_window_public_demo_") as temporary:
        work = Path(temporary)
        raw_root = work / "raw"
        snapshot_root = work / "snapshots" / "bgp"
        raw_root.mkdir(parents=True)

        for device in DEVICES:
            for stage, created_at in (
                ("before", BEFORE_CREATED),
                ("after", AFTER_CREATED),
            ):
                raw_file = raw_root / f"{device}_{stage}.xml"
                raw_file.write_text(_document(device, stage), encoding="utf-8", newline="\n")
                _write_snapshot(
                    snapshot_root=snapshot_root,
                    raw_file=raw_file,
                    device=device,
                    stage=stage,
                    created_at=created_at,
                )

        state_reports: list[dict[str, object]] = []
        health_reports: list[dict[str, object]] = []

        for device in DEVICES:
            comparison, before, after = compare_bgp_snapshot_files(
                snapshot_root=snapshot_root,
                mw_id=MW_ID,
                before_stage="before",
                after_stage="after",
                device=device,
            )
            state_report = snapshot_comparison_to_dict(comparison, before, after)
            _sanitize_state_report(state_report, device)
            state_reports.append(state_report)

            health = compare_session_health_snapshots(
                snapshot_root=snapshot_root,
                mw_id=MW_ID,
                before_stage="before",
                after_stage="after",
                device=device,
            )
            health_report = session_health_to_dict(health)
            _sanitize_health_report(health_report, device)
            health_reports.append(health_report)

    request = SimpleNamespace(
        mw_id=MW_ID,
        before_stage="before",
        after_stage="after",
        device_names=list(DEVICES),
    )
    report_directory = (
        f"outputs/snapshots/bgp/{MW_ID}/comparison_reports/20260906_161000"
    )
    payload = full_reports.build_full_report_payload(
        request=request,
        state_reports=state_reports,
        session_health_reports=health_reports,
        report_directory=report_directory,
    )

    if payload["result"] != "WARNING":
        raise RuntimeError(f"Unexpected demo overall result: {payload['result']}")
    if payload["state_result"] != "PASS":
        raise RuntimeError(f"Unexpected demo State result: {payload['state_result']}")
    if payload["session_health_result"] != "WARNING":
        raise RuntimeError(
            f"Unexpected demo Session Health result: {payload['session_health_result']}"
        )

    counts = payload.get("finding_counts")
    if not isinstance(counts, dict):
        raise RuntimeError("Demo payload does not contain finding_counts.")

    observed = {name: int(counts.get(name, 0)) for name in EXPECTED_FINDINGS}
    if observed != EXPECTED_FINDINGS:
        raise RuntimeError(
            "Demo finding inventory drifted from the public contract: "
            f"expected={EXPECTED_FINDINGS!r} observed={observed!r}"
        )

    unexpected = {
        name: int(value)
        for name, value in counts.items()
        if int(value) and name not in EXPECTED_FINDINGS
    }
    if unexpected:
        raise RuntimeError(f"Unexpected non-zero demo findings: {unexpected!r}")

    # Keep generated public artifacts byte-for-byte reproducible. The live PDF
    # renderer still uses the current local time when this field is absent.
    payload["generated_at_utc"] = AFTER_CREATED
    return payload


def write_public_examples(output_root: Path) -> dict[str, Path]:
    payload = build_demo_payload()
    examples = output_root / "docs" / "examples"
    examples.mkdir(parents=True, exist_ok=True)

    summary = examples / "MW_DEMO_BGP_001_summary.txt"
    detail = examples / "MW_DEMO_BGP_001_detail.txt"
    pdf = examples / "MW_DEMO_BGP_001_executive_report.pdf"

    summary.write_text(full_reports.format_full_summary(payload) + "\n", encoding="utf-8", newline="\n")
    detail.write_text(full_reports.format_full_detail(payload) + "\n", encoding="utf-8", newline="\n")
    write_executive_pdf(payload, pdf)

    return {"summary": summary, "detail": detail, "pdf": pdf}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root that receives docs/examples outputs.",
    )
    args = parser.parse_args()

    paths = write_public_examples(args.root.resolve())
    payload = build_demo_payload()
    print("Public demo generated through the real BGP comparison/reporting engine.")
    print(f"Result: {payload['result']}")
    print(f"State: {payload['state_result']}")
    print(f"Session Health: {payload['session_health_result']}")
    for key in EXPECTED_FINDINGS:
        print(f"{key}: {payload['finding_counts'][key]}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
