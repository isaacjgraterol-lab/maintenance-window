from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

from maintenance_window.core.models import CredentialProfile, Device
from maintenance_window.protocols.bgp.collectors import gnmic, pyez, ssh


def _profile() -> CredentialProfile:
    return CredentialProfile(
        name="demo",
        profile_type="username_password",
        username="operator",
        password="password",
    )


def test_credential_profile_repr_redacts_password() -> None:
    rendered = repr(_profile())
    assert "operator" in rendered
    assert "password='password'" not in rendered
    assert "password=" not in rendered


def test_ssh_compatibility_mode_accepts_unknown_host_keys() -> None:
    calls: list[object] = []

    class Client:
        def set_missing_host_key_policy(self, policy: object) -> None:
            calls.append(policy)

    class Auto: pass
    class Reject: pass
    fake = SimpleNamespace(AutoAddPolicy=Auto, RejectPolicy=Reject)

    ssh._configure_host_key_policy(Client(), {"verify_host_key": False}, fake)
    assert isinstance(calls[-1], Auto)


def test_ssh_advanced_secure_mode_loads_known_hosts_and_rejects_unknown(tmp_path: Path) -> None:
    events: list[object] = []

    class Client:
        def load_system_host_keys(self) -> None:
            events.append("system")
        def load_host_keys(self, path: str) -> None:
            events.append(("file", path))
        def set_missing_host_key_policy(self, policy: object) -> None:
            events.append(policy)

    class Auto: pass
    class Reject: pass
    fake = SimpleNamespace(AutoAddPolicy=Auto, RejectPolicy=Reject)
    known_hosts = tmp_path / "known_hosts"

    ssh._configure_host_key_policy(
        Client(),
        {"verify_host_key": True, "known_hosts_file": str(known_hosts)},
        fake,
    )

    assert events[0] == "system"
    assert events[1] == ("file", str(known_hosts))
    assert isinstance(events[2], Reject)


def test_pyez_passes_configured_hostkey_verify(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    class Rpc:
        def get_bgp_summary_information(self, **kwargs):
            del kwargs
            class Reply:
                pass
            return Reply()

    class FakeDevice:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.rpc = Rpc()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    fake_junos = types.ModuleType("jnpr.junos")
    fake_junos.Device = FakeDevice
    monkeypatch.setitem(sys.modules, "jnpr", types.ModuleType("jnpr"))
    monkeypatch.setitem(sys.modules, "jnpr.junos", fake_junos)

    fake_lxml = types.ModuleType("lxml")
    fake_lxml.etree = SimpleNamespace(tostring=lambda *args, **kwargs: "<bgp-information/>")
    monkeypatch.setitem(sys.modules, "lxml", fake_lxml)

    settings = {
        "pyez": {"verify_host_key": True},
        "protocols": {"bgp": {"pyez_rpc": "get_bgp_summary_information"}},
    }
    pyez.collect_pyez(Device("192.0.2.10"), _profile(), settings, tmp_path)
    assert seen["hostkey_verify"] is True


def test_gnmic_compatibility_mode_adds_insecure(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []

    def fake_run(command, **kwargs):
        del kwargs
        seen.extend(command)
        return SimpleNamespace(returncode=0, stdout="{}\n", stderr="")

    monkeypatch.setattr(gnmic.subprocess, "run", fake_run)
    settings = {
        "gnmic": {"insecure": True, "command_prefix": ["gnmic"]},
        "protocols": {"bgp": {"gnmi_paths": ["/demo"]}},
    }
    gnmic.collect_gnmic(Device("192.0.2.10"), _profile(), settings, tmp_path)
    assert "--insecure" in seen
    assert "--tls-ca" not in seen


def test_gnmic_advanced_secure_mode_adds_tls_options(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []

    def fake_run(command, **kwargs):
        del kwargs
        seen.extend(command)
        return SimpleNamespace(returncode=0, stdout="{}\n", stderr="")

    monkeypatch.setattr(gnmic.subprocess, "run", fake_run)
    settings = {
        "gnmic": {
            "insecure": False,
            "skip_verify": False,
            "tls_ca": "ca.pem",
            "tls_cert": "client.pem",
            "tls_key": "client.key",
            "tls_server_name": "router.example",
            "command_prefix": ["gnmic"],
        },
        "protocols": {"bgp": {"gnmi_paths": ["/demo"]}},
    }
    gnmic.collect_gnmic(Device("192.0.2.10"), _profile(), settings, tmp_path)

    assert "--insecure" not in seen
    assert seen[seen.index("--tls-ca") + 1] == "ca.pem"
    assert seen[seen.index("--tls-cert") + 1] == "client.pem"
    assert seen[seen.index("--tls-key") + 1] == "client.key"
    assert seen[seen.index("--tls-server-name") + 1] == "router.example"
