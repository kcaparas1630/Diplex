"""Tests for the command line, including the Claude Code Stop hook mode and its exit codes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.conventions import __main__ as command_line

BROKEN_FILE = "def run():\n    return 1\n"


def run_checker(monkeypatch: pytest.MonkeyPatch, root: Path, *flags: str) -> int:
    """Run the command line against the repository at root with the given flags and return its exit code."""
    monkeypatch.setattr(command_line, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(sys, "argv", ["conventions", *flags])
    return command_line.main()


def test_clean_repository_exits_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A repository with no problems exits 0 and says so."""
    (tmp_path / "tool.py").write_text('"""A tool."""\n', encoding="utf-8")
    assert run_checker(monkeypatch, tmp_path) == 0
    assert "passed" in capsys.readouterr().out


def test_problems_exit_one_with_report_on_stdout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Without --hook, problems exit 1 and the report goes to stdout."""
    (tmp_path / "tool.py").write_text(BROKEN_FILE, encoding="utf-8")
    assert run_checker(monkeypatch, tmp_path) == 1
    output = capsys.readouterr()
    assert "tool.py" in output.out and "[file-docblock]" in output.out and output.err == ""


def test_hook_mode_blocks_with_exit_two_and_report_on_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With --hook, problems exit 2 and the report goes to stderr, which Claude Code feeds back to Claude."""
    (tmp_path / "tool.py").write_text(BROKEN_FILE, encoding="utf-8")
    assert run_checker(monkeypatch, tmp_path, "--hook") == 2
    output = capsys.readouterr()
    assert "[function-comment]" in output.err and output.out == ""


def test_hook_mode_is_silent_when_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With --hook and no problems, the checker prints nothing and lets Claude stop."""
    (tmp_path / "tool.py").write_text('"""A tool."""\n', encoding="utf-8")
    assert run_checker(monkeypatch, tmp_path, "--hook") == 0
    assert capsys.readouterr() == ("", "")
