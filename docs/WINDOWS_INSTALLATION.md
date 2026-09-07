# Windows 11 Installation Guide

This is the official v1.0.0 installation path.

Validated environment:

```text
Operating system: Windows 11
Python:           3.12
Installation:     Git clone + editable install
```

The application is read-only with respect to network-device configuration. Connection transport defaults to **Compatibility Mode**; see [Advanced Security](ADVANCED_SECURITY.md) when your environment uses known-host verification and/or gNMI TLS.

## What you need

- Windows 11.
- Internet access for the initial Git/Python/package installation.
- Git for Windows.
- Python 3.12.
- Reachability to the Juniper Junos devices you will collect from.
- A device account permitted to run the required operational commands/RPCs.
- WSL only when using the gNMI/OpenConfig source.

You do not need a GitHub account to clone a public repository.

## Fast path

If Git and Python 3.12 are already installed:

```powershell
git --version
py -3.12 --version

New-Item -ItemType Directory -Force -Path "$HOME\Documents\NetworkTools" | Out-Null
Set-Location "$HOME\Documents\NetworkTools"

git clone https://github.com/isaacjgraterol-lab/maintenance-window.git
Set-Location .\maintenance-window

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .

Copy-Item .\auth\credentials.example.json .\auth\credentials.json
Copy-Item .\inventory\devices.example.txt .\inventory\devices.txt

.\.venv\Scripts\python.exe .\gui.py 8765
```

Open:

```text
http://127.0.0.1:8765
```

For a first installation, follow the complete steps below.

---

## Step 1 - Install Git for Windows

### 1A. Check Git

Open PowerShell:

```powershell
git --version
```

A working installation returns a version similar to:

```text
git version 2.x.x.windows.x
```

### 1B. Recommended installation with winget

Check winget:

```powershell
winget --version
```

Install Git:

```powershell
winget install --id Git.Git -e --source winget
```

Close all PowerShell windows, open a new one, and verify:

```powershell
git --version
```

### 1C. Graphical installer alternative

If winget is unavailable, use the official Git for Windows installer:

```text
https://git-scm.com/install/windows
```

For a normal Intel/AMD Windows workstation, install the current x64 build. The default installer choices are appropriate for most users; keep Git available from the command line/PowerShell.

Close/reopen PowerShell and verify `git --version` before continuing.

> GitHub Desktop is not required.

## Step 2 - Install Python 3.12

### 2A. Check Python 3.12

```powershell
py -3.12 --version
```

Expected form:

```text
Python 3.12.x
```

### 2B. Recommended installation with winget

```powershell
winget install --id Python.Python.3.12 -e --source winget
```

Close every PowerShell window, open a new one, and verify:

```powershell
py -3.12 --version
```

### 2C. Official graphical installer alternative

Use the official Python Windows downloads page:

```text
https://www.python.org/downloads/windows/
```

Install Python 3.12 and include the Python launcher when offered. Reopen PowerShell and confirm that `py -3.12 --version` works.

Do not continue until Python 3.12 is available through that command.

## Step 3 - Clone the repository

Create a neutral tools folder under your own Windows home directory:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\Documents\NetworkTools" | Out-Null
Set-Location "$HOME\Documents\NetworkTools"
```

Clone:

```powershell
git clone https://github.com/isaacjgraterol-lab/maintenance-window.git
Set-Location .\maintenance-window
```

Verify the remote:

```powershell
git remote -v
```

Verify key project files:

```powershell
Get-ChildItem README.md, pyproject.toml, gui.py, main.py
```

## Step 4 - Create the Python environment

You do not need to activate the virtual environment. The guide calls its Python explicitly.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Verify the application package:

```powershell
.\.venv\Scripts\python.exe -c "import maintenance_window; print('Maintenance Window import: OK')"
```

## Step 5 - Create local credentials

Copy the example:

```powershell
Copy-Item .\auth\credentials.example.json .\auth\credentials.json
notepad .\auth\credentials.json
```

Replace only the local-copy example values. Keep valid JSON syntax.

Rules:

- never put real passwords into `credentials.example.json`;
- never commit `auth\credentials.json`;
- use an operational/read-only account where practical;
- local credentials are separate from the repository.

## Step 6 - Create the device inventory

```powershell
Copy-Item .\inventory\devices.example.txt .\inventory\devices.txt
notepad .\inventory\devices.txt
```

Use one management address per line, for example:

```text
192.0.2.10
192.0.2.11
```

The example addresses above are documentation-only; use your real management addresses only in the ignored local inventory file.

## Step 7 - Understand the v1.0.0 sources

### PyEZ / NETCONF - Juniper Junos only

Requirements:

```text
TCP/830 reachable
NETCONF enabled
valid operational credentials
```

No WSL is required.

### SSH CLI JSON - Juniper Junos only

Requirements:

```text
TCP/22 reachable
account can run the operational BGP show command
```

No WSL is required.

### gNMI / OpenConfig - Juniper Junos validated

The Windows 11 v1.0.0 workflow uses gNMIc through WSL.

Cisco IOS XR and Nokia SR OS are future capability-driven gNMI/OpenConfig research targets, not current supported choices.

### Manual JSON/XML

Uses offline evidence available on the workstation and does not connect to a device.

## Step 8 - Compatibility Mode versus Advanced Secure Mode

The supplied `config\connections\settings.json` starts in **Compatibility Mode**:

```text
SSH host-key verification:     off
NETCONF host-key verification: off
gNMI TLS:                      off (`--insecure`)
```

This is deliberate so the first connection works in trusted operational management networks that do not yet have known-host/PKI processes.

For environments that require identity verification/TLS, follow:

[Advanced Security](ADVANCED_SECURITY.md)

Do not enable secure options across a large inventory until the underlying SSH/NETCONF/gNMI security configuration has been validated on a lab/test device.

## Step 9 - Install WSL and gNMIc when required

Skip this step when you use PyEZ, SSH, or Manual only.

### Install WSL

Open PowerShell as Administrator:

```powershell
wsl --install
```

Restart Windows if requested. Open the installed Linux distribution once and finish its initial username/password setup.

Verify from PowerShell:

```powershell
wsl -l -v
```

### Install gNMIc inside WSL

Open the WSL Linux shell and use the installation instructions from the gNMIc project. A commonly documented installer command is:

```bash
bash -c "$(curl -sL https://get-gnmic.openconfig.net)"
```

Verify inside WSL:

```bash
gnmic version
```

Then verify from Windows PowerShell:

```powershell
wsl gnmic version
```

The default project command prefix is:

```json
["wsl", "gnmic"]
```

## Step 10 - Start the local GUI

From the repository directory:

```powershell
.\.venv\Scripts\python.exe .\gui.py 8765
```

Open:

```text
http://127.0.0.1:8765
```

Keep that PowerShell process running while the GUI is in use.

If port 8765 is occupied:

```powershell
.\.venv\Scripts\python.exe .\gui.py 8766
```

then open `http://127.0.0.1:8766`.

The GUI is designed for loopback/local use. Do not expose it directly to an untrusted network.

## Step 11 - Run the first maintenance-window workflow

```text
1. Select the source.
2. Select one device or Database Inventory.
3. Enter a unique MW ID.
4. Capture Before.
5. Perform the maintenance.
6. Capture After with the same MW ID.
7. Compare Existing MW.
8. Review State, Session Health, coverage, source, and findings.
9. Export Summary / Detail / JSON / Executive PDF as needed.
```

Use the same actual source for the official comparison:

```text
PyEZ -> PyEZ
SSH  -> SSH
gNMI -> gNMI
```

## Step 12 - Find reports

Full comparisons are normally stored under:

```text
outputs\snapshots\bgp\<MW_ID>\comparison_reports\<timestamp>\
```

Generated evidence can contain sensitive operational information. Review it before sharing.

## Updating later

From the repository directory:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e .
```

Review release notes when moving between versions.

## Common problems

### `git` is not recognized

Install Git, close/reopen PowerShell, and rerun:

```powershell
git --version
```

### `py` or Python 3.12 is not recognized

Install Python 3.12, close/reopen PowerShell, and rerun:

```powershell
py -3.12 --version
```

### `ModuleNotFoundError`

From the repository directory:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

### PyEZ / NETCONF cannot connect

```powershell
Test-NetConnection <DEVICE_IP> -Port 830
```

Then verify NETCONF, credentials, and (when Advanced Secure Mode is enabled) host-key trust.

### SSH cannot connect

```powershell
Test-NetConnection <DEVICE_IP> -Port 22
```

Then verify credentials and host-key policy.

### gNMIc does not run

```powershell
wsl gnmic version
```

Fix the WSL/gNMIc installation before troubleshooting the application.

### Advanced Secure Mode fails

Test the SSH/NETCONF/gNMI trust/TLS configuration independently first. See [Advanced Security](ADVANCED_SECURITY.md).

## Security reminders

- Keep real credentials/inventory local.
- Use Compatibility Mode only on a trusted management network.
- Do not expose the local GUI to an untrusted network.
- RAW evidence and reports can contain addresses, ASNs, service/table names, and platform details.
- Review evidence before sharing it publicly.
