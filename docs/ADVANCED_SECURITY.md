# Advanced Security

v1.0.0 starts in **Compatibility Mode** because many operational management networks do not yet use SSH/NETCONF host-key verification or gNMI TLS. Compatibility Mode is the default and is intended only for management networks you trust.

This guide explains the optional **Advanced Secure Mode** settings. Enabling them can require known-host management and/or a working TLS PKI on the network devices.

## Security boundary

Read-only collection and transport security are separate concerns.

The application does not configure routers, but credentials and operational evidence still travel over the selected management transport. Advanced Secure Mode strengthens server identity and transport verification; it does not change the read-only application boundary.

## Configuration file

Connection settings are stored in:

```text
config/connections/settings.json
```

The public file contains no credentials.

## Default Compatibility Mode

The shipped defaults are intentionally:

```json
{
  "pyez": {
    "verify_host_key": false
  },
  "ssh": {
    "verify_host_key": false,
    "known_hosts_file": ""
  },
  "gnmic": {
    "insecure": true,
    "skip_verify": false,
    "tls_ca": "",
    "tls_cert": "",
    "tls_key": "",
    "tls_server_name": ""
  }
}
```

With these defaults:

- SSH CLI JSON can accept an unknown SSH host key.
- PyEZ/NETCONF does not enforce SSH host-key verification.
- gNMIc uses non-TLS `--insecure` transport.

Do not treat Compatibility Mode as a secure Internet-facing configuration.

## SSH CLI JSON - known-host verification

Set:

```json
"ssh": {
  "port": 22,
  "timeout_seconds": 30,
  "verify_host_key": true,
  "known_hosts_file": ""
}
```

When `verify_host_key` is `true`, the collector loads the operating-system/user SSH known-host database and rejects an unknown host key.

To use an additional known-host file, provide its local path:

```json
"known_hosts_file": "C:\\path\\to\\known_hosts"
```

Before enabling this mode for production use, make sure the expected device host keys are already trusted on the workstation.

## PyEZ / NETCONF - host-key verification

Set:

```json
"pyez": {
  "port": 830,
  "timeout_seconds": 60,
  "verify_host_key": true
}
```

The value is passed to the Junos PyEZ `hostkey_verify` option. Confirm that the NETCONF/SSH host key is trusted before enabling it across an inventory.

## gNMI / OpenConfig - TLS

On Windows 11, v1.0.0 runs gNMIc **inside WSL**. TLS certificate/key paths in `settings.json` are therefore passed directly to the Linux gNMIc process and must be valid WSL/Linux paths, not normal `C:\\...` Windows paths.

For example, if the files are stored in `C:\\NetworkKeys` on Windows, WSL normally sees that directory as `/mnt/c/NetworkKeys`.

To stop using non-TLS gNMI transport, set:

```json
"gnmic": {
  "insecure": false,
  "skip_verify": false,
  "tls_ca": "/mnt/c/NetworkKeys/ca.pem",
  "tls_cert": "",
  "tls_key": "",
  "tls_server_name": "router.example.net"
}
```

The adapter passes these values to gNMIc without path conversion. Validate the paths from WSL before enabling the secure profile.

### Server certificate validation

Recommended settings:

```text
insecure: false
skip_verify: false
tls_ca: trusted CA certificate
tls_server_name: expected certificate/server name when required
```

### Mutual TLS

When the gNMI server requires a client certificate, also configure:

```json
"tls_cert": "/mnt/c/NetworkKeys/client.pem",
"tls_key": "/mnt/c/NetworkKeys/client.key"
```

Protect private-key material using normal workstation/PKI controls. The repository ignores common private-key file extensions, but do not store operational certificates or keys inside the project unless your local security policy explicitly permits it.

### `skip_verify`

`skip_verify=true` uses TLS encryption while disabling server-certificate verification. It can be useful while troubleshooting a lab PKI, but it is not equivalent to verified TLS.

### Validate TLS paths from WSL

Before running Maintenance Window with TLS enabled, verify that WSL/gNMIc can see the configured files:

```powershell
wsl test -r /mnt/c/NetworkKeys/ca.pem
```

For mTLS, validate the client certificate and key as well:

```powershell
wsl test -r /mnt/c/NetworkKeys/client.pem
wsl test -r /mnt/c/NetworkKeys/client.key
```

A successful `test -r` command returns no text and exit code `0`. If these checks fail, fix the WSL path before troubleshooting gNMI itself.

## Credentials and local process visibility

The current gNMIc adapter invokes the local gNMIc process with username/password command arguments. On multi-user systems where process command lines can be inspected, treat this as a local exposure consideration.

GUI-entered Radius credentials are written to an operating-system temporary directory only for the active operation and are deleted after normal completion. Abnormal process termination can leave temporary files behind, so workstation access controls still matter.

## Recommended migration sequence

For an existing management network, migrate deliberately rather than enabling every control across all devices at once:

1. Validate SSH/NETCONF known-host behavior on one lab device.
2. Enable host-key verification for that device/workstation.
3. Validate gNMI TLS and CA/server-name handling on one device.
4. Add mTLS only when the platform requires it.
5. Run BEFORE/AFTER collection against a lab MW ID.
6. Confirm `source_actual`, coverage, and report output.
7. Expand to the production inventory in controlled batches.

## Troubleshooting principle

When Advanced Secure Mode fails, first test the underlying management transport independently of Maintenance Window Automation. Certificate/known-host problems must be fixed at the SSH/NETCONF/gNMI layer rather than bypassed silently inside the application.
