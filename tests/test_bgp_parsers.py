from pathlib import Path

from maintenance_window.protocols.bgp.parsers.gnmic_json import parse_gnmic_json
from maintenance_window.protocols.bgp.parsers.json_auto import parse_json_bgp_file
from maintenance_window.protocols.bgp.parsers.pyez_xml import parse_pyez_xml
from maintenance_window.protocols.bgp.parsers.ssh_json import parse_ssh_json


ROOT = Path(__file__).resolve().parents[1]


def test_parse_normalized_json() -> None:
    sessions = parse_json_bgp_file(ROOT / "sample_data/bgp_sessions_normalized.json")
    assert len(sessions) == 4
    assert sessions[0].device == "PE01"


def test_parse_gnmic_protojson() -> None:
    sessions = parse_gnmic_json(
        ROOT / "sample_data/bgp_sessions_gnmic_protojson.json"
    )
    assert len(sessions) == 2
    assert sessions[0].state == "Established"


def test_parse_pyez_xml() -> None:
    sessions = parse_pyez_xml(
        ROOT / "sample_data/bgp_sessions_pyez.xml", device_name="PE01"
    )
    assert len(sessions) == 2
    assert sessions[0].state == "Established"


def test_parse_ssh_json() -> None:
    sessions = parse_ssh_json(
        ROOT / "sample_data/bgp_sessions_ssh.json",
        device_name="192.0.2.254",
    )
    assert len(sessions) == 2
    assert sessions[1].state == "Idle"


def test_json_loader_accepts_utf8_bom(tmp_path: Path) -> None:
    from maintenance_window.core.files import load_json_documents

    path = tmp_path / "bom.json"
    path.write_bytes(b'\xef\xbb\xbf{"device":"192.0.2.10"}')
    assert load_json_documents(path) == [{"device": "192.0.2.10"}]
