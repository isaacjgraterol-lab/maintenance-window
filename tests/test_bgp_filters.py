from maintenance_window.protocols.bgp.state.filters import filter_sessions, group_sessions
from maintenance_window.protocols.bgp.state.models import BgpSession


def sample_sessions() -> list[BgpSession]:
    return [
        BgpSession("PE01", "192.0.2.1", "Established"),
        BgpSession("PE01", "192.0.2.2", "Idle"),
        BgpSession("PE02", "192.0.2.3", "Active"),
    ]


def test_filter_healthy() -> None:
    result = filter_sessions(sample_sessions(), "healthy")
    assert [item.neighbor for item in result] == ["192.0.2.1"]


def test_filter_unhealthy() -> None:
    result = filter_sessions(sample_sessions(), "unhealthy")
    assert [item.neighbor for item in result] == ["192.0.2.2", "192.0.2.3"]


def test_group_sessions() -> None:
    result = group_sessions(sample_sessions())
    assert len(result["PE01"]) == 2
    assert result["PE02"][0]["state"] == "Active"
