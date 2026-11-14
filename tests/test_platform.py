"""Check desktop integration without needing a Linux desktop on the test host."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from bookbinding import gui


@pytest.mark.parametrize(
    "platform,available,expected",
    [
        ("darwin", set(), ["open"]),
        ("linux", {"xdg-open", "gio"}, ["xdg-open"]),
        ("linux", {"gio"}, ["gio", "open"]),
    ],
)
def test_output_folder_uses_the_platform_desktop_opener(monkeypatch, platform, available, expected):
    app = gui.BookbindingApp.__new__(gui.BookbindingApp)
    app.last_output = Path("/tmp/Buch mit Leerzeichen")
    monkeypatch.setattr(gui.sys, "platform", platform)
    monkeypatch.setattr(gui.shutil, "which", lambda name: name if name in available else None)
    launch = Mock()
    monkeypatch.setattr(gui.subprocess, "Popen", launch)
    app._open_output()
    launch.assert_called_once_with([*expected, str(app.last_output)])


@pytest.mark.parametrize("missing", [False, True])
def test_folder_opener_failures_are_shown_without_crashing(monkeypatch, missing):
    app = gui.BookbindingApp.__new__(gui.BookbindingApp)
    app.last_output = Path("/tmp/output")
    app.root = object()
    monkeypatch.setattr(gui.sys, "platform", "linux")
    monkeypatch.setattr(gui.shutil, "which", lambda name: None if missing else name)
    launch = Mock(side_effect=FileNotFoundError("opener unavailable"))
    dialog = Mock()
    monkeypatch.setattr(gui.subprocess, "Popen", launch)
    monkeypatch.setattr(gui.messagebox, "showerror", dialog)
    app._open_output()
    dialog.assert_called_once()
    if missing:
        launch.assert_not_called()
        assert str(app.last_output) in dialog.call_args.args[1]


def test_linux_launcher_works_from_another_directory_with_spaces(tmp_path):
    project = tmp_path / "Projekt mit Leerzeichen"
    interpreter = project / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        '#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nprintf "%s\\n" "$PWD" "$@"\n',
        encoding="utf-8",
    )
    interpreter.chmod(0o755)
    launcher = project / "bookbinding-linux.sh"
    shutil.copyfile(Path(__file__).parents[1] / launcher.name, launcher)
    result = subprocess.run(
        ["sh", str(launcher)], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert result.stdout.splitlines() == [str(project), "-m", "bookbinding"]
