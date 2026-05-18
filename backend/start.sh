#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}"
cd "${ROOT}/backend"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-10000}"
