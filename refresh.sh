#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$project_dir/backend"

if [[ ! -x "$backend_dir/venv/bin/python" ]]; then
    echo "mtg-database virtualenv was not found at $backend_dir/venv/bin/python" >&2
    exit 1
fi

echo "Refreshing mtg-database data. Stop or drain mtg-database first so SQLite VACUUM can obtain its exclusive lock."
cd "$backend_dir"
exec ./venv/bin/python scripts/refresh_mtg_data.py
