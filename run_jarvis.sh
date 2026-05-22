#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python jarvis.py
fi

echo "[JARVIS] Virtual environment not found at .venv"
echo "[JARVIS] Run setup first:"
echo "    python setup_jarvis.py"
exit 1
