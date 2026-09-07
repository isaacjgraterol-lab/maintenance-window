"""Small local HTTP server for the Maintenance Window GUI.

The server stays dependency-free by using the Python standard library.
Protocol logic remains outside the UI; this layer only builds CLI commands,
renders pages, and shows operator-facing results.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
import tempfile
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, urlparse

from maintenance_window.cli_app.defaults import DEFAULT_INVENTORY
from maintenance_window.ui.command_builder import (
    CAPTURE_ACTIONS,
    UiCommandRequest,
    build_mw_command,
)
from maintenance_window.ui.options import (
    AUTH_BACKEND_OPTIONS,
    AUTHOR_BANNER,
    AUTHOR_EMAIL,
    AUTHOR_LINKEDIN_LABEL,
    AUTHOR_LINKEDIN_URL,
    GNMIC_LIMITATION_MESSAGE,
    GUI_ADMIN_PASSWORD_ENV,
    CAPTURE_LEVEL_OPTIONS,
    MANUAL_DB_LIMIT_OPTIONS,
    MANUAL_INPUT_FORMAT_OPTIONS,
    PROTOCOL_OPTIONS,
    SNAPSHOT_RESULT_MESSAGE,
    SOURCE_LABELS,
    SOURCE_OPTIONS,
    WORKER_OPTIONS,
)
from maintenance_window.ui.report_reader import (
    read_report_summary,
    resolve_health_depth,
)
from maintenance_window.ui.report_downloads import (
    build_export_actions,
    resolve_report_download,
)
from maintenance_window.ui.snapshot_store import (
    SnapshotMwRecord,
    discover_snapshot_mw_records,
)

PROJECT_ROOT = Path.cwd()
UI_ROOT = Path(__file__).resolve().parent
INDEX_TEMPLATE_PATH = UI_ROOT / "templates" / "index.html"
RESULT_TEMPLATE_PATH = UI_ROOT / "templates" / "result.html"
EXISTING_MW_TEMPLATE_PATH = UI_ROOT / "templates" / "existing_mw.html"
STATIC_ROOT = UI_ROOT / "static"


@dataclass(frozen=True, slots=True)
class UiState:
    protocol: str = "bgp"
    source: str = "pyez"
    device_mode: str = "individual"
    device: str = "192.0.2.10"
    mw_id: str = "MW_GUI_TEST_001"
    auth_backend: str = "radius"
    workers: int = 1
    health_depth: str = "auto"
    capture_level: str = "basic"
    inventory_path: str = str(DEFAULT_INVENTORY)
    manual_input_path: str = ""
    manual_input_format: str = "auto"
    manual_db_limit: int = 200
    radius_username: str = ""
    radius_password: str = ""
    admin_password: str = ""
    stdout: str = ""
    stderr: str = ""
    command: str = ""
    exit_code: int | None = None
    error: str = ""
    action: str = ""
    report_summary: dict[str, object] | None = None
    result_title: str = ""
    result_message: str = ""


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _selected(current: object, value: object) -> str:
    return "selected" if str(current) == str(value) else ""


def _protocol_options(current: str) -> str:
    chunks: list[str] = []
    for option in PROTOCOL_OPTIONS:
        disabled = "" if option.available else "disabled"
        chunks.append(
            f'<option value="{_escape(option.value)}" '
            f'{_selected(current, option.value)} {disabled}>'
            f'{_escape(option.label)}</option>'
        )
    return "\n".join(chunks)


def _simple_options(options: tuple[object, ...], current: object) -> str:
    return "\n".join(
        f'<option value="{_escape(option)}" {_selected(current, option)}>'
        f'{_escape(option)}</option>'
        for option in options
    )



def _source_options(current: str) -> str:
    return "\n".join(
        f'<option value="{_escape(value)}" {_selected(current, value)}>'
        f'{_escape(SOURCE_LABELS.get(value, value))}</option>'
        for value in SOURCE_OPTIONS
    )

def _manual_db_limit_options(current: int) -> str:
    return "\n".join(
        f'<option value="{option}" {_selected(current, option)}>{option}</option>'
        for option in MANUAL_DB_LIMIT_OPTIONS
    )


def _snapshot_devices_text(record: SnapshotMwRecord) -> str:
    if record.common_devices:
        devices = list(record.common_devices)
        shown = devices[:8]
        text = ", ".join(shown)
        if len(devices) > len(shown):
            text += f", +{len(devices) - len(shown)} more"
        return text

    if record.before_only_devices:
        return "before only: " + ", ".join(record.before_only_devices[:6])
    if record.after_only_devices:
        return "after only: " + ", ".join(record.after_only_devices[:6])
    return "N/A"


def _snapshot_store_rows() -> str:
    records = discover_snapshot_mw_records(PROJECT_ROOT, protocol="bgp")
    if not records:
        return (
            '<tr><td colspan="7" class="muted-cell">'
            "No BGP snapshot maintenance windows found under "
            "outputs/snapshots/bgp/."
            "</td></tr>"
        )

    rows: list[str] = []
    for record in records:
        ready = (
            '<span class="ready-badge">YES</span>'
            if record.ready
            else '<span class="not-ready-badge">NO</span>'
        )
        rows.append(
            "<tr>"
            f"<td><code>{_escape(record.mw_id)}</code></td>"
            f"<td>{record.before_count}</td>"
            f"<td>{record.after_count}</td>"
            f"<td>{record.common_count}</td>"
            f"<td>{ready}</td>"
            f"<td>{_escape(record.before_last_modified)}</td>"
            f"<td>{_escape(record.after_last_modified)}</td>"
            f"<td>{_escape(record.last_modified)}</td>"
            f"<td>{_escape(record.reason)}<br>"
            f"<span class=\"table-devices\">{_escape(_snapshot_devices_text(record))}</span>"
            "</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _status_badge(value: object) -> str:
    text = str(value or "UNKNOWN")
    normalized = text.strip().lower().replace("_", "-")
    css_class = {
        "pass": "result-pass",
        "ok": "result-pass",
        "warning": "result-warning",
        "pass-with-unhealthy-sessions": "result-warning",
        "unhealthy": "result-unhealthy",
        "fail": "result-fail",
        "error": "result-error",
        "not-evaluated": "result-neutral",
        "unknown": "result-neutral",
    }.get(normalized, "result-neutral")
    return (
        f'<span class="result-badge {css_class}">'
        f'{_escape(text)}</span>'
    )


def _author_banner_html() -> str:
    return (
        '<div class="banner-title">'
        f'{_escape(AUTHOR_BANNER)}'
        '</div>'
        '<div class="banner-contact">'
        f'<a href="mailto:{_escape(AUTHOR_EMAIL)}">{_escape(AUTHOR_EMAIL)}</a>'
        '<span class="banner-separator">|</span>'
        f'<a href="{_escape(AUTHOR_LINKEDIN_URL)}" '
        'target="_blank" rel="noopener noreferrer">'
        f'{_escape(AUTHOR_LINKEDIN_LABEL)}</a>'
        '</div>'
    )


def _summary_card(label: str, value: object, *, path: bool = False) -> str:
    extra_class = " path-card" if path else ""
    result_labels = {
        "Overall result",
        "State result",
        "Session-health result",
    }
    rendered_value = (
        _status_badge(value)
        if label in result_labels
        else _escape(value)
    )
    return (
        f'<div class="card{extra_class}">'
        f'<div class="card-label">{_escape(label)}</div>'
        f'<div class="card-value">{rendered_value}</div>'
        '</div>'
    )


def _summary_section(title: str, items: list[tuple[str, object]], *, empty_note: str = "") -> str:
    cards = []
    for label, value in items:
        if value is None:
            continue
        cards.append(
            _summary_card(
                label,
                value,
                path=(label == "Report directory"),
            )
        )

    if not cards:
        if not empty_note:
            return ""
        cards.append(f'<p class="hint section-placeholder">{_escape(empty_note)}</p>')

    return (
        '<section class="summary-section">'
        f'<h2>{_escape(title)}</h2>'
        f'<div class="cards">{"".join(cards)}</div>'
        '</section>'
    )


def _future_bgp_modules_section() -> str:
    return (
        '<section class="summary-section future-modules">'
        '<h2>Future BGP modules</h2>'
        '<div class="future-module-grid">'
        '<article class="future-module-card">'
        '<h3>BGP Routes / Prefixes</h3>'
        '<p><strong>Status:</strong> Future</p>'
        '<p>Capture received and advertised routes, then compare before vs after to list added and disappeared prefixes.</p>'
        '</article>'
        '<article class="future-module-card">'
        '<h3>BGP VPN / Services</h3>'
        '<p><strong>Status:</strong> Future</p>'
        '<p>Apply the same route-delta model to L3VPN, VPNv6, EVPN, L2VPN, RT/RD, and service route health.</p>'
        '</article>'
        '</div>'
        '</section>'
    )


def _summary_cards(state: UiState) -> str:
    summary = state.report_summary or {}
    if not summary:
        return ""

    health_depth = resolve_health_depth(
        source=state.source,
        selected=state.health_depth,
        action=state.action,
        not_evaluated_peers=summary.get("not_evaluated_peers"),
    )

    general_items = [
        ("Overall result", summary.get("overall_result")),
        ("Health depth", health_depth),
        ("Total sessions before", summary.get("total_sessions_before")),
        ("Total sessions after", summary.get("total_sessions_after")),
        ("Report directory", summary.get("report_directory")),
    ]

    state_items = [
        ("State result", summary.get("state_result")),
        ("Lost sessions", summary.get("lost_sessions")),
        ("New sessions", summary.get("new_sessions")),
        ("State changes", summary.get("state_changes")),
        (
            "Unhealthy FSM transitions",
            summary.get("unhealthy_fsm_transitions"),
        ),
        ("New unhealthy", summary.get("new_unhealthy")),
        ("Resolved unhealthy", summary.get("resolved_unhealthy")),
        ("Persistent unhealthy", summary.get("persistent_unhealthy")),
        ("Unique peers before", summary.get("unique_sessions_before")),
        ("Unique peers after", summary.get("unique_sessions_after")),
        ("Duplicate/context records before", summary.get("duplicate_entries_before")),
        ("Duplicate/context records after", summary.get("duplicate_entries_after")),
    ]

    session_health_items = [
        ("Session-health result", summary.get("session_health_result")),
        ("Warning peers", summary.get("warning_peers")),
        ("Session restarts", summary.get("session_restarts")),
        ("Uptime resets", summary.get("uptime_resets")),
        ("Flap increases", summary.get("flap_count_increases")),
        ("Flap counter resets", summary.get("flap_count_resets")),
        ("New families", summary.get("new_families")),
        ("Missing families", summary.get("missing_families")),
        ("Prefix deltas", summary.get("prefix_deltas")),
        ("Persistent unhealthy findings", summary.get("persistent_unhealthy_findings")),
        ("Low uptime peers", summary.get("low_after_uptime_peers")),
        ("Failed peers", summary.get("failed_peers")),
        ("Unhealthy peers", summary.get("unhealthy_peers")),
        ("Not evaluated peers", summary.get("not_evaluated_peers")),
        ("Partial peers", summary.get("partial_peers")),
        ("Data coverage", summary.get("health_coverage")),
        ("Warning families", summary.get("warning_families")),
        ("Failed families", summary.get("failed_families")),
        ("Total families", summary.get("total_families")),
        ("Fallback devices", summary.get("fallback_device_count")),
        ("Before sources", summary.get("before_source_coverage")),
        ("After sources", summary.get("after_source_coverage")),
    ]

    sections = [
        _summary_section("General summary", general_items),
        _summary_section("BGP State", state_items),
        _summary_section("BGP Session Health", session_health_items),
    ]

    rendered = "".join(section for section in sections if section)
    if not rendered:
        return ""
    return f'<div class="summary-groups">{rendered}</div>'


def _device_summary_table(state: UiState) -> str:
    summary = state.report_summary or {}
    rows = summary.get("device_summaries")
    if not isinstance(rows, list) or not rows:
        return ""

    rendered_rows: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        state_summary = row.get("state", {})
        health_summary = row.get("session_health", {})
        if not isinstance(state_summary, dict):
            state_summary = {}
        if not isinstance(health_summary, dict):
            health_summary = {}

        sessions = (
            f"{state_summary.get('total_sessions_before', 0)} -> "
            f"{state_summary.get('total_sessions_after', 0)}"
        )
        state_delta = (
            f"L:{state_summary.get('lost_sessions', 0)} "
            f"N:{state_summary.get('new_sessions', 0)} "
            f"C:{state_summary.get('state_changes', 0)} "
            f"U:{state_summary.get('persistent_unhealthy', 0)}"
        )
        peers = (
            f"P:{health_summary.get('passed_peers', 0)} "
            f"W:{health_summary.get('warning_peers', 0)} "
            f"F:{health_summary.get('failed_peers', 0)} "
            f"U:{health_summary.get('unhealthy_peers', 0)} "
            f"NE:{health_summary.get('not_evaluated_peers', 0)}"
        )
        families = (
            f"T:{health_summary.get('families_total', 0)} "
            f"W:{health_summary.get('warning_families', 0)} "
            f"F:{health_summary.get('failed_families', 0)}"
        )
        finding_counts = row.get("finding_counts", {})
        if not isinstance(finding_counts, dict):
            finding_counts = {}
        findings = (
            f"Restart:{finding_counts.get('session_restart_detected', 0)} "
            f"Flap+:{finding_counts.get('flap_count_increased', 0)} "
            f"Flap reset:{finding_counts.get('flap_count_reset', 0)} "
            f"New family:{finding_counts.get('new_family_after', 0)} "
            f"Missing family:{finding_counts.get('missing_family_after', 0)} "
            f"Prefix delta:{finding_counts.get('prefix_delta', 0)}"
        )

        rendered_rows.append(
            "<tr>"
            f"<td><code>{_escape(row.get('device'))}</code></td>"
            f"<td>{_status_badge(row.get('overall_result'))}</td>"
            f"<td>{_status_badge(state_summary.get('result'))}</td>"
            f"<td>{_escape(sessions)}</td>"
            f"<td>{_escape(state_delta)}</td>"
            f"<td>{_status_badge(health_summary.get('result'))}</td>"
            f"<td>{_escape(peers)}</td>"
            f"<td>{_escape(families)}</td>"
            f"<td>{_escape(findings)}</td>"
            "</tr>"
        )

    if not rendered_rows:
        return ""

    return (
        '<section class="evidence-panel">'
        '<h2>Per-device summary</h2>'
        '<p class="hint">'
        'State delta: L=lost, N=new, C=state changes, U=persistent unhealthy. '
        'Peers: P=pass, W=warning, F=fail, U=unhealthy, NE=not evaluated. '
        'Families: T=total, W=warning, F=fail.'
        '</p>'
        '<table class="snapshot-table evidence-table">'
        '<thead><tr>'
        '<th>Device</th>'
        '<th>Overall</th>'
        '<th>State</th>'
        '<th>Sessions B/A</th>'
        '<th>State delta</th>'
        '<th>Session health</th>'
        '<th>Peers</th>'
        '<th>Families</th>'
        '<th>Findings</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rendered_rows)}</tbody>'
        '</table>'
        '</section>'
    )


def _snapshot_evidence_table(state: UiState) -> str:
    summary = state.report_summary or {}
    rows = summary.get("snapshot_evidence")
    if not isinstance(rows, list) or not rows:
        return ""

    rendered_rows: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rendered_rows.append(
            "<tr>"
            f"<td>{_escape(row.get('device'))}</td>"
            f"<td>{_escape(row.get('before_source'))}</td>"
            f"<td><code>{_escape(row.get('before_raw_timestamp'))}</code></td>"
            f"<td>{_escape(row.get('after_source'))}</td>"
            f"<td><code>{_escape(row.get('after_raw_timestamp'))}</code></td>"
            "</tr>"
        )

    if not rendered_rows:
        return ""

    total = summary.get("snapshot_evidence_total")
    note = (
        "Compare uses the current before/after snapshot files for the selected "
        "MW ID. Re-running Capture Before or Capture After updates the evidence "
        "used by future comparisons."
    )
    if isinstance(total, int) and total > len(rendered_rows):
        note += f" Showing first {len(rendered_rows)} of {total} devices."

    return (
        '<section class="evidence-panel">'
        '<h2>Snapshot evidence used</h2>'
        f'<p class="hint">{_escape(note)}</p>'
        '<table class="snapshot-table evidence-table">'
        '<thead><tr>'
        '<th>Device</th>'
        '<th>Before source</th>'
        '<th>Before raw timestamp</th>'
        '<th>After source</th>'
        '<th>After raw timestamp</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rendered_rows)}</tbody>'
        '</table>'
        '</section>'
    )


def _result_hint_for_action(action: str) -> str:
    if action in CAPTURE_ACTIONS:
        return (
            "Snapshot capture stores evidence only. Maintenance-window impact is "
            "evaluated by Compare State, Compare Session-Health, or Compare Full."
        )
    if action.startswith("compare-"):
        return (
            "This comparison uses the current before/after snapshot files for the "
            "selected MW ID. Re-running Capture Before or Capture After for the "
            "same MW ID updates the evidence used by future comparisons."
        )
    return ""


def _render_index(state: UiState | None = None) -> str:
    state = state or UiState()
    template = Template(INDEX_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.safe_substitute(
        author_banner=_author_banner_html(),
        protocol_options=_protocol_options(state.protocol),
        source_options=_source_options(state.source),
        auth_backend_options=_simple_options(AUTH_BACKEND_OPTIONS, state.auth_backend),
        worker_options=_simple_options(WORKER_OPTIONS, state.workers),
        manual_input_format_options=_simple_options(
            MANUAL_INPUT_FORMAT_OPTIONS,
            state.manual_input_format,
        ),
        capture_level_options=_simple_options(
            CAPTURE_LEVEL_OPTIONS,
            state.capture_level,
        ),
        individual_selected=_selected(state.device_mode, "individual"),
        db_selected=_selected(state.device_mode, "db"),
        device=_escape(state.device),
        mw_id=_escape(state.mw_id),
        inventory_path=_escape(state.inventory_path),
        manual_input_path=_escape(state.manual_input_path),
        gnmic_limitation=_escape(GNMIC_LIMITATION_MESSAGE),
    )


def _render_existing_mw(state: UiState | None = None) -> str:
    state = state or UiState(action="list-manual-db", device="", mw_id="")
    template = Template(EXISTING_MW_TEMPLATE_PATH.read_text(encoding="utf-8"))

    exit_class = "status neutral"
    if state.exit_code == 0:
        exit_class = "status ok"
    elif state.exit_code == 1:
        exit_class = "status fail"
    elif state.exit_code == 2:
        exit_class = "status error"

    manual_db_output = state.stdout.strip()
    if not manual_db_output:
        manual_db_output = (
            "Manual DB records are secondary. Click Refresh Manual DB Records "
            "to view local SQLite manual/upload history."
        )

    return template.safe_substitute(
        author_banner=_author_banner_html(),
        mw_id=_escape("" if state.mw_id == "MW_LIST_ONLY" else state.mw_id),
        snapshot_rows=_snapshot_store_rows(),
        manual_db_limit_options=_manual_db_limit_options(state.manual_db_limit),
        manual_db_output=_escape(manual_db_output),
        stderr=_escape(state.stderr),
        error=_escape(state.error),
        exit_code="" if state.exit_code is None else _escape(state.exit_code),
        exit_class=exit_class,
    )


def _operator_output_for_action(action: str, stdout: str) -> str:
    """Return operator-facing output without misleading MW results."""
    if action not in CAPTURE_ACTIONS:
        return stdout

    if not stdout.strip():
        return ""

    lines = stdout.splitlines()
    filtered: list[str] = []
    skip_next_result_value = False

    for line in lines:
        stripped = line.strip()

        if skip_next_result_value:
            skip_next_result_value = False
            if stripped in {
                "PASS",
                "FAIL",
                "ERROR",
                "PASS_WITH_UNHEALTHY_SESSIONS",
            }:
                continue

        if stripped.lower() == "result:":
            skip_next_result_value = True
            continue

        filtered.append(line)

    cleaned = "\n".join(filtered).strip()
    message = (
        "Snapshot captured successfully.\n"
        "No maintenance-window comparison was executed.\n"
    )

    if cleaned:
        return f"{message}\n{cleaned}"

    return message


def _render_result(state: UiState) -> str:
    template = Template(RESULT_TEMPLATE_PATH.read_text(encoding="utf-8"))
    exit_class = "status neutral"
    if state.exit_code == 0:
        exit_class = "status ok"
    elif state.exit_code == 1:
        exit_class = "status fail"
    elif state.exit_code == 2:
        exit_class = "status error"

    return template.safe_substitute(
        author_banner=_author_banner_html(),
        result_title=_escape(state.result_title or "Execution result"),
        result_message=_escape(state.result_message),
        exit_code="" if state.exit_code is None else _escape(state.exit_code),
        exit_class=exit_class,
        action=_escape(state.action),
        command=_escape(state.command),
        stdout=_escape(_operator_output_for_action(state.action, state.stdout)),
        stderr=_escape(state.stderr),
        error=_escape(state.error),
        result_hint=_escape(_result_hint_for_action(state.action)),
        summary_cards=_summary_cards(state),
        device_summary=_device_summary_table(state),
        snapshot_evidence=_snapshot_evidence_table(state),
        export_actions=build_export_actions(state.report_summary),
    )


def _int_from_form(data: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(data.get(key, [str(default)])[0])
    except ValueError:
        return default


def _state_from_form(body: bytes) -> UiState:
    data = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return UiState(
        protocol=data.get("protocol", ["bgp"])[0],
        source=data.get("source", ["pyez"])[0],
        device_mode=data.get("device_mode", ["individual"])[0],
        device=data.get("device", [""])[0],
        mw_id=data.get("mw_id", [""])[0],
        action=data.get("action", [""])[0],
        auth_backend=data.get("auth_backend", ["radius"])[0],
        workers=_int_from_form(data, "workers", 1),
        health_depth=data.get("health_depth", ["auto"])[0],
        capture_level=data.get("capture_level", ["basic"])[0],
        inventory_path=data.get("inventory_path", [str(DEFAULT_INVENTORY)])[0],
        manual_input_path=data.get("manual_input_path", [""])[0],
        manual_input_format=data.get("manual_input_format", ["auto"])[0],
        manual_db_limit=_int_from_form(data, "manual_db_limit", 200),
        radius_username=data.get("radius_username", [""])[0],
        radius_password=data.get("radius_password", [""])[0],
        admin_password=data.get("admin_password", [""])[0],
    )


def _runtime_credentials_payload(username: str, password: str) -> dict[str, object]:
    profile_name = "gui_radius_runtime"
    return {
        "auth_mode": "profiles",
        "default_profiles": {
            "ssh": profile_name,
            "pyez": profile_name,
            "gnmic": profile_name,
        },
        "profiles": {
            profile_name: {
                "type": "username_password",
                "username": username,
                "password": password,
                "authentication_backend": "radius",
                "description": "Temporary GUI Radius runtime profile",
            }
        },
    }


def _write_runtime_credentials(username: str, password: str) -> Path:
    temp_dir = (
        Path(tempfile.gettempdir())
        / "maintenance_window"
        / "gui_credentials"
    )
    temp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        suffix=".json",
        prefix="radius_",
        dir=temp_dir,
        delete=False,
    ) as file_handle:
        json.dump(_runtime_credentials_payload(username, password), file_handle)
        file_handle.write("\n")
        path = Path(file_handle.name)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def _validate_runtime_auth(state: UiState) -> Path | None:
    if state.action not in CAPTURE_ACTIONS:
        return None

    if state.source == "manual":
        return None

    if state.auth_backend == "radius":
        if not state.radius_username.strip() or not state.radius_password:
            raise ValueError(
                "Radius username and password are required for each live capture."
            )
        return _write_runtime_credentials(
            state.radius_username.strip(),
            state.radius_password,
        )

    configured_password = os.environ.get(GUI_ADMIN_PASSWORD_ENV, "")
    if not configured_password:
        raise ValueError(
            f"Admin mode is disabled. Set {GUI_ADMIN_PASSWORD_ENV} before using "
            "local or auto authentication from the GUI."
        )
    if state.admin_password != configured_password:
        raise ValueError("Invalid GUI admin password for local/auto authentication.")
    return None


def _display_command(command: list[str]) -> str:
    displayed: list[str] = []
    skip_next = False
    for index, value in enumerate(command):
        if skip_next:
            skip_next = False
            continue
        displayed.append(value)
        if value == "--credentials" and index + 1 < len(command):
            displayed.append("<runtime_credentials.json>")
            skip_next = True
    return " ".join(displayed)


def _manual_input_path(value: str) -> Path | None:
    text = value.strip()
    if not text:
        return None
    return Path(text).expanduser()


def _inventory_path(value: str) -> Path | None:
    text = value.strip()
    if not text:
        return None
    return Path(text).expanduser()


def _result_title_for_action(action: str) -> str:
    titles = {
        "capture-before": "Snapshot Result - Before",
        "capture-after": "Snapshot Result - After",
        "compare-state": "Maintenance Window Result - State",
        "compare-session-health": "Maintenance Window Result - Session-Health",
        "compare-full": "Maintenance Window Result - Full",
        "list-manual-db": "Manual DB Records",
    }
    return titles.get(action, "Execution result")


def _result_message_for_action(action: str) -> str:
    if action in CAPTURE_ACTIONS:
        return SNAPSHOT_RESULT_MESSAGE
    if action == "list-manual-db":
        return "Manual DB records are secondary reference data."
    return (
        "Maintenance-window comparison executed using devices found in the "
        "selected MW snapshot folders. Summary is shown below and report "
        "artifacts are available for download."
    )


def _run_action(state: UiState) -> UiState:
    runtime_credentials: Path | None = None
    try:
        runtime_credentials = _validate_runtime_auth(state)
        ui_command = build_mw_command(
            UiCommandRequest(
                action=state.action,
                protocol=state.protocol,
                source=state.source,
                device_mode=state.device_mode,
                device=state.device,
                mw_id=state.mw_id,
                auth_backend=state.auth_backend,
                health_depth=state.health_depth,
                capture_level=state.capture_level,
                workers=state.workers,
                credentials_path=runtime_credentials,
                inventory_path=_inventory_path(state.inventory_path),
                manual_input_path=_manual_input_path(state.manual_input_path),
                manual_input_format=state.manual_input_format,
                manual_db_limit=state.manual_db_limit,
            ),
            project_root=PROJECT_ROOT,
        )
        if ui_command.export_path is not None:
            ui_command.export_path.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            ui_command.command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        summary = read_report_summary(ui_command.export_path)
        if ui_command.export_path is not None:
            summary = dict(summary)
            summary["export_path"] = str(ui_command.export_path)
        return UiState(
            protocol=state.protocol,
            source=state.source,
            device_mode=state.device_mode,
            device=state.device,
            mw_id=state.mw_id,
            auth_backend=state.auth_backend,
            workers=state.workers,
            health_depth=state.health_depth,
            capture_level=state.capture_level,
            inventory_path=state.inventory_path,
            manual_input_path=state.manual_input_path,
            manual_input_format=state.manual_input_format,
            manual_db_limit=state.manual_db_limit,
            stdout=completed.stdout,
            stderr=completed.stderr,
            command=_display_command(ui_command.command),
            exit_code=completed.returncode,
            action=state.action,
            report_summary=summary,
            result_title=_result_title_for_action(state.action),
            result_message=_result_message_for_action(state.action),
        )
    except Exception as exc:  # noqa: BLE001 - user-facing local UI error panel
        return UiState(
            protocol=state.protocol,
            source=state.source,
            device_mode=state.device_mode,
            device=state.device,
            mw_id=state.mw_id,
            auth_backend=state.auth_backend,
            workers=state.workers,
            health_depth=state.health_depth,
            capture_level=state.capture_level,
            inventory_path=state.inventory_path,
            manual_input_path=state.manual_input_path,
            manual_input_format=state.manual_input_format,
            manual_db_limit=state.manual_db_limit,
            error=f"{type(exc).__name__}: {exc}",
            exit_code=2,
            action=state.action,
            result_title=_result_title_for_action(state.action),
            result_message="The GUI could not execute the requested action.",
        )
    finally:
        if runtime_credentials is not None:
            try:
                runtime_credentials.unlink(missing_ok=True)
            except OSError:
                pass


class MwGuiHandler(BaseHTTPRequestHandler):
    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file_download(
        self,
        path: Path,
        *,
        content_type: str,
        filename: str,
    ) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Report file not found")
            return
        payload = path.read_bytes()
        safe_name = filename.replace('"', "_")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_report_download(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=True)
        kind = params.get("kind", [""])[0]
        report_dir = params.get("report_dir", [""])[0]
        export_file = params.get("export_file", [""])[0]
        export_path = params.get("export_path", [""])[0]
        try:
            download = resolve_report_download(
                PROJECT_ROOT,
                report_dir_text=report_dir,
                export_file_text=export_file,
                export_path_text=export_path,
                kind=kind,
            )
        except FileNotFoundError as exc:
            self.send_error(HTTPStatus.NOT_FOUND, str(exc))
            return
        except ValueError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        try:
            self._send_file_download(
                download.path,
                content_type=download.content_type,
                filename=download.filename,
            )
        finally:
            if download.delete_after_send:
                try:
                    download.path.unlink(missing_ok=True)
                except OSError:
                    pass

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/download-report":
            self._send_report_download(parsed.query)
            return
        if path == "/static/styles.css":
            self._send_static(STATIC_ROOT / "styles.css")
            return
        if path == "/existing-mw":
            self._send_html(_render_existing_mw())
            return
        self._send_html(_render_index())

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        state = _run_action(_state_from_form(body))
        if path == "/existing-mw" and state.action == "list-manual-db":
            self._send_html(_render_existing_mw(state))
            return
        self._send_html(_render_result(state))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Start the local Maintenance Window GUI."
    )
    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=8080,
        help="local TCP port to listen on (default: 8080)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    host = "127.0.0.1"
    port = args.port

    server = ThreadingHTTPServer((host, port), MwGuiHandler)
    url = f"http://{host}:{port}"
    print(f"Maintenance Window GUI running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Maintenance Window GUI.")
    finally:
        server.server_close()
    return 0
