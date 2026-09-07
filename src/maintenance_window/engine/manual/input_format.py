from __future__ import annotations

from pathlib import Path


DEFAULT_MANUAL_FORMATS_BY_SUFFIX = {
    ".json": "json-file",
    ".xml": "xml-file",
}


def detect_manual_input_format(
    input_file: Path,
    input_format: str | None,
    formats_by_suffix: dict[str, str] | None = None,
) -> str:
    """
    Detect a manual input format from CLI value or file extension.
    """
    if input_format:
        return input_format

    suffix_map = (
        formats_by_suffix
        if formats_by_suffix is not None
        else DEFAULT_MANUAL_FORMATS_BY_SUFFIX
    )
    suffix = input_file.suffix.lower()

    try:
        return suffix_map[suffix]
    except KeyError as exc:
        raise ValueError(
            "Unable to detect manual input format. Use an explicit "
            "--input-format value."
        ) from exc
