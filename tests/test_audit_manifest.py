from __future__ import annotations

from maintenance_window.core.audit_manifest import (
    get_gnmi_paths,
    get_pyez_rpc_name,
    get_ssh_command,
    combine_audit_with_evidence,
    normalize_audit_settings,
)


def _settings_from_audit(audit: dict[str, object]) -> dict[str, object]:
    return {"protocols": {"bgp": normalize_audit_settings(audit)}}


def test_manifest_resolves_source_declarations() -> None:
    audit = {
        "module": "bgp.session_health",
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
                    {
                        "name": "bgp_neighbor_session_state",
                        "path": "/network-instances/default/bgp/session-state",
                    }
                ]
            },
        },
    }

    settings = _settings_from_audit(audit)

    assert get_ssh_command(settings) == "show bgp summary | display json | no-more"
    assert get_pyez_rpc_name(settings) == "get_bgp_summary_information"
    assert get_gnmi_paths(settings) == [
        "/network-instances/default/bgp/session-state"
    ]


def test_legacy_audit_settings_still_work() -> None:
    settings = {
        "protocols": {
            "bgp": {
                "ssh_command": "show bgp summary",
                "pyez_rpc": "get_bgp_summary_information",
                "gnmic_paths": ["/bgp/state"],
            }
        }
    }

    assert get_ssh_command(settings) == "show bgp summary"
    assert get_pyez_rpc_name(settings) == "get_bgp_summary_information"
    assert get_gnmi_paths(settings) == ["/bgp/state"]


def test_consumer_manifest_can_reuse_evidence_sources() -> None:
    evidence = {
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
    consumer = {
        "module": "bgp.session_health",
        "uses_evidence": "bgp.evidence.basic",
        "requires": ["neighbor", "state", "families"],
    }

    settings = _settings_from_audit(
        combine_audit_with_evidence(consumer, evidence)
    )

    assert settings["protocols"]["bgp"]["module"] == "bgp.session_health"
    assert settings["protocols"]["bgp"]["evidence_module"] == "bgp.evidence.basic"
    assert get_ssh_command(settings) == "show bgp summary | display json | no-more"
    assert get_pyez_rpc_name(settings) == "get_bgp_summary_information"
    assert get_gnmi_paths(settings) == [
        "/bgp/neighbor/state",
        "/bgp/afi-safi/state",
    ]
