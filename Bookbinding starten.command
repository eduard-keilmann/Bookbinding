#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"

# A configured environment also fixes which Tk-enabled Python is used.
if [[ -x .venv/bin/python ]]; then
    exec .venv/bin/python -m bookbinding
fi

if command -v uv >/dev/null 2>&1; then
    bookbinding_uv="$(command -v uv)"
elif [[ -x /usr/local/bin/uv ]]; then
    bookbinding_uv=/usr/local/bin/uv
elif [[ -x /opt/homebrew/bin/uv ]]; then
    bookbinding_uv=/opt/homebrew/bin/uv
else
    print 'uv fehlt. Installation: https://docs.astral.sh/uv/'
    read 'bookbinding_reply?Zum Schließen Eingabetaste drücken. '
    exit 1
fi

if [[ -x /Users/Eddie/.venvs/base/bin/python3 ]]; then
    exec "$bookbinding_uv" run --locked --no-dev --python /Users/Eddie/.venvs/base/bin/python3 python -m bookbinding
fi
exec "$bookbinding_uv" run --locked --no-dev python -m bookbinding
