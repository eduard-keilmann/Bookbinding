#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"

# Use the project environment first; it already selects a compatible Python.
if [ -x .venv/bin/python ]; then
    bookbinding_python=.venv/bin/python
else
    bookbinding_python=python3
fi

if ! "$bookbinding_python" -c 'import sys, tkinter; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    printf '%s\n' 'Python ab 3.11 mit Tkinter benötigt. Bitte über die Linux-Paketverwaltung installieren.' >&2
    exit 1
fi

if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -m bookbinding
fi

if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'uv fehlt. Installation: https://docs.astral.sh/uv/' >&2
    exit 1
fi

# Keep the Tk-enabled system interpreter instead of downloading another Python.
exec uv run --locked --no-dev --no-python-downloads --python "$(command -v python3)" python -m bookbinding
