# Operator Guide

For first installation, start with the [Windows 11 Installation Guide](WINDOWS_INSTALLATION.md).

## 1. Local credentials and inventory

Create local copies:

```powershell
Copy-Item .\auth\credentials.example.json .\auth\credentials.json
Copy-Item .\inventory\devices.example.txt .\inventory\devices.txt
```

Edit only the local copies. They are ignored by Git.

## 2. Collection sources

### PyEZ / NETCONF - Juniper Junos

Best when Junos RPC detail and family/table counters are required. Native Windows 11 workflow.

### SSH CLI JSON - Juniper Junos

Collects Junos operational CLI JSON. Native Windows 11 workflow.

### gNMI / OpenConfig - Juniper Junos validated

Uses gNMI/OpenConfig through gNMIc in WSL. Implemented OpenConfig leaves vary by platform/software, so Session Health coverage may be `PARTIAL` or `NOT_EVALUATED` for some checks.

Cisco IOS XR and Nokia SR OS are future capability-driven research targets and are not selectable/supported platforms in v1.0.0.

### Manual JSON/XML

Offline input for previously collected evidence.

## 3. Security mode

The shipped connection settings use **Compatibility Mode (default)** to maximize reachability on trusted management networks.

Compatibility Mode does not enforce SSH/NETCONF host-key verification and can use gNMI without TLS. Operators with known-host management or a TLS PKI can enable [Advanced Secure Mode](ADVANCED_SECURITY.md).

## 4. Use a unique MW ID

Use a stable identifier for one maintenance activity, for example:

```text
MW_CORE_UPGRADE_001
```

The same MW ID is used for BEFORE and AFTER. MW IDs are validated as Windows-safe path components.

## 5. Capture BEFORE

Example using SSH and an inventory:

```powershell
.\.venv\Scripts\python.exe .\main.py `
  --protocol bgp `
  --source ssh `
  --auth-backend local `
  --snapshot before `
  --mw-id MW_CORE_UPGRADE_001 `
  --device all `
  --inventory .\inventory\devices.txt `
  --workers 10 `
  --output summary
```

## 6. Perform the maintenance and capture AFTER

Repeat the capture with the same MW ID and the same intended collection source:

```text
--snapshot after
```

## 7. Compare the current snapshots

```powershell
.\.venv\Scripts\python.exe .\main.py `
  --protocol bgp `
  --module full `
  --compare-snapshots before,after `
  --mw-id MW_CORE_UPGRADE_001 `
  --device all `
  --inventory .\inventory\devices.txt `
  --output summary
```

The official comparison requires the same actual source on both sides for each device.

## 8. Interpret results

Operational result:

```text
PASS
PASS_WITH_UNHEALTHY_SESSIONS
WARNING
FAIL
ERROR
```

Coverage:

```text
FULL
PARTIAL
NOT_EVALUATED
```

A `PASS` can still have `PARTIAL` coverage when the source did not expose every Session Health signal.

Important `WARNING` examples include:

- inferred session restart;
- flap-count increase;
- flap-counter reset;
- new family/table after maintenance;
- **missing family/table after maintenance**;
- meaningful prefix loss.

A `missing_family_after` finding deserves operator attention because the missing table/AFI-SAFI can imply loss of all routes carried by that family.

Pre-existing unhealthy peers are retained as `persistent_unhealthy_peer` context rather than being misclassified as a new maintenance failure.

## 9. Source fallback

Snapshots and reports preserve:

```text
source_requested
source_actual
```

A fallback is visible to the operator. The tool does not silently treat unlike sources as equivalent for the official BEFORE/AFTER result.

## 10. Local GUI

Start it with:

```powershell
.\.venv\Scripts\python.exe .\gui.py 8765
```

Open:

```text
http://127.0.0.1:8765
```

Workflow:

1. Select the source/authentication backend.
2. Select one device or an inventory.
3. Enter a unique MW ID.
4. Capture Before.
5. Perform maintenance.
6. Capture After.
7. Compare Existing MW.
8. Review global result, coverage, source fallback, device rows, and finding inventory.
9. Download Summary TXT, Detail TXT, JSON, or Executive PDF.

The GUI is local-only and its download resolver accepts only generated report locations.

## 11. Reports

### Summary TXT

Structured operational overview including the global key-finding inventory and per-device counts.

### Detail TXT

Peer/family evidence with before/after values and finding messages.

### JSON

Machine-readable audit evidence and canonical finding counts.

### Executive PDF

Three-page compact operator/management view.

## 12. Before sharing evidence

Review reports and RAW files for management/peer addresses, ASNs, VRF/table names, customer/service identifiers, software/platform information, and local paths. Generated evidence is not automatically safe to publish.
