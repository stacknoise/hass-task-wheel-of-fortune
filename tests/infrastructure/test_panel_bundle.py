"""Suche nach dem gebauten Panel-Bundle."""

import os
from pathlib import Path

from custom_components.task_wheel.infrastructure.panel_bundle import find_bundle_name

OLDER = 1_000
NEWER = 2_000


def test_missing_directory_gives_none(tmp_path: Path):
    assert find_bundle_name(tmp_path / "dist") is None


def test_directory_without_entry_gives_none(tmp_path: Path):
    (tmp_path / "state-abc.js").write_text("x")
    assert find_bundle_name(tmp_path) is None


def test_finds_entry_and_ignores_chunks(tmp_path: Path):
    (tmp_path / "state-abc.js").write_text("x")
    (tmp_path / "task-wheel-panel.abc123.js").write_text("x")
    assert find_bundle_name(tmp_path) == "task-wheel-panel.abc123.js"


def test_newest_entry_wins(tmp_path: Path):
    old = tmp_path / "task-wheel-panel.old.js"
    new = tmp_path / "task-wheel-panel.new.js"
    old.write_text("x")
    new.write_text("x")
    os.utime(old, (NEWER, NEWER))
    os.utime(new, (OLDER, OLDER))
    assert find_bundle_name(tmp_path) == "task-wheel-panel.old.js"
