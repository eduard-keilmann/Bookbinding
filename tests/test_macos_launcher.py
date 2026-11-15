"""The source launcher must not depend on editable-install path hooks."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("zsh") is None, reason="Requires zsh")
def test_macos_launcher_loads_checkout_without_site_path_hooks(tmp_path):
    project = tmp_path / "Project with spaces"
    package = project / "src/bookbinding"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "__main__.py").write_text('print("checkout started")')
    python = project / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' -S "$@"\n')
    python.chmod(0o755)
    source = Path(__file__).parents[1]
    launcher = project / "Bookbinding starten.command"
    shutil.copyfile(source / launcher.name, launcher)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        ["zsh", str(launcher)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "checkout started"
