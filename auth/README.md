# Authentication

Copy the example file and edit only the local copy:

```powershell
Copy-Item .\auth\credentials.example.json .\auth\credentials.json
```

`auth/credentials.json` is ignored by Git and must never be committed.

The application uses username/password profiles for the selected operational transport. `radius` describes how the network device validates the supplied identity; the application still connects through SSH, PyEZ/NETCONF, or gNMIc.

GUI-entered Radius credentials are written to the operating-system temporary directory only for the active operation and removed after normal completion.

Connection transport defaults to Compatibility Mode. See [`docs/ADVANCED_SECURITY.md`](../docs/ADVANCED_SECURITY.md) for optional host-key/TLS verification.
