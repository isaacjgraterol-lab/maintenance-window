from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp import service
from maintenance_window.protocols.bgp.service_layer import explicit_collection
from maintenance_window.protocols.bgp.service_layer import fallback_collection
from maintenance_window.protocols.bgp.service_layer import file_input
from maintenance_window.protocols.bgp.service_layer import live_comparison


def _profile(name: str) -> CredentialProfile:
    return CredentialProfile(
        name=name,
        profile_type="password",
        username="user",
        password="secret",
    )


def test_public_service_is_a_small_facade() -> None:
    path = Path(service.__file__).resolve()

    assert len(path.read_text(encoding="utf-8").splitlines()) < 125
    assert callable(service.parse_input_file)
    assert callable(service.collect_with_source)
    assert callable(service.collect_live)
    assert callable(service.compare_live_sources)


def test_file_input_dispatches_json_parser(tmp_path: Path) -> None:
    path = tmp_path / "bgp.json"
    path.write_text("{}", encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_json_parser(
        path: Path,
        **kwargs: object,
    ) -> list[object]:
        calls["path"] = path
        calls.update(kwargs)
        return [object()]

    sessions = file_input.parse_input_file(
        path=path,
        source="json-file",
        fallback_device="router-a",
        parse_json_fn=fake_json_parser,
    )

    assert len(sessions) == 1
    assert calls == {
        "path": path,
        "fallback_device": "router-a",
    }


def test_file_input_rejects_wrong_extension(tmp_path: Path) -> None:
    path = tmp_path / "bgp.txt"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="json-file requires"):
        file_input.parse_input_file(
            path=path,
            source="json-file",
            fallback_device="router-a",
        )


def test_explicit_ssh_collection_uses_ssh_profile_and_paths() -> None:
    device = Device(host="router-a")
    selected: list[str] = []
    captured: dict[str, object] = {}
    sessions = [object()]

    def fake_select_profile(
        adapter: str,
        defaults: dict[str, str],
        profiles: dict[str, CredentialProfile],
    ) -> CredentialProfile:
        selected.append(adapter)
        return _profile(adapter)

    def fake_collect(**kwargs: object) -> Path:
        captured.update(kwargs)
        return Path("raw.json")

    result = explicit_collection.collect_with_source(
        source="ssh",
        device=device,
        defaults={},
        profiles={},
        settings={"x": 1},
        project_root=Path("project"),
        select_profile_fn=fake_select_profile,
        collect_ssh_fn=fake_collect,
        parse_ssh_fn=lambda path, host: sessions,
    )

    assert result == (sessions, Path("raw.json"), "ssh")
    assert selected == ["ssh"]
    assert captured["output_directory"] == Path("project/outputs/raw/ssh")
    assert captured["device"] is device


def test_explicit_gnmic_selects_only_gnmic_profile() -> None:
    selected: list[str] = []

    def fake_select_profile(
        adapter: str,
        defaults: dict[str, str],
        profiles: dict[str, CredentialProfile],
    ) -> CredentialProfile:
        selected.append(adapter)
        return _profile(adapter)

    explicit_collection.collect_with_source(
        source="gnmic",
        device=Device(host="router-a"),
        defaults={},
        profiles={},
        settings={},
        project_root=Path("project"),
        select_profile_fn=fake_select_profile,
        collect_gnmic_fn=lambda **kwargs: Path("raw.json"),
        parse_gnmic_fn=lambda path, **kwargs: [],
    )

    assert selected == ["gnmic"]


def test_fallback_collection_uses_ssh_after_pyez_failure() -> None:
    calls: list[str] = []

    def fake_collect(source: str, **kwargs: object):
        calls.append(source)
        if source == "pyez":
            raise RuntimeError("netconf unavailable")
        return [], Path("ssh.json"), "ssh"

    result = fallback_collection.collect_live(
        source="pyez",
        device=Device(host="router-a"),
        defaults={},
        profiles={},
        settings={},
        project_root=Path("project"),
        collect_with_source_fn=fake_collect,
    )

    assert calls == ["pyez", "ssh"]
    assert result == ([], Path("ssh.json"), "ssh")



def test_gnmic_explicit_collection_tries_multiple_profiles() -> None:
    selected_profiles = [
        CredentialProfile(
            name="radius-primary",
            profile_type="username_password",
            username="operator-a",
            password="password",
        ),
        CredentialProfile(
            name="radius-secondary",
            profile_type="username_password",
            username="operator-b",
            password="password",
        ),
    ]
    calls: list[str] = []

    def fake_select_profile(*args: object, **kwargs: object):
        del args, kwargs
        return selected_profiles

    def fake_collect_gnmic(**kwargs: object) -> Path:
        profile = kwargs["profile"]
        assert isinstance(profile, CredentialProfile)
        calls.append(profile.name)
        if profile.name == "radius-primary":
            raise RuntimeError("primary credentials rejected")
        return Path("gnmic-secondary.json")

    result = explicit_collection.collect_with_source(
        source="gnmic",
        device=Device(host="router-a"),
        defaults={},
        profiles={},
        settings={},
        project_root=Path("project"),
        select_profile_fn=fake_select_profile,
        collect_gnmic_fn=fake_collect_gnmic,
        parse_gnmic_fn=lambda path, fallback_device: [fallback_device],
    )

    assert calls == ["radius-primary", "radius-secondary"]
    assert result == (["router-a"], Path("gnmic-secondary.json"), "gnmic")


def test_fallback_collection_uses_ssh_after_gnmic_failure() -> None:
    calls: list[str] = []

    def fake_collect(source: str, **kwargs: object):
        del kwargs
        calls.append(source)
        if source == "gnmic":
            raise RuntimeError("gnmi unavailable")
        return [], Path("ssh.json"), "ssh"

    result = fallback_collection.collect_live(
        source="gnmic",
        device=Device(host="router-a"),
        defaults={},
        profiles={},
        settings={},
        project_root=Path("project"),
        collect_with_source_fn=fake_collect,
    )

    assert calls == ["gnmic", "ssh"]
    assert result == ([], Path("ssh.json"), "ssh")

def test_auto_collection_reports_all_failures() -> None:
    calls: list[str] = []

    def always_fail(source: str, **kwargs: object):
        calls.append(source)
        raise RuntimeError(source)

    with pytest.raises(RuntimeError, match="All BGP collectors failed"):
        fallback_collection.collect_live(
            source="auto",
            device=Device(host="router-a"),
            defaults={},
            profiles={},
            settings={},
            project_root=Path("project"),
            collect_with_source_fn=always_fail,
        )

    assert calls == ["pyez", "gnmic", "ssh"]


def test_live_comparison_rejects_duplicate_sources() -> None:
    with pytest.raises(ValueError, match="two different sources"):
        live_comparison.validate_comparison_sources("ssh", "ssh")


def test_live_comparison_returns_metadata() -> None:
    calls: list[str] = []
    expected = object()

    def fake_collect(source: str, **kwargs: object):
        calls.append(source)
        return [source], Path(f"{source}.raw"), source

    def fake_compare(**kwargs: object):
        assert kwargs["left_sessions"] == ["pyez"]
        assert kwargs["right_sessions"] == ["ssh"]
        return expected

    comparison, raw_files, actual_sources = (
        live_comparison.compare_live_sources(
            left_source="pyez",
            right_source="ssh",
            device=Device(host="router-a"),
            defaults={},
            profiles={},
            settings={},
            project_root=Path("project"),
            collect_with_source_fn=fake_collect,
            compare_bgp_sources_fn=fake_compare,
        )
    )

    assert comparison is expected
    assert calls == ["pyez", "ssh"]
    assert raw_files == {
        "pyez": Path("pyez.raw"),
        "ssh": Path("ssh.raw"),
    }
    assert actual_sources == {"pyez": "pyez", "ssh": "ssh"}


def test_service_facade_preserves_monkeypatch_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    expected = object()

    def fake_collect(source: str, **kwargs: object):
        calls.append(source)
        return [source], Path(f"{source}.raw"), source

    monkeypatch.setattr(service, "collect_with_source", fake_collect)
    monkeypatch.setattr(
        service,
        "compare_bgp_sources",
        lambda **kwargs: expected,
    )

    result, _, _ = service.compare_live_sources(
        left_source="pyez",
        right_source="ssh",
        device=Device(host="router-a"),
        defaults={},
        profiles={},
        settings={},
        project_root=Path("project"),
    )

    assert result is expected
    assert calls == ["pyez", "ssh"]
