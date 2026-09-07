"""Generate a dependency-free executive PDF for Maintenance Window reports.

The PDF is intentionally an executive view. Full peer/family evidence remains in
TXT and JSON artifacts. This module does not run protocol logic or mutate report
data; it only renders an already-generated JSON report.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

PAGE_W = 612.0
PAGE_H = 792.0
MARGIN = 42.0
CONTENT_W = PAGE_W - (2 * MARGIN)

NAVY = (0.055, 0.090, 0.160)
NAVY_2 = (0.085, 0.135, 0.225)
BLUE = (0.12, 0.42, 0.86)
LIGHT_BLUE = (0.92, 0.96, 1.00)
GREEN = (0.12, 0.63, 0.32)
LIGHT_GREEN = (0.91, 0.98, 0.93)
ORANGE = (0.95, 0.49, 0.08)
LIGHT_ORANGE = (1.00, 0.96, 0.90)
RED = (0.78, 0.18, 0.18)
LIGHT_RED = (1.00, 0.93, 0.93)
PURPLE = (0.48, 0.31, 0.78)
GRAY_900 = (0.10, 0.13, 0.18)
GRAY_700 = (0.30, 0.35, 0.42)
GRAY_500 = (0.48, 0.53, 0.60)
GRAY_300 = (0.80, 0.83, 0.87)
GRAY_200 = (0.89, 0.91, 0.94)
GRAY_100 = (0.96, 0.97, 0.98)
WHITE = (1.0, 1.0, 1.0)

AUTHOR = "Isaac J. Graterol"
EMAIL = "isaacjgraterol@gmail.com"
LINKEDIN = "linkedin.com/in/inggraterol"


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: object, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _escape_pdf_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _status_colors(status: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    value = status.upper()
    if value == "PASS":
        return GREEN, LIGHT_GREEN
    if value in {"WARNING", "PASS_WITH_UNHEALTHY_SESSIONS", "UNHEALTHY"}:
        return ORANGE, LIGHT_ORANGE
    if value in {"FAIL", "ERROR"}:
        return RED, LIGHT_RED
    if value == "NOT_EVALUATED":
        return PURPLE, (0.95, 0.93, 0.99)
    return GRAY_700, GRAY_100


def _approx_text_width(text: str, size: float, bold: bool = False) -> float:
    factor = 0.56 if bold else 0.52
    return len(text) * size * factor


def _fit_text_size(
    text: str,
    width: float,
    preferred: float,
    *,
    bold: bool = False,
    minimum: float = 6.8,
) -> float:
    size = preferred
    while size > minimum and _approx_text_width(text, size, bold) > width:
        size -= 0.25
    return max(minimum, size)


def _timezone_abbreviation(value: datetime) -> str:
    name = (value.tzname() or "").strip()
    if name and len(name) <= 5 and " " not in name:
        return name

    known = {
        "Mountain Daylight Time": "MDT",
        "Mountain Standard Time": "MST",
        "Central Daylight Time": "CDT",
        "Central Standard Time": "CST",
        "Eastern Daylight Time": "EDT",
        "Eastern Standard Time": "EST",
        "Pacific Daylight Time": "PDT",
        "Pacific Standard Time": "PST",
    }
    if name in known:
        return known[name]

    words = [word for word in name.replace("-", " " ).split() if word and word[0].isalpha()]
    if len(words) >= 2:
        acronym = "".join(word[0].upper() for word in words)
        if 2 <= len(acronym) <= 5:
            return acronym

    offset = value.strftime("%z")
    if len(offset) == 5:
        return f"UTC{offset[:3]}:{offset[3:]}"
    return "local"


def _format_generated_timestamp(value: datetime) -> str:
    return f"{value.strftime('%Y-%m-%d %H:%M')} {_timezone_abbreviation(value)}"


def _report_generated_timestamp(data: dict[str, object]) -> str:
    raw = data.get("generated_at_utc")
    if isinstance(raw, str) and raw.strip():
        try:
            value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            return _format_generated_timestamp(value)
    return _format_generated_timestamp(datetime.now().astimezone())


def _wrap_text(text: str, width: float, size: float, bold: bool = False) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _approx_text_width(candidate, size, bold) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


class _Page:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def raw(self, command: str) -> None:
        self.commands.append(command)

    def fill_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color: tuple[float, float, float],
    ) -> None:
        r, g, b = color
        self.raw(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")

    def stroke_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color: tuple[float, float, float] = GRAY_300,
        line_width: float = 0.7,
    ) -> None:
        r, g, b = color
        self.raw(
            f"{r:.3f} {g:.3f} {b:.3f} RG {line_width:.2f} w "
            f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S"
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = GRAY_300,
        line_width: float = 0.7,
    ) -> None:
        r, g, b = color
        self.raw(
            f"{r:.3f} {g:.3f} {b:.3f} RG {line_width:.2f} w "
            f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 10,
        color: tuple[float, float, float] = GRAY_900,
        bold: bool = False,
    ) -> None:
        r, g, b = color
        font = "/F2" if bold else "/F1"
        escaped = _escape_pdf_text(value)
        self.raw(
            f"BT {r:.3f} {g:.3f} {b:.3f} rg {font} {size:.2f} Tf "
            f"1 0 0 1 {x:.2f} {y:.2f} Tm ({escaped}) Tj ET"
        )

    def wrapped_text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        width: float,
        size: float = 9,
        leading: float = 12,
        color: tuple[float, float, float] = GRAY_700,
        bold: bool = False,
        max_lines: int | None = None,
    ) -> float:
        lines = _wrap_text(value, width, size, bold)
        if max_lines is not None:
            lines = lines[:max_lines]
        current_y = y
        for line in lines:
            self.text(x, current_y, line, size=size, color=color, bold=bold)
            current_y -= leading
        return current_y

    def badge(self, x: float, y: float, status: str, *, width: float = 78.0) -> None:
        fg, bg = _status_colors(status)
        self.fill_rect(x, y, width, 20, bg)
        self.stroke_rect(x, y, width, 20, fg, 0.7)
        text = status.replace("PASS_WITH_UNHEALTHY_SESSIONS", "UNHEALTHY")
        text_x = x + max(6.0, (width - _approx_text_width(text, 8.4, True)) / 2)
        self.text(text_x, y + 6.2, text, size=8.4, color=fg, bold=True)

    def card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        value: str,
        *,
        accent: tuple[float, float, float] = BLUE,
        value_size: float = 17,
    ) -> None:
        self.fill_rect(x, y, w, h, WHITE)
        self.stroke_rect(x, y, w, h, GRAY_200, 0.8)
        self.fill_rect(x, y, 4, h, accent)
        self.text(x + 12, y + h - 16, label.upper(), size=7.4, color=GRAY_500, bold=True)
        available = max(24.0, w - 24.0)
        fitted = _fit_text_size(value, available, value_size, bold=True, minimum=7.0)
        if _approx_text_width(value, fitted, True) <= available:
            self.text(x + 12, y + 13, value, size=fitted, color=GRAY_900, bold=True)
            return

        lines = _wrap_text(value, available, 7.0, True)[:2]
        baseline = y + 17 if len(lines) > 1 else y + 13
        for line in lines:
            self.text(x + 12, baseline, line, size=7.0, color=GRAY_900, bold=True)
            baseline -= 9


class _Pdf:
    def __init__(self) -> None:
        self.pages: list[_Page] = []

    def add_page(self) -> _Page:
        page = _Page()
        self.pages.append(page)
        return page

    def to_bytes(self) -> bytes:
        pages = self.pages or [_Page()]
        objects: dict[int, bytes] = {}
        catalog_obj = 1
        pages_obj = 2
        font_regular_obj = 3
        font_bold_obj = 4
        objects[catalog_obj] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[font_regular_obj] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
        objects[font_bold_obj] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"

        kids: list[int] = []
        next_obj = 5
        for page in pages:
            page_obj = next_obj
            content_obj = next_obj + 1
            next_obj += 2
            kids.append(page_obj)
            stream = ("\n".join(page.commands) + "\n").encode("latin-1", errors="replace")
            objects[page_obj] = (
                f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
                f"/Resources << /Font << /F1 {font_regular_obj} 0 R /F2 {font_bold_obj} 0 R >> >> "
                f"/Contents {content_obj} 0 R >>"
            ).encode("ascii")
            objects[content_obj] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
                + stream
                + b"endstream"
            )

        kids_ref = " ".join(f"{obj} 0 R" for obj in kids)
        objects[pages_obj] = (
            f"<< /Type /Pages /Kids [{kids_ref}] /Count {len(kids)} >>"
        ).encode("ascii")

        output = bytearray(b"%PDF-1.4\n%MWEX\n")
        offsets: dict[int, int] = {}
        for obj_num in sorted(objects):
            offsets[obj_num] = len(output)
            output.extend(f"{obj_num} 0 obj\n".encode("ascii"))
            output.extend(objects[obj_num])
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        max_obj = max(objects)
        output.extend(f"xref\n0 {max_obj + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for obj_num in range(1, max_obj + 1):
            offset = offsets.get(obj_num, 0)
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            f"trailer\n<< /Size {max_obj + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return bytes(output)


def _section_title(page: _Page, y: float, title: str, subtitle: str = "") -> float:
    page.text(MARGIN, y, title, size=13.5, color=GRAY_900, bold=True)
    y -= 15
    if subtitle:
        page.wrapped_text(MARGIN, y, subtitle, width=CONTENT_W, size=8.5, leading=10, color=GRAY_500)
        y -= 16
    else:
        y -= 6
    page.line(MARGIN, y, PAGE_W - MARGIN, y, GRAY_200, 0.8)
    return y - 13


def _footer(page: _Page, page_num: int, total: int) -> None:
    page.line(MARGIN, 34, PAGE_W - MARGIN, 34, GRAY_200, 0.6)
    page.text(MARGIN, 20, f"Maintenance Window Automation | {AUTHOR}", size=7.2, color=GRAY_500)
    page.text(PAGE_W - MARGIN - 55, 20, f"Page {page_num} / {total}", size=7.2, color=GRAY_500)


def _global_sections(data: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    global_summary = _as_dict(data.get("global_summary"))
    state = _as_dict(global_summary.get("state"))
    health = _as_dict(global_summary.get("session_health"))
    if not state:
        state = _as_dict(_as_dict(_as_dict(data.get("module_summary")).get("state")).get("summary"))
    if not health:
        modules = _as_dict(data.get("module_summary"))
        health = _as_dict(_as_dict(modules.get("session-health") or modules.get("session_health")).get("summary"))
    return global_summary, state, health


def _device_summaries(data: dict[str, object]) -> list[dict[str, object]]:
    summaries = [item for item in _as_list(data.get("device_summary")) if isinstance(item, dict)]
    if summaries:
        return summaries

    reports = _as_dict(data.get("reports"))
    state_reports = {
        _text(item.get("device"), ""): item
        for item in _as_list(reports.get("state"))
        if isinstance(item, dict) and item.get("device") is not None
    }
    health_reports = {
        _text(item.get("device"), ""): item
        for item in _as_list(reports.get("session_health"))
        if isinstance(item, dict) and item.get("device") is not None
    }
    devices: list[str] = []
    for device in [*state_reports, *health_reports]:
        if device and device not in devices:
            devices.append(device)

    result: list[dict[str, object]] = []
    for device in devices:
        state_report = _as_dict(state_reports.get(device))
        health_report = _as_dict(health_reports.get(device))
        before = _as_dict(state_report.get("before"))
        after = _as_dict(state_report.get("after"))
        findings = _finding_counts_from_health_report(health_report)
        result.append(
            {
                "device": device,
                "overall_result": _text(health_report.get("result") or state_report.get("result"), "UNKNOWN"),
                "state": {
                    "result": _text(state_report.get("result"), "UNKNOWN"),
                    "total_sessions_before": _int(before.get("total_sessions")),
                    "total_sessions_after": _int(after.get("total_sessions")),
                    "lost_sessions": _int(state_report.get("lost_sessions_count")),
                    "new_sessions": _int(state_report.get("new_sessions_count")),
                    "state_changes": _int(state_report.get("state_changes_count")),
                    "new_unhealthy": _int(state_report.get("new_unhealthy_count")),
                    "persistent_unhealthy": _int(state_report.get("persistent_unhealthy_count")),
                },
                "session_health": {
                    "result": _text(health_report.get("result"), "UNKNOWN"),
                    "total_peers": _int(health_report.get("peers_total")),
                    "passed_peers": _int(health_report.get("peers_passed")),
                    "failed_peers": _int(health_report.get("peers_failed")),
                    "warning_peers": _int(health_report.get("peers_warning")),
                    "unhealthy_peers": _int(health_report.get("peers_unhealthy")),
                    "not_evaluated_peers": _int(health_report.get("peers_not_evaluated")),
                    "families_total": _int(health_report.get("families_total")),
                    "warning_families": _int(health_report.get("families_warning")),
                    "failed_families": _int(health_report.get("families_failed")),
                },
                "finding_counts": findings,
            }
        )
    return result


def _finding_counts_from_health_report(report: dict[str, object]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for peer in _as_list(report.get("peers")):
        if not isinstance(peer, dict):
            continue
        for finding in _as_list(peer.get("findings")):
            if isinstance(finding, dict):
                counts[_text(finding.get("rule"), "unknown")] += 1
        for family in _as_list(peer.get("families")):
            if not isinstance(family, dict):
                continue
            for finding in _as_list(family.get("findings")):
                if isinstance(finding, dict):
                    counts[_text(finding.get("rule"), "unknown")] += 1
    return dict(counts)


def _global_finding_counts(data: dict[str, object], devices: list[dict[str, object]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in devices:
        for rule, value in _as_dict(item.get("finding_counts")).items():
            counts[str(rule)] += _int(value)
    if counts:
        return counts

    reports = _as_dict(data.get("reports"))
    for report in _as_list(reports.get("session_health")):
        if isinstance(report, dict):
            counts.update(_finding_counts_from_health_report(report))
    return counts


def _attention_peers(data: dict[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    reports = _as_dict(data.get("reports"))
    for report in _as_list(reports.get("session_health")):
        if not isinstance(report, dict):
            continue
        device = _text(report.get("device"))
        for peer in _as_list(report.get("peers")):
            if not isinstance(peer, dict):
                continue
            peer_result = _text(peer.get("result"), "PASS")
            if peer_result == "PASS":
                continue
            peer_findings = [f for f in _as_list(peer.get("findings")) if isinstance(f, dict)]
            families = [f for f in _as_list(peer.get("families")) if isinstance(f, dict)]
            warning_family_count = sum(1 for family in families if _text(family.get("result"), "PASS") != "PASS")
            rules = [_text(f.get("rule"), "") for f in peer_findings]
            before = _as_dict(peer.get("before"))
            after = _as_dict(peer.get("after"))
            result.append(
                {
                    "device": device,
                    "peer": _text(peer.get("peer") or peer.get("neighbor") or before.get("neighbor") or after.get("neighbor")),
                    "result": peer_result,
                    "state": f"{_text(before.get('state'))} -> {_text(after.get('state'))}",
                    "rules": [rule for rule in rules if rule],
                    "warning_families": warning_family_count,
                }
            )
    return result


def _evidence_rows(data: dict[str, object]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    reports = _as_dict(data.get("reports"))
    for report in _as_list(reports.get("state")):
        if not isinstance(report, dict):
            continue
        before = _as_dict(report.get("before"))
        after = _as_dict(report.get("after"))
        rows.append(
            {
                "device": _text(report.get("device")),
                "before": _text(before.get("source_actual") or before.get("source_requested")),
                "after": _text(after.get("source_actual") or after.get("source_requested")),
            }
        )
    return rows


def _header(page: _Page, data: dict[str, object], overall: str) -> None:
    page.fill_rect(0, PAGE_H - 112, PAGE_W, 112, NAVY)
    page.text(MARGIN, PAGE_H - 34, "MAINTENANCE WINDOW AUTOMATION", size=8.5, color=(0.56, 0.72, 0.95), bold=True)
    page.text(MARGIN, PAGE_H - 61, "Executive Report", size=23, color=WHITE, bold=True)
    page.text(MARGIN, PAGE_H - 82, "BGP before/after validation with operator-focused findings", size=9, color=(0.83, 0.88, 0.95))
    page.badge(PAGE_W - MARGIN - 92, PAGE_H - 70, overall, width=92)
    mw_label = f"MW ID: {_text(data.get('mw_id'))}"
    mw_size = _fit_text_size(mw_label, 176.0, 8.5, bold=True, minimum=6.8)
    page.text(PAGE_W - MARGIN - 176, PAGE_H - 92, mw_label, size=mw_size, color=WHITE, bold=True)


def _draw_module_row(page: _Page, y: float, name: str, status: str) -> float:
    page.fill_rect(MARGIN, y - 2, CONTENT_W, 28, GRAY_100)
    page.text(MARGIN + 10, y + 7, name, size=9.5, color=GRAY_900, bold=True)
    page.badge(PAGE_W - MARGIN - 88, y + 2, status, width=78)
    return y - 32


def _draw_bar(
    page: _Page,
    x: float,
    y: float,
    label: str,
    value: int,
    max_value: int,
    *,
    width: float,
    color: tuple[float, float, float],
) -> float:
    page.text(x, y + 2, label, size=8, color=GRAY_700)
    bar_x = x + 112
    bar_w = width - 150
    page.fill_rect(bar_x, y, bar_w, 9, GRAY_200)
    fill_w = 0 if max_value <= 0 else max(2.0 if value > 0 else 0.0, bar_w * (value / max_value))
    if fill_w > 0:
        page.fill_rect(bar_x, y, fill_w, 9, color)
    page.text(x + width - 28, y + 1, str(value), size=8, color=GRAY_900, bold=True)
    return y - 17


def _page_one(pdf: _Pdf, data: dict[str, object], devices: list[dict[str, object]], findings: Counter[str]) -> None:
    page = pdf.add_page()
    global_summary, state, health = _global_sections(data)
    overall = _text(data.get("result") or global_summary.get("overall_result"), "UNKNOWN")
    _header(page, data, overall)

    generated = _report_generated_timestamp(data)
    page.text(MARGIN, 655, "REPORT CONTEXT", size=8, color=GRAY_500, bold=True)
    metadata = [
        ("Protocol", _text(data.get("protocol"), "BGP").upper()),
        ("Stages", f"{_text(data.get('before_stage'), 'before')} -> {_text(data.get('after_stage'), 'after')}") ,
        ("Devices", str(len(_as_list(data.get("devices"))) or len(devices))),
        ("Generated", generated),
    ]
    card_gap = 8
    card_w = (CONTENT_W - (3 * card_gap)) / 4
    x = MARGIN
    for label, value in metadata:
        page.card(x, 602, card_w, 44, label, value, accent=BLUE, value_size=11.0 if label == "Generated" else 13)
        x += card_w + card_gap

    y = _section_title(page, 580, "Executive Summary", "Fast operational view of the maintenance-window outcome.")
    total_peers = _int(health.get("total_peers"))
    warning_peers = _int(health.get("total_warning_peers"))
    unhealthy_peers = _int(health.get("total_unhealthy_peers"))
    warning_families = _int(health.get("total_warning_families"))
    restarts = findings["session_restart_detected"]
    prefix_deltas = findings["prefix_delta"]
    kpis = [
        ("Total peers", total_peers, BLUE),
        ("Warning peers", warning_peers, ORANGE),
        ("Unhealthy peers", unhealthy_peers, ORANGE),
        ("Warning families", warning_families, PURPLE),
        ("Session restarts", restarts, RED if restarts else GREEN),
        ("Prefix deltas", prefix_deltas, BLUE),
    ]
    gap = 8
    w = (CONTENT_W - (2 * gap)) / 3
    for idx, (label, value, accent) in enumerate(kpis):
        row = idx // 3
        col = idx % 3
        page.card(MARGIN + col * (w + gap), y - 54 - row * 62, w, 52, label, str(value), accent=accent)

    modules_y = y - 142
    page.text(MARGIN, modules_y + 10, "MODULE STATUS", size=8, color=GRAY_500, bold=True)
    modules_y -= 20
    modules = _as_dict(global_summary.get("modules"))
    modules_y = _draw_module_row(page, modules_y, "BGP State", _text(data.get("state_result") or modules.get("state"), "UNKNOWN"))
    modules_y = _draw_module_row(page, modules_y, "BGP Session Health", _text(data.get("session_health_result") or modules.get("session-health"), "UNKNOWN"))

    chart_y = modules_y - 5
    page.text(MARGIN, chart_y, "PEER HEALTH DISTRIBUTION", size=8, color=GRAY_500, bold=True)
    chart_y -= 19
    passed = max(0, total_peers - warning_peers - unhealthy_peers - _int(health.get("total_failed_peers")) - _int(health.get("total_not_evaluated_peers")))
    peer_values = [
        ("Pass", passed, GREEN),
        ("Warning", warning_peers, ORANGE),
        ("Unhealthy", unhealthy_peers, RED),
        ("Failed", _int(health.get("total_failed_peers")), RED),
        ("Not evaluated", _int(health.get("total_not_evaluated_peers")), PURPLE),
    ]
    max_peer = max([value for _, value, _ in peer_values] + [1])
    for label, value, color in peer_values:
        chart_y = _draw_bar(page, MARGIN, chart_y, label, value, max_peer, width=CONTENT_W, color=color)

    note_y = 86
    page.fill_rect(MARGIN, note_y, CONTENT_W, 50, LIGHT_BLUE)
    page.stroke_rect(MARGIN, note_y, CONTENT_W, 50, (0.72, 0.83, 0.96), 0.7)
    page.text(MARGIN + 12, note_y + 33, "Executive interpretation", size=9, color=NAVY_2, bold=True)
    state_result = _text(data.get("state_result") or modules.get("state"), "UNKNOWN")
    health_result = _text(data.get("session_health_result") or modules.get("session-health"), "UNKNOWN")
    interpretation = (
        f"State validation: {state_result}. Session health: {health_result}. "
        f"Detected {restarts} session restart(s), {warning_peers} warning peer(s), "
        f"{unhealthy_peers} persistent unhealthy peer(s), and {warning_families} warning family/table result(s)."
    )
    page.wrapped_text(MARGIN + 12, note_y + 20, interpretation, width=CONTENT_W - 24, size=8.2, leading=10, color=GRAY_700, max_lines=2)


def _page_two(pdf: _Pdf, data: dict[str, object], devices: list[dict[str, object]], findings: Counter[str]) -> None:
    page = pdf.add_page()
    page.fill_rect(0, PAGE_H - 62, PAGE_W, 62, NAVY)
    page.text(MARGIN, PAGE_H - 30, "DEVICE EXECUTIVE SUMMARY", size=15.5, color=WHITE, bold=True)
    page.text(MARGIN, PAGE_H - 47, "Per-device outcome and operational findings", size=8.5, color=(0.82, 0.88, 0.95))

    y = 706
    cols = [
        ("Device", 95),
        ("Overall", 68),
        ("State", 58),
        ("Health", 68),
        ("Sessions", 62),
        ("Peers W/U", 62),
        ("Fam W/T", 62),
        ("Restarts", 52),
    ]
    x = MARGIN
    page.fill_rect(MARGIN, y, CONTENT_W, 24, GRAY_100)
    for label, width in cols:
        page.text(x + 4, y + 8, label.upper(), size=6.9, color=GRAY_500, bold=True)
        x += width
    y -= 30

    for item in devices[:10]:
        state = _as_dict(item.get("state"))
        health = _as_dict(item.get("session_health"))
        fcounts = _as_dict(item.get("finding_counts"))
        row_h = 30
        page.line(MARGIN, y - 5, PAGE_W - MARGIN, y - 5, GRAY_200, 0.5)
        x = MARGIN
        page.text(x + 4, y + 5, _text(item.get("device")), size=8.2, color=GRAY_900, bold=True); x += 95
        page.text(x + 4, y + 5, _text(item.get("overall_result")), size=7.1, color=_status_colors(_text(item.get("overall_result")))[0], bold=True); x += 68
        page.text(x + 4, y + 5, _text(state.get("result")), size=7.1, color=_status_colors(_text(state.get("result")))[0], bold=True); x += 58
        page.text(x + 4, y + 5, _text(health.get("result")), size=7.1, color=_status_colors(_text(health.get("result")))[0], bold=True); x += 68
        page.text(x + 4, y + 5, f"{_int(state.get('total_sessions_before'))}->{_int(state.get('total_sessions_after'))}", size=7.5); x += 62
        page.text(x + 4, y + 5, f"{_int(health.get('warning_peers'))}/{_int(health.get('unhealthy_peers'))}", size=7.5); x += 62
        page.text(x + 4, y + 5, f"{_int(health.get('warning_families'))}/{_int(health.get('families_total'))}", size=7.5); x += 62
        page.text(x + 4, y + 5, str(_int(fcounts.get("session_restart_detected"))), size=7.5, bold=True)
        y -= row_h

    y -= 8
    y = _section_title(page, y, "Finding distribution", "Counts are factual findings, not a weighted risk score.")
    display_rules = [
        ("Session restarts", findings["session_restart_detected"], RED),
        ("Uptime resets", findings["uptime_reset"], ORANGE),
        ("Flap count increases", findings["flap_count_increased"], ORANGE),
        ("Flap count resets", findings["flap_count_reset"], ORANGE),
        ("New families", findings["new_family_after"], BLUE),
        ("Missing families", findings["missing_family_after"], RED),
        ("Persistent unhealthy", findings["persistent_unhealthy_peer"], RED),
        ("Prefix deltas", findings["prefix_delta"], PURPLE),
    ]
    max_value = max([value for _, value, _ in display_rules] + [1])
    for label, value, color in display_rules:
        y = _draw_bar(page, MARGIN, y, label, value, max_value, width=CONTENT_W, color=color)

    y -= 4
    page.fill_rect(MARGIN, y - 58, CONTENT_W, 58, GRAY_100)
    page.stroke_rect(MARGIN, y - 58, CONTENT_W, 58, GRAY_200, 0.7)
    page.text(MARGIN + 12, y - 17, "Evidence completeness", size=9, color=GRAY_900, bold=True)
    evidence = _evidence_rows(data)
    evidence_text = "; ".join(f"{row['device']}: {row['before']} -> {row['after']}" for row in evidence) or "Source metadata is available in the JSON report."
    page.wrapped_text(MARGIN + 12, y - 31, evidence_text, width=CONTENT_W - 24, size=8.2, leading=10, color=GRAY_700, max_lines=2)


def _finding_summary_phrase(peer: dict[str, object]) -> str:
    rules = [str(rule) for rule in peer.get("rules", []) if rule]
    selected = [rule.replace("_", " ") for rule in rules if rule != "prefix_delta"]
    family_count = _int(peer.get("warning_families"))
    if family_count:
        selected.append(f"{family_count} warning family/table(s)")
    if not selected:
        selected.append("family/table warning(s)")
    return ", ".join(selected[:3])


def _page_three(pdf: _Pdf, data: dict[str, object], devices: list[dict[str, object]], findings: Counter[str]) -> None:
    page = pdf.add_page()
    page.fill_rect(0, PAGE_H - 62, PAGE_W, 62, NAVY)
    page.text(MARGIN, PAGE_H - 30, "OPERATIONAL ATTENTION", size=15.5, color=WHITE, bold=True)
    page.text(MARGIN, PAGE_H - 47, "Peers and findings that deserve operator review", size=8.5, color=(0.82, 0.88, 0.95))

    y = 706
    attention = _attention_peers(data)
    if attention:
        page.fill_rect(MARGIN, y, CONTENT_W, 24, GRAY_100)
        headers = [("Device", 88), ("Peer", 112), ("Result", 62), ("State", 112), ("Why it matters", 154)]
        x = MARGIN
        for label, width in headers:
            page.text(x + 4, y + 8, label.upper(), size=6.8, color=GRAY_500, bold=True)
            x += width
        y -= 30
        for item in attention[:12]:
            x = MARGIN
            page.line(MARGIN, y - 7, PAGE_W - MARGIN, y - 7, GRAY_200, 0.5)
            page.text(x + 4, y + 4, _text(item.get("device")), size=7.4, bold=True); x += 88
            page.text(x + 4, y + 4, _text(item.get("peer")), size=7.0); x += 112
            status = _text(item.get("result"))
            status_size = _fit_text_size(status, 54.0, 7.1, bold=True, minimum=6.4)
            page.text(x + 4, y + 4, status, size=status_size, color=_status_colors(status)[0], bold=True); x += 62
            state_text = _text(item.get("state"))
            state_size = _fit_text_size(state_text, 104.0, 7.0, minimum=6.2)
            page.text(x + 4, y + 4, state_text, size=state_size); x += 112
            phrase = _finding_summary_phrase(item)
            page.wrapped_text(x + 4, y + 4, phrase, width=148, size=6.8, leading=8, color=GRAY_700, max_lines=2)
            y -= 27
    else:
        page.text(MARGIN, y, "No non-PASS peers were present in the report.", size=9, color=GRAY_700)
        y -= 28

    y -= 8
    y = _section_title(page, y, "Finding inventory", "Complete technical evidence remains available in Detail TXT and JSON.")
    ordered = sorted(findings.items(), key=lambda item: (-item[1], item[0]))
    if not ordered:
        page.text(MARGIN, y, "No findings recorded.", size=9, color=GRAY_700)
        y -= 20
    else:
        left = ordered[:7]
        right = ordered[7:14]
        col_w = (CONTENT_W - 14) / 2
        for col, values in enumerate((left, right)):
            x = MARGIN + col * (col_w + 14)
            cy = y
            for rule, count in values:
                page.fill_rect(x, cy - 2, col_w, 22, GRAY_100)
                page.text(x + 7, cy + 6, rule.replace("_", " "), size=7.5, color=GRAY_700)
                page.text(x + col_w - 28, cy + 6, str(count), size=8, color=GRAY_900, bold=True)
                cy -= 27
        y -= max(len(left), len(right)) * 27 + 6

    page.fill_rect(MARGIN, 112, CONTENT_W, 105, LIGHT_BLUE)
    page.stroke_rect(MARGIN, 112, CONTENT_W, 105, (0.72, 0.83, 0.96), 0.8)
    page.text(MARGIN + 14, 194, "Report usage", size=10, color=NAVY_2, bold=True)
    guidance = (
        "This PDF is designed for executive and operational review. It intentionally summarizes repetitive "
        "prefix-level detail. Use the Summary TXT for a structured complete warning list, the Detail TXT for "
        "peer/family evidence, and JSON for machine-readable audit evidence."
    )
    page.wrapped_text(MARGIN + 14, 178, guidance, width=CONTENT_W - 28, size=8.3, leading=11, color=GRAY_700, max_lines=4)
    page.text(MARGIN + 14, 132, f"Contact: {AUTHOR} | {EMAIL} | {LINKEDIN}", size=8.2, color=NAVY_2, bold=True)


def build_executive_pdf(data: dict[str, object]) -> bytes:
    """Render an executive PDF from an already-generated report payload."""
    devices = _device_summaries(data)
    findings = _global_finding_counts(data, devices)
    pdf = _Pdf()
    _page_one(pdf, data, devices, findings)
    _page_two(pdf, data, devices, findings)
    _page_three(pdf, data, devices, findings)
    total = len(pdf.pages)
    for index, page in enumerate(pdf.pages, start=1):
        _footer(page, index, total)
    return pdf.to_bytes()


def write_executive_pdf(data: dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(build_executive_pdf(data))
    return output_path
