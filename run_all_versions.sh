#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/bhushan-arc/flytbase"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "==> Running v1.0 tests"
cd "${ROOT_DIR}/v1.0"
"${PYTHON_BIN}" -m pytest -q

echo "==> Running v1.0 visualization"
cd "${ROOT_DIR}/v1.0/src"
"${PYTHON_BIN}" visualization.py

echo "==> Running v1.1 tests"
cd "${ROOT_DIR}/v1.1"
"${PYTHON_BIN}" -m pytest -q

echo "==> Running v1.1 visualization"
cd "${ROOT_DIR}/v1.1/src"
"${PYTHON_BIN}" visualization.py

echo "==> Running v2.0 tests"
cd "${ROOT_DIR}/v2.0"
"${PYTHON_BIN}" -m pytest -q

echo "==> Running v2.0 frontend build"
cd "${ROOT_DIR}/v2.0/frontend"
npm run build

echo "==> All versions executed successfully"
