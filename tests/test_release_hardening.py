from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from maintenance_window.protocols.bgp.full_report import reports
from maintenance_window.ui import report_downloads
from maintenance_window.ui.server import _write_runtime_credentials


def test_full_payload_has_global_finding_inventory() -> None:
    request = type("Request", (), {
        "mw_id": "MW_DEMO_001",
        "before_stage": "before",
        "after_stage": "after",
        "device_names": ["192.0.2.10"],
    })()
    health = {
        "device": "192.0.2.10",
        "result": "WARNING",
        "peers_total": 1,
        "peers_warning": 1,
        "peers": [
            {
                "neighbor": "198.51.100.1",
                "findings": [
                    {"rule": "session_restart_detected", "severity": "WARNING"},
                    {"rule": "persistent_unhealthy_peer", "severity": "UNHEALTHY"},
                ],
                "families": [
                    {"findings": [{"rule": "new_family_after", "severity": "WARNING"}]},
                    {"findings": [{"rule": "missing_family_after", "severity": "WARNING"}]},
                    {"findings": [{"rule": "prefix_delta", "severity": "WARNING"}]},
                ],
            }
        ],
    }
    payload = reports.build_full_report_payload(
        request=request,
        state_reports=[{"device": "192.0.2.10", "result": "PASS"}],
        session_health_reports=[health],
    )

    assert payload["finding_counts"] == {
        "missing_family_after": 1,
        "new_family_after": 1,
        "persistent_unhealthy_peer": 1,
        "prefix_delta": 1,
        "session_restart_detected": 1,
    }
    assert payload["global_summary"]["finding_counts"] == payload["finding_counts"]

    summary = reports.format_full_summary(payload)
    assert "KEY FINDING INVENTORY" in summary
    assert "Session restarts: 1" in summary
    assert "New families: 1" in summary
    assert "Missing families: 1" in summary
    assert "Prefix deltas: 1" in summary
    assert "Persistent unhealthy peers: 1" in summary



def test_full_summary_formats_source_coverage_for_operators() -> None:
    request = type("Request", (), {
        "mw_id": "MW_DEMO_001",
        "before_stage": "before",
        "after_stage": "after",
        "device_names": ["192.0.2.10"],
    })()
    state = {
        "device": "192.0.2.10",
        "result": "PASS",
        "before": {"source_requested": "pyez", "source_actual": "pyez"},
        "after": {"source_requested": "pyez", "source_actual": "pyez"},
    }
    health = {
        "device": "192.0.2.10",
        "result": "PASS",
        "peers": [],
    }
    payload = reports.build_full_report_payload(
        request=request,
        state_reports=[state],
        session_health_reports=[health],
    )
    summary = reports.format_full_summary(payload)
    assert "Before actual: pyez: 1" in summary
    assert "After actual: pyez: 1" in summary
    assert "{'pyez': 1}" not in summary

def test_report_download_rejects_arbitrary_project_json(tmp_path: Path) -> None:
    secret = tmp_path / "auth" / "credentials.json"
    secret.parent.mkdir(parents=True)
    secret.write_text('{"password": "password"}', encoding="utf-8")

    with pytest.raises(ValueError):
        report_downloads.resolve_report_download(
            tmp_path,
            export_path_text=str(secret),
            kind="json",
        )


def test_report_download_rejects_non_comparison_directory(tmp_path: Path) -> None:
    bad = tmp_path / "outputs" / "snapshots" / "bgp" / "MW_DEMO" / "before" / "reports"
    bad.mkdir(parents=True)
    with pytest.raises(ValueError):
        report_downloads.resolve_report_download(tmp_path, str(bad), "json")


def test_report_download_accepts_exact_comparison_directory(tmp_path: Path) -> None:
    report_dir = (
        tmp_path / "outputs" / "snapshots" / "bgp" / "MW_DEMO" /
        "comparison_reports" / "20260906_120000"
    )
    report_dir.mkdir(parents=True)
    (report_dir / "full_report.json").write_text('{"result":"PASS"}', encoding="utf-8")
    download = report_downloads.resolve_report_download(tmp_path, str(report_dir), "json")
    assert download.path.name == "full_report.json"


def test_gui_runtime_credentials_use_os_temp_not_project(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    path = _write_runtime_credentials("operator", "password")
    try:
        assert path.is_file()
        assert path.parent == tmp_path / "maintenance_window" / "gui_credentials"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["profiles"]["gui_radius_runtime"]["username"] == "operator"
    finally:
        path.unlink(missing_ok=True)


def _load_release_scanner(root: Path):
    spec = importlib.util.spec_from_file_location(
        "public_release_check_test_module",
        root / "tools" / "public_release_check.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_scanner_detects_non_documentation_ip_even_before_underscore() -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)
    unsafe = "172" + ".20.24.2_timestamp.xml"
    address = scanner.IPV4_CANDIDATE.findall(unsafe)[0]
    import ipaddress
    assert not scanner._ipv4_is_public_fixture_safe(ipaddress.ip_address(address))


def test_release_scanner_checks_secret_like_values_inside_tests(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    key = "pass" + "word"
    unsafe_value = "operator-prod-" + "credential-2026"
    fixture_text = (
        f'safe = {{"{key}": "password"}}\n'
        f'unsafe = {{"{key}": "{unsafe_value}"}}\n'
    )
    (tests_dir / "test_fixture.py").write_text(
        fixture_text,
        encoding="utf-8",
    )
    findings = scanner.scan_sensitive_data(tmp_path)
    assert any(
        item.rule == "embedded_secret"
        and item.path == "tests/test_fixture.py"
        for item in findings
    )


def test_release_scanner_detects_obvious_credential_tokens(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)
    token_file = tmp_path / "fixture.txt"
    label = "to" + "ken"
    access_prefix = "AK" + "IA"
    token_file.write_text(
        label + "=" + access_prefix + "A" * 16 + "\n",
        encoding="utf-8",
    )
    findings = scanner.scan_sensitive_data(tmp_path)
    assert any(item.rule == "credential_token" for item in findings)


def test_release_scanner_allows_documentation_ipv4() -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)
    import ipaddress
    assert scanner._ipv4_is_public_fixture_safe(ipaddress.ip_address("192.0.2.10"))
    assert scanner._ipv4_is_public_fixture_safe(ipaddress.ip_address("198.51.100.1"))
    assert scanner._ipv4_is_public_fixture_safe(ipaddress.ip_address("203.0.113.44"))


def test_gui_source_labels_make_platform_scope_explicit() -> None:
    from maintenance_window.ui.options import SOURCE_LABELS

    assert SOURCE_LABELS["pyez"] == "PyEZ / NETCONF - Juniper Junos"
    assert SOURCE_LABELS["ssh"] == "SSH CLI JSON - Juniper Junos"
    assert SOURCE_LABELS["gnmic"] == "gNMI / OpenConfig - Juniper Junos validated"
    assert "Cisco" not in SOURCE_LABELS["gnmic"]
    assert "Nokia" not in SOURCE_LABELS["gnmic"]


def test_report_download_accepts_relative_comparison_directory(tmp_path: Path) -> None:
    report_dir = (
        tmp_path
        / "outputs"
        / "snapshots"
        / "bgp"
        / "MW_DEMO"
        / "comparison_reports"
        / "20260906_120000"
    )
    report_dir.mkdir(parents=True)
    (report_dir / "full_report.json").write_text('{"result":"PASS"}', encoding="utf-8")

    download = report_downloads.resolve_report_download(
        tmp_path,
        "outputs/snapshots/bgp/MW_DEMO/comparison_reports/20260906_120000",
        "json",
    )
    assert download.path == report_dir / "full_report.json"


def test_connection_defaults_are_compatibility_mode() -> None:
    root = Path(__file__).resolve().parents[1]
    settings = json.loads((root / "config/connections/settings.json").read_text(encoding="utf-8"))

    assert settings["ssh"]["verify_host_key"] is False
    assert settings["pyez"]["verify_host_key"] is False
    assert settings["gnmic"]["insecure"] is True
    assert settings["gnmic"]["skip_verify"] is False


def test_full_report_package_keeps_lazy_public_cli_exports() -> None:
    import maintenance_window.protocols.bgp.full_report as full_report

    assert callable(full_report.run_bgp_full_report)
    assert callable(full_report.run_bgp_full_report_comparison)


def test_public_demo_generator_uses_real_rules_and_exact_inventory() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "generate_public_demo_test_module",
        root / "tools" / "generate_public_demo.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    payload = module.build_demo_payload()
    assert payload["result"] == "WARNING"
    assert payload["state_result"] == "PASS"
    assert payload["session_health_result"] == "WARNING"
    assert payload["finding_counts"] == module.EXPECTED_FINDINGS
    assert payload["generated_at_utc"] == module.AFTER_CREATED


def test_report_reader_formats_source_coverage_for_gui(tmp_path: Path) -> None:
    from maintenance_window.ui.report_reader import read_report_summary

    report = tmp_path / "full_report.json"
    report.write_text(
        json.dumps(
            {
                "result": "PASS",
                "source_coverage": {
                    "before_actual": {"pyez": 2},
                    "after_actual": {"pyez": 2},
                    "fallback_device_count": 0,
                },
                "reports": {"state": [], "session_health": []},
            }
        ),
        encoding="utf-8",
    )
    summary = read_report_summary(report)
    assert summary["before_source_coverage"] == "pyez: 2"
    assert summary["after_source_coverage"] == "pyez: 2"


def test_main_gui_discloses_compatibility_security_mode(capsys: pytest.CaptureFixture[str]) -> None:
    from maintenance_window.ui import server

    html = server._render_index(server.UiState())
    assert "Compatibility Mode (default)" in html
    assert "docs/ADVANCED_SECURITY.md" in html
    assert "removed after normal completion" in html

    with pytest.raises(SystemExit) as exc_info:
        server.main(["--help"])
    assert exc_info.value.code == 0
    assert "usage:" in capsys.readouterr().out.lower()


def test_release_scanner_ipv6_policy() -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)
    import ipaddress

    assert scanner._ipv6_is_public_fixture_safe(ipaddress.ip_address("2001:db8::10"))
    assert scanner._ipv6_is_public_fixture_safe(ipaddress.ip_address("::1"))
    assert not scanner._ipv6_is_public_fixture_safe(ipaddress.ip_address("fd00" + chr(58) * 2 + "10"))


def test_cli_snapshot_request_rejects_unsafe_mw_id_before_io() -> None:
    import argparse
    from maintenance_window.cli_handlers.snapshot_comparison.request import (
        build_snapshot_comparison_request,
    )

    args = argparse.Namespace(
        mw_id="..",
        compare_snapshots="before,after",
        inventory=Path("does-not-need-to-exist.txt"),
        device="all",
        export=None,
        module="full",
        output="summary",
    )
    with pytest.raises(ValueError, match="MW ID"):
        build_snapshot_comparison_request(args)


def test_standard_snapshot_validation_rejects_unsafe_mw_id() -> None:
    import argparse
    from maintenance_window.cli_handlers.validation.request import (
        validate_validation_request,
    )

    args = argparse.Namespace(
        source="ssh",
        snapshot="before",
        mw_id="..",
        workers=1,
    )
    with pytest.raises(ValueError, match="MW ID"):
        validate_validation_request(args)


def test_public_demo_files_do_not_leak_temporary_build_paths(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "generate_public_demo_output_test_module",
        root / "tools" / "generate_public_demo.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    outputs = module.write_public_examples(tmp_path)
    summary_bytes = outputs["summary"].read_bytes()
    detail_bytes = outputs["detail"].read_bytes()
    assert b"\r\n" not in summary_bytes
    assert b"\r\n" not in detail_bytes
    summary = summary_bytes.decode("utf-8")
    detail = detail_bytes.decode("utf-8")
    for text in (summary, detail):
        assert "maintenance_window_public_demo_" not in text
        assert "/tmp/" not in text
        assert "C:\\Users\\" not in text
        assert "Missing families: 1" in summary
    assert b"2026-09-06 16:10 UTC" in outputs["pdf"].read_bytes()


def test_main_gui_renders_platform_scoped_source_labels() -> None:
    from maintenance_window.ui.server import UiState, _render_index

    html = _render_index(UiState())
    assert "PyEZ / NETCONF - Juniper Junos" in html
    assert "SSH CLI JSON - Juniper Junos" in html
    assert "gNMI / OpenConfig - Juniper Junos validated" in html

def test_advanced_security_uses_wsl_paths_for_gnmic_tls() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "ADVANCED_SECURITY.md").read_text(encoding="utf-8")
    assert "must be valid WSL/Linux paths" in text
    assert '"tls_ca": "/mnt/c/NetworkKeys/ca.pem"' in text
    assert '"tls_cert": "/mnt/c/NetworkKeys/client.pem"' in text
    assert '"tls_key": "/mnt/c/NetworkKeys/client.key"' in text
    assert '"tls_ca": "C:\\' not in text



def test_gui_deletes_generated_download_after_send(monkeypatch, tmp_path: Path) -> None:
    from maintenance_window.ui import server

    generated = tmp_path / "generated_summary.txt"
    generated.write_text("temporary report", encoding="utf-8")
    download = report_downloads.ReportDownload(
        path=generated,
        content_type="text/plain; charset=utf-8",
        filename="MW_DEMO_summary.txt",
        delete_after_send=True,
    )
    monkeypatch.setattr(server, "resolve_report_download", lambda *args, **kwargs: download)

    class DummyHandler:
        def _send_file_download(self, path: Path, *, content_type: str, filename: str) -> None:
            assert path == generated
            assert path.exists()
            assert content_type.startswith("text/plain")
            assert filename == "MW_DEMO_summary.txt"

    server.MwGuiHandler._send_report_download(DummyHandler(), "kind=summary-txt")
    assert not generated.exists()


def test_public_release_scanner_rejects_unresolved_placeholders(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)
    (tmp_path / "README.md").write_text("Tests: " + "__TEST_" + "COUNT__\n", encoding="utf-8")
    findings = scanner.scan_sensitive_data(tmp_path)
    assert any(item.rule == "publication_placeholder" for item in findings)


def test_public_release_scanner_checks_ci_contract(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    scanner = _load_release_scanner(root)

    # Minimal tree for the structural function; missing release files are fine.
    (tmp_path / "src" / "maintenance_window" / "protocols" / "bgp").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        'name = "bgp-maintenance-window"\nversion = "1.0.0"\nrequires-python = ">=3.12,<3.13"\n',
        encoding="utf-8",
    )
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.parent.mkdir(parents=True)
    ci.write_text("runs-on: ubuntu-latest\n", encoding="utf-8")

    findings = scanner.check_release_structure(tmp_path)
    assert any(item.rule == "ci_contract" for item in findings)
