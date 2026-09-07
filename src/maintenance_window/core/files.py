from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def load_json_documents(path: Path) -> list[Any]:
    """
    Load JSON documents from a file.

    Supported formats:
    - One JSON object
    - One JSON array
    - NDJSON / JSON lines
    - Multiple concatenated pretty-printed JSON objects
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    text = path.read_text(encoding="utf-8-sig").strip()

    if not text:
        raise ValueError(f"The JSON file is empty: {path}")

    # Case 1: standard single JSON document.
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        pass

    # Case 2: multiple JSON documents in the same file.
    decoder = json.JSONDecoder()
    documents: list[Any] = []
    index = 0

    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1

        if index >= len(text):
            break

        try:
            document, next_index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON document in {path}: {exc}"
            ) from exc

        documents.append(document)
        index = next_index

    if not documents:
        raise ValueError(f"No JSON documents found in {path}")

    return documents

def load_xml_root(path: Path) -> ET.Element:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML in {path}: {exc}") from exc
