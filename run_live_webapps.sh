#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
API_PORT="${API_PORT:-8000}"
VITE_PORT="${VITE_PORT:-5173}"
PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid}" ]]; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempt
  for ((attempt = 1; attempt <= 45; attempt += 1)); do
    if "${PYTHON_BIN}" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1)' "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Warning: ${label} did not respond in time at ${url}." >&2
  return 1
}

open_browser_tab() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${url}" >/dev/null 2>&1 || true
    return
  fi
  if command -v open >/dev/null 2>&1; then
    open "${url}" >/dev/null 2>&1 || true
    return
  fi
  "${PYTHON_BIN}" -m webbrowser "${url}" >/dev/null 2>&1 || true
}

open_live_dashboards() {
  if [[ "${OPEN_BROWSER:-1}" != "1" ]]; then
    echo "Browser auto-open disabled because OPEN_BROWSER=${OPEN_BROWSER}."
    return
  fi

  local dashboard_url="http://127.0.0.1:${STREAMLIT_PORT}"
  local console_url="http://127.0.0.1:${VITE_PORT}"

  (
    wait_for_http "${dashboard_url}" "ATC deconfliction dashboard" && open_browser_tab "${dashboard_url}"
  ) &
  (
    wait_for_http "${console_url}" "ATC console frontend" && open_browser_tab "${console_url}"
  ) &
}

trap cleanup EXIT INT TERM

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}."
  echo "Create the shared environment first from ${ROOT_DIR}:"
  echo "  python3 -m venv .venv"
  echo "  ./.venv/bin/pip install -U pip"
  echo "  ./.venv/bin/pip install -r v1.0/requirements.txt -r v1.1/requirements.txt -r v2.0/requirements.txt"
  echo "  ./.venv/bin/pip install -e ./v2.0"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to run the ATC Console frontend."
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/v2.0/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies first..."
  (
    cd "${ROOT_DIR}/v2.0/frontend"
    npm install
  )
fi

echo "Starting FlytBase live web apps:"
echo "  ATC deconfliction dashboard: http://127.0.0.1:${STREAMLIT_PORT}"
echo "  ATC API:                    http://127.0.0.1:${API_PORT}"
echo "  ATC console frontend:       http://127.0.0.1:${VITE_PORT}"

(
  cd "${ROOT_DIR}/v2.0"
  "${PYTHON_BIN}" -m streamlit run app.py --server.address 127.0.0.1 --server.port "${STREAMLIT_PORT}"
) &
PIDS+=("$!")

(
  cd "${ROOT_DIR}/v2.0"
  "${PYTHON_BIN}" -m uvicorn server.main:app --host 127.0.0.1 --port "${API_PORT}"
) &
PIDS+=("$!")

(
  cd "${ROOT_DIR}/v2.0/frontend"
  npm run dev -- --host 127.0.0.1 --port "${VITE_PORT}"
) &
PIDS+=("$!")

open_live_dashboards

wait
