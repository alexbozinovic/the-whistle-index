#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run scripts/setup_env.sh first."
  exit 1
fi

GAME_ID="${1:-}"
if [[ -z "$GAME_ID" ]]; then
  echo "Usage: scripts/run_acceptance.sh <game_id>"
  exit 1
fi

source .venv/bin/activate

scripts/run_pipeline.sh --game-id "$GAME_ID"
python scripts/sanity_check.py --game-id "$GAME_ID"

echo "Acceptance run completed for game $GAME_ID"
