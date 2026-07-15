#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -n "${INSIFT_PYTHON:-}" ]]; then
    PYTHON_BIN="$INSIFT_PYTHON"
elif [[ -x "/opt/anaconda3/bin/python" ]]; then
    # The project-local .venv may be offloaded by macOS; Anaconda is local here.
    PYTHON_BIN="/opt/anaconda3/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "Python 3.11 or newer is required." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c "import streamlit, sqlalchemy, pydantic" >/dev/null 2>&1; then
    echo "InSift dependencies are not installed for $PYTHON_BIN." >&2
    echo "Run: $PYTHON_BIN -m pip install -r requirements.txt" >&2
    exit 1
fi

if [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo "Created .env from .env.example."
fi

"$PYTHON_BIN" scripts/initialize_database.py

echo "Starting InSift with $PYTHON_BIN"
echo "Open the Local URL that Streamlit prints below."
exec "$PYTHON_BIN" -m streamlit run streamlit_app.py "$@"
