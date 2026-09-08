from pathlib import Path
from unittest.mock import patch

import pytest
from app.source_path_parser import SourcePathParser


@patch("app.source_path_parser.settings")
def test_parses_assignment_identity_and_relative_path(settings):
    settings.WATCH_ROOT = Path("/watch/root")
    result = SourcePathParser().parse(
        Path("/watch/root/os-1-202012345/assignment-42/src/main.c")
    )
    assert result == {
        "class_div": "os-1",
        "hw_name": "assignment-42",
        "assignment_id": 42,
        "student_id": "202012345",
        "filename": "src/main.c",
    }


@patch("app.source_path_parser.settings")
def test_rejects_mutable_assignment_directory(settings):
    settings.WATCH_ROOT = Path("/watch/root")
    with pytest.raises(ValueError, match="불변 과제 경로"):
        SourcePathParser().parse(Path("/watch/root/os-1-202012345/hw1/main.c"))


@patch("app.source_path_parser.settings")
def test_rejects_path_outside_workspace(settings):
    settings.WATCH_ROOT = Path("/watch/root")
    with pytest.raises(ValueError, match="WATCH_ROOT 하위"):
        SourcePathParser().parse(Path("/other/os-1-202012345/assignment-42/main.c"))
