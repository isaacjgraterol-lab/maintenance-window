from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from maintenance_window.protocols.bgp.state.models import BgpSession
from maintenance_window.protocols.bgp.parsers.json_auto import (
    parse_json_bgp_file,
)
from maintenance_window.protocols.bgp.parsers.pyez_xml import parse_pyez_xml


FileParser = Callable[..., list[BgpSession]]


def parse_input_file(
    path: Path,
    source: str,
    fallback_device: str,
    *,
    parse_json_fn: FileParser = parse_json_bgp_file,
    parse_xml_fn: FileParser = parse_pyez_xml,
) -> list[BgpSession]:
    """Parse BGP sessions from a supported local JSON or XML file."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()

    if source == "json-file":
        if suffix not in {".json", ".jsonl"}:
            raise ValueError(
                "json-file requires a .json or .jsonl input file."
            )
        return parse_json_fn(
            path,
            fallback_device=fallback_device,
        )

    if source == "xml-file":
        if suffix != ".xml":
            raise ValueError("xml-file requires a .xml input file.")
        return parse_xml_fn(
            path,
            device_name=fallback_device,
        )

    raise ValueError(f"Unsupported BGP file source: {source}")
