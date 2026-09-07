#!/usr/bin/env python3
"""Audit the repository tree for the v1.0.0 public-release contract."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


IPV4_CANDIDATE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
IPV6_CANDIDATE = re.compile(
    r"(?i)(?<![0-9a-z_:])(?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}(?![0-9a-z_:])"
)
PERSONAL_PATH = re.compile(r"C:\\Users\\|C:/Users/|/home/[^/\s]+/", re.IGNORECASE)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PUBLIC_PLACEHOLDER = re.compile(r"__TEST_COUNT__|<TBD>|\bTBD\b")
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "env",
    ".release",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
}
FORBIDDEN_FILES = {
    "auth/credentials.json",
    "inventory/devices.txt",
}
FORBIDDEN_DIR_PREFIXES = {
    "outputs/raw",
    "outputs/reports",
    "outputs/snapshots",
    "tmp",
}
FORBIDDEN_PUBLIC_DOCS = {
    "docs/ANNOUNCEMENT.md",
    "docs/PUBLICATION_CHECKLIST.md",
    "docs/PUBLIC_RELEASE_AUDIT.md",
    "docs/PUBLIC_RELEASE_ROUTE.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/SANITIZATION_MAP.md",
}
REQUIRED_RELEASE_FILES = {
    "README.md",
    "ROADMAP.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "ACKNOWLEDGMENTS.md",
    "CHANGELOG.md",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "docs/ADVANCED_SECURITY.md",
    "docs/ARCHITECTURE.md",
    "docs/DEVELOPMENT.md",
    "docs/GITHUB_RELEASE_NOTES.md",
    "docs/OPERATOR_GUIDE.md",
    "docs/RESULT_POLICY.md",
    "docs/WINDOWS_INSTALLATION.md",
    "docs/examples/README.md",
    "docs/examples/MW_DEMO_BGP_001_summary.txt",
    "docs/examples/MW_DEMO_BGP_001_detail.txt",
    "docs/examples/MW_DEMO_BGP_001_executive_report.pdf",
    "docs/images/MW_DEMO_BGP_001_gui_main.png",
    "docs/images/MW_DEMO_BGP_001_gui_result.png",
}
PLACEHOLDER_SECRETS = {
    "change_me",
    "example",
    "password",
    "secret",
    "local_password",
    "radius_password",
    "gnmic_password",
    "radius password",
    "admin security password",
}
OBVIOUS_SECRET_TOKEN = re.compile(
    r"(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})"
)
ALLOWED_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "192.0.2.0/24",
        "198.51.100.0/24",
        "203.0.113.0/24",
    )
)
ALLOWED_IPV4_EXACT = {ipaddress.ip_address("127.0.0.1")}
ALLOWED_IPV6_NETWORKS = (ipaddress.ip_network("2001:db8::/32"),)
ALLOWED_IPV6_EXACT = {ipaddress.ip_address("::1")}

@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int | None
    message: str


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def _ipv4_is_public_fixture_safe(address: ipaddress.IPv4Address) -> bool:
    if address in ALLOWED_IPV4_EXACT:
        return True
    return any(address in network for network in ALLOWED_IPV4_NETWORKS)


def _ipv6_is_public_fixture_safe(address: ipaddress.IPv6Address) -> bool:
    if address in ALLOWED_IPV6_EXACT:
        return True
    return any(address in network for network in ALLOWED_IPV6_NETWORKS)


def scan_sensitive_data(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    for relative in sorted(FORBIDDEN_FILES):
        if (root / relative).exists():
            findings.append(
                Finding("forbidden_file", relative, None, "Local secret/inventory file exists.")
            )

    for prefix in sorted(FORBIDDEN_DIR_PREFIXES):
        directory = root / prefix
        if directory.exists() and any(
            item.is_file() and item.name != ".gitkeep"
            for item in directory.rglob("*")
        ):
            findings.append(
                Finding("runtime_output", prefix, None, "Generated runtime evidence is present.")
            )

    for path, text in iter_text_files(root):
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(text.splitlines(), 1):
            for candidate in IPV4_CANDIDATE.findall(line):
                try:
                    address = ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                if isinstance(address, ipaddress.IPv4Address) and not _ipv4_is_public_fixture_safe(address):
                    findings.append(
                        Finding(
                            "non_documentation_ipv4",
                            relative,
                            number,
                            f"IPv4 literal is outside approved documentation space: {address}",
                        )
                    )

            for candidate in IPV6_CANDIDATE.findall(line):
                if candidate == "::":
                    continue
                try:
                    address6 = ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                if isinstance(address6, ipaddress.IPv6Address) and not _ipv6_is_public_fixture_safe(address6):
                    findings.append(
                        Finding(
                            "non_documentation_ipv6",
                            relative,
                            number,
                            f"IPv6 literal is outside approved documentation space: {address6}",
                        )
                    )

            if relative != "tools/public_release_check.py" and PERSONAL_PATH.search(line):
                findings.append(
                    Finding("personal_path", relative, number, "Personal filesystem path found.")
                )
            if PRIVATE_KEY.search(line):
                findings.append(
                    Finding("private_key", relative, number, "Private-key material found.")
                )
            if relative != "tools/public_release_check.py" and PUBLIC_PLACEHOLDER.search(line):
                findings.append(
                    Finding(
                        "publication_placeholder",
                        relative,
                        number,
                        "Unresolved public-release placeholder found.",
                    )
                )

            token_match = OBVIOUS_SECRET_TOKEN.search(line)
            if token_match:
                findings.append(
                    Finding(
                        "credential_token",
                        relative,
                        number,
                        "Credential/token-like value found.",
                    )
                )

            secret_match = re.search(
                r'(?i)["\']?(?:password|secret|token)["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                line,
            )
            if secret_match:
                value = secret_match.group(1).strip()
                if (
                    value.casefold() not in PLACEHOLDER_SECRETS
                    and not value.startswith("${")
                ):
                    findings.append(
                        Finding(
                            "embedded_secret",
                            relative,
                            number,
                            "Non-placeholder secret-like value found.",
                        )
                    )
    return findings


def check_markdown_links(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in root.rglob("*.md"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for target in MARKDOWN_LINK.findall(line):
                target = target.strip()
                if not target or target.startswith(("http://", "https://", "mailto:", "#", "<")):
                    continue
                clean_target = target.split("#", 1)[0]
                if not clean_target:
                    continue
                resolved = (path.parent / clean_target).resolve()
                if not resolved.exists():
                    findings.append(
                        Finding(
                            "broken_markdown_link",
                            path.relative_to(root).as_posix(),
                            number,
                            f"Missing local target: {target}",
                        )
                    )
    return findings


def check_release_structure(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    for relative in sorted(REQUIRED_RELEASE_FILES):
        if not (root / relative).is_file():
            findings.append(
                Finding("missing_release_file", relative, None, "Required release file is missing.")
            )

    for relative in sorted(FORBIDDEN_PUBLIC_DOCS):
        if (root / relative).exists():
            findings.append(
                Finding(
                    "private_release_process_file",
                    relative,
                    None,
                    "Internal publication-process document must not be in the public tree.",
                )
            )

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    if 'name = "bgp-maintenance-window"' not in pyproject:
        findings.append(Finding("package_name", "pyproject.toml", None, "Unexpected package name."))
    if 'version = "1.0.0"' not in pyproject:
        findings.append(Finding("package_version", "pyproject.toml", None, "Version is not 1.0.0."))
    if 'requires-python = ">=3.12,<3.13"' not in pyproject:
        findings.append(
            Finding(
                "python_contract",
                "pyproject.toml",
                None,
                "v1.0.0 must declare the validated Python 3.12 runtime contract.",
            )
        )

    protocol_root = root / "src/maintenance_window/protocols"
    active_protocols = sorted(
        item.name
        for item in protocol_root.iterdir()
        if item.is_dir() and not item.name.startswith("__")
    )
    if active_protocols != ["bgp"]:
        findings.append(
            Finding(
                "active_protocol_scope",
                protocol_root.relative_to(root).as_posix(),
                None,
                f"Expected only BGP, found: {active_protocols}",
            )
        )

    public_docs = [
        root / "README.md",
        root / "ROADMAP.md",
        root / "SECURITY.md",
        root / "docs" / "WINDOWS_INSTALLATION.md",
        root / "docs" / "GITHUB_RELEASE_NOTES.md",
    ]
    for path in public_docs:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        if re.search(r"Windows\s+10|Windows\s+10/11", text, re.IGNORECASE):
            findings.append(
                Finding("windows_contract", relative, None, "v1.0.0 is validated on Windows 11 only.")
            )
        if re.search(r"Python\s+3\.12\s+or\s+newer", text, re.IGNORECASE):
            findings.append(
                Finding("python_claim", relative, None, "Do not claim unvalidated Python versions.")
            )

    ci_path = root / ".github" / "workflows" / "ci.yml"
    if ci_path.exists():
        ci_text = ci_path.read_text(encoding="utf-8")
        for required_ci_text, message in (
            ("runs-on: windows-latest", "CI must validate the Windows 11 release path."),
            ('python-version: "3.12"', "CI must validate Python 3.12."),
            ("python -m pytest -q", "CI must run the full pytest suite."),
            ("tools/public_release_check.py --root .", "CI must run the public-release audit."),
        ):
            if required_ci_text not in ci_text:
                findings.append(
                    Finding("ci_contract", ".github/workflows/ci.yml", None, message)
                )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    findings = [
        *scan_sensitive_data(root),
        *check_markdown_links(root),
        *check_release_structure(root),
    ]
    payload = {
        "root": str(root),
        "result": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
