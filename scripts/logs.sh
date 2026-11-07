#!/usr/bin/env bash
# Stream live OptimAI node logs directly to the terminal
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR" || exit 1

if [ -f ".venv/bin/python" ]; then
  exec .venv/bin/python -m bot.main logs "$@"
else
  exec python3 -m bot.main logs "$@"
fi
