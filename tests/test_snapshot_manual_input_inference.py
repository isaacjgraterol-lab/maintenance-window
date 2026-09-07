from __future__ import annotations

from pathlib import Path

import pytest

from maintenance_window.runners import snapshot_manual as runner


@pytest.mark.parametrize(
    ("filename", "expected_device", "expected_type", "expected_format"),
    [
        (
            "router-a.json",
            "router-a",
            "json",
            "json-file",
        ),
        (
            "router-a.xml",
            "router-a",
            "xml",
            "xml-file",
        ),
    ],
)
def test_upload_infers_device_and_format(
    tmp_path: Path,
    filename: str,
    expected_device: str,
    expected_type: str,
    expected_format: str,
) -> None:
    input_file = tmp_path / filename
    input_file.write_text("{}", encoding="utf-8")

    args = runner.parse_args(
        [
            "--input",
            str(input_file),
            "--protocol",
            "bgp",
            "--stage",
            "before",
            "--mw-id",
            "MW_INFERENCE_001",
        ]
    )

    config = runner.build_config(args)
    runner.validate_configuration(config)

    assert config.device == expected_device
    assert config.input_type == expected_type
    assert config.input_format == expected_format
    assert config.input_file == input_file


def test_hyphenated_device_name_is_preserved(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "router-a.json"
    input_file.write_text("{}", encoding="utf-8")

    args = runner.parse_args(
        [
            "--input",
            str(input_file),
            "--stage",
            "after",
            "--mw-id",
            "MW_HYPHEN_001",
        ]
    )

    config = runner.build_config(args)

    assert config.device == "router-a"


def test_unsupported_extension_is_rejected(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "router-a.txt"
    input_file.write_text("show bgp summary", encoding="utf-8")

    args = runner.parse_args(
        [
            "--input",
            str(input_file),
            "--stage",
            "before",
            "--mw-id",
            "MW_UNSUPPORTED_001",
        ]
    )

    with pytest.raises(
        ValueError,
        match="Unsupported manual input extension",
    ):
        runner.build_config(args)


def test_input_is_required() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args(
            [
                "--stage",
                "before",
                "--mw-id",
                "MW_REQUIRED_001",
            ]
        )


def test_legacy_input_type_flag_is_rejected(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "router.json"
    input_file.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit):
        runner.parse_args(
            [
                "--input",
                str(input_file),
                "--input-type",
                "json",
                "--stage",
                "before",
                "--mw-id",
                "MW_NO_LEGACY_001",
            ]
        )
