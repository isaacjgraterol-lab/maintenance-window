from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintenance_window.cli import build_parser
from maintenance_window.core.settings import (
    compose_runtime_settings,
    load_audit_settings,
    load_connection_settings,
    load_runtime_settings,
)


def test_connection_settings_reject_protocol_audits(
    tmp_path: Path,
) -> None:
    path = tmp_path / "connections.json"
    path.write_text(
        json.dumps(
            {
                "ssh": {"port": 22},
                "protocols": {"bgp": {}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must not contain protocol audit settings",
    ):
        load_connection_settings(path)


def test_split_settings_compose_current_runtime_contract(
    tmp_path: Path,
) -> None:
    connection_path = tmp_path / "connections.json"
    audit_path = tmp_path / "state.json"

    connection_path.write_text(
        json.dumps(
            {
                "ssh": {"port": 22},
                "pyez": {"port": 830},
                "gnmic": {"port": 57400},
            }
        ),
        encoding="utf-8",
    )
    audit_path.write_text(
        json.dumps(
            {
                "ssh_command": "show bgp summary",
                "gnmic_paths": ["/bgp/state"],
            }
        ),
        encoding="utf-8",
    )

    runtime = load_runtime_settings(
        protocol="bgp",
        connection_path=connection_path,
        audit_path=audit_path,
    )

    assert runtime["ssh"] == {"port": 22}
    assert runtime["pyez"] == {"port": 830}
    assert runtime["gnmic"] == {"port": 57400}
    assert runtime["protocols"]["bgp"] == {
        "ssh_command": "show bgp summary",
        "gnmic_paths": ["/bgp/state"],
    }


def test_compose_runtime_settings_does_not_mutate_sources() -> None:
    connections = {"ssh": {"port": 22}}
    audit = {"ssh_command": "show bgp summary"}

    runtime = compose_runtime_settings(
        protocol="bgp",
        connection_settings=connections,
        audit_settings=audit,
    )

    runtime["ssh"]["port"] = 2222
    runtime["protocols"]["bgp"]["ssh_command"] = "changed"

    assert connections == {"ssh": {"port": 22}}
    assert audit == {"ssh_command": "show bgp summary"}


def test_load_audit_settings_requires_json_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="must contain a JSON object",
    ):
        load_audit_settings(path)

def test_main_cli_accepts_only_implemented_protocols() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--protocol", "ospf"])


def test_legacy_settings_alias_is_rejected() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--protocol",
                "bgp",
                "--settings",
                "config/settings.json",
            ]
        )


def test_manifest_settings_compose_legacy_runtime_keys(
    tmp_path: Path,
) -> None:
    connection_path = tmp_path / "connections.json"
    audit_path = tmp_path / "session_health.json"

    connection_path.write_text(
        json.dumps(
            {
                "ssh": {"port": 22},
                "pyez": {"port": 830},
                "gnmic": {"port": 57400},
            }
        ),
        encoding="utf-8",
    )
    audit_path.write_text(
        json.dumps(
            {
                "module": "bgp.session_health",
                "version": 1,
                "sources": {
                    "ssh": {
                        "enabled": True,
                        "items": [
                            {
                                "name": "bgp_summary",
                                "command": "show bgp summary | display json | no-more",
                            }
                        ],
                    },
                    "pyez": {
                        "enabled": True,
                        "items": [
                            {
                                "name": "bgp_summary",
                                "rpc": "get_bgp_summary_information",
                            }
                        ],
                    },
                    "gnmi": {
                        "enabled": True,
                        "items": [
                            {
                                "name": "bgp_neighbor_session_state",
                                "path": "/bgp/state",
                            }
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    runtime = load_runtime_settings(
        protocol="bgp",
        connection_path=connection_path,
        audit_path=audit_path,
    )

    bgp_settings = runtime["protocols"]["bgp"]
    assert bgp_settings["module"] == "bgp.session_health"
    assert bgp_settings["ssh_command"] == "show bgp summary | display json | no-more"
    assert bgp_settings["pyez_rpc"] == "get_bgp_summary_information"
    assert bgp_settings["gnmic_paths"] == ["/bgp/state"]
    assert bgp_settings["sources"]["ssh"]["items"][0]["name"] == "bgp_summary"


def test_load_runtime_settings_resolves_reusable_evidence_manifest(
    tmp_path: Path,
) -> None:
    connection_path = tmp_path / "connections.json"
    audit_root = tmp_path / "config" / "audits" / "bgp"
    audit_root.mkdir(parents=True)
    audit_path = audit_root / "session_health.json"
    evidence_path = audit_root / "evidence_basic.json"

    connection_path.write_text(
        json.dumps(
            {
                "ssh": {"port": 22},
                "pyez": {"port": 830},
                "gnmic": {"port": 57400},
            }
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            {
                "module": "bgp.evidence.basic",
                "capture_level": "basic",
                "sources": {
                    "ssh": {
                        "items": [
                            {
                                "name": "bgp_summary",
                                "command": "show bgp summary | display json | no-more",
                            }
                        ]
                    },
                    "pyez": {
                        "items": [
                            {
                                "name": "bgp_summary",
                                "rpc": "get_bgp_summary_information",
                            }
                        ]
                    },
                    "gnmi": {
                        "items": [
                            {"name": "neighbor_state", "path": "/bgp/neighbor/state"},
                            {"name": "afi_safi_state", "path": "/bgp/afi-safi/state"},
                        ]
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    audit_path.write_text(
        json.dumps(
            {
                "module": "bgp.session_health",
                "uses_evidence": "bgp.evidence.basic",
                "requires": ["neighbor", "state", "families"],
            }
        ),
        encoding="utf-8",
    )

    runtime = load_runtime_settings(
        protocol="bgp",
        connection_path=connection_path,
        audit_path=audit_path,
    )

    bgp_settings = runtime["protocols"]["bgp"]
    assert bgp_settings["module"] == "bgp.session_health"
    assert bgp_settings["uses_evidence"] == "bgp.evidence.basic"
    assert bgp_settings["evidence_module"] == "bgp.evidence.basic"
    assert bgp_settings["evidence_capture_level"] == "basic"
    assert bgp_settings["ssh_command"] == "show bgp summary | display json | no-more"
    assert bgp_settings["pyez_rpc"] == "get_bgp_summary_information"
    assert bgp_settings["gnmic_paths"] == [
        "/bgp/neighbor/state",
        "/bgp/afi-safi/state",
    ]


def test_load_connection_settings_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "connections.json"
    path.write_bytes(b'\xef\xbb\xbf{"ssh":{"port":22}}')
    assert load_connection_settings(path) == {"ssh": {"port": 22}}
