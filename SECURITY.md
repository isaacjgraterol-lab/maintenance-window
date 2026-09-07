# Security Policy

## Supported version

Security fixes are accepted for the latest public release.

## Reporting

Use a private GitHub security advisory when possible. Do not post credentials, private inventory, RAW evidence, or sensitive topology information in a public issue.

## Read-only device boundary

The project performs operational collection and does not intentionally implement router configuration or remediation actions such as:

```text
commit
load
lock
unlock
rollback
edit-config
```

Read-only behavior does **not** mean that the management transport is automatically hardened.

## Connection security profiles

### Compatibility Mode (default)

v1.0.0 defaults to Compatibility Mode to work in trusted management networks where host-key verification or gNMI TLS may not yet be deployed.

Default connection posture:

- SSH CLI JSON: unknown SSH host keys can be accepted.
- PyEZ / NETCONF: host-key verification is disabled.
- gNMIc: non-TLS `--insecure` mode is enabled.

This mode favors operational compatibility. Use it only on a management network you trust.

### Advanced Secure Mode

Operators with known-host management and/or a TLS PKI can enable stronger verification in `config/connections/settings.json`.

See [Advanced Security](docs/ADVANCED_SECURITY.md) for the supported settings and validation steps.

## Local GUI

The GUI is intended to bind to `127.0.0.1` and should not be exposed directly to the Internet or an untrusted network.

Report downloads are constrained to generated GUI reports and BGP comparison-report directories; arbitrary project files are not valid download targets.

## Credentials

The following local files are ignored by Git:

```text
auth/credentials.json
inventory/devices.txt
.env
config/**/*.local.json
```

GUI-entered Radius credentials are written only to a temporary OS directory for the duration of the operation and are removed after normal completion. An abnormal process termination can leave temporary operating-system files behind, so local workstation access still matters.

The current gNMIc adapter passes username/password as command arguments to the local gNMIc process. On systems where local users can inspect process command lines, treat that as a local credential-exposure consideration.

## Evidence sensitivity

RAW evidence, snapshots, the local manual database, and reports can contain:

- management and peer addresses;
- ASNs;
- customer or VRF names;
- routing-table names;
- platform/version data;
- source-native protocol evidence.

Review and sanitize evidence before sharing it.

## Public repository data policy

Public fixtures and examples must use reserved documentation address space only. The publication scanner rejects non-documentation IP literals, personal filesystem paths, forbidden credentials/inventory files, generated runtime evidence, and private release-process documents.
