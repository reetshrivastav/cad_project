#!/usr/bin/env bash
# Usage: bash scripts/start_lab_gateway.sh static|adaptive [model-directory]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export GATEWAY_ROUTING_MODE="${1:-adaptive}"
export GATEWAY_MODELS_DIR="${2:-models/lab_native_v1}"
exec .venv/bin/python app.py
