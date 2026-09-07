from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def build_raw_output_path(
    output_directory: Path,
    device_name: str,
    suffix: str,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_device = device_name.replace(":", "_").replace("/", "_")
    return output_directory / f"{safe_device}_{timestamp}.{suffix}"


def export_json_report(payload: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
