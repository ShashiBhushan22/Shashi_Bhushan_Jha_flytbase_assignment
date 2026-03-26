#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
PRIVATE_DOCS_DIR="${PRIVATE_DOCS_DIR:-${HOME}/flytbase_private_docs}"

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

open_output() {
  local output_path="$1"
  if [[ ! -e "${output_path}" ]]; then
    echo "Warning: output not found: ${output_path}" >&2
    return 1
  fi

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${output_path}" >/dev/null 2>&1 || true
    return 0
  fi
  if command -v open >/dev/null 2>&1; then
    open "${output_path}" >/dev/null 2>&1 || true
    return 0
  fi
  "${PYTHON_BIN}" -m webbrowser "file://${output_path}" >/dev/null 2>&1 || true
}

open_generated_outputs() {
  if [[ "${OPEN_BROWSER:-1}" != "1" ]]; then
    echo "Browser auto-open disabled because OPEN_BROWSER=${OPEN_BROWSER}."
    return
  fi

  local output_path
  for output_path in "$@"; do
    open_output "${output_path}"
  done
}

open_outputs_in_dir() {
  local output_dir="$1"
  if [[ ! -d "${output_dir}" ]]; then
    echo "Warning: output directory not found: ${output_dir}" >&2
    return 1
  fi

  mapfile -t output_files < <(find "${output_dir}" -maxdepth 1 -type f | sort)
  if [[ "${#output_files[@]}" -eq 0 ]]; then
    echo "Warning: no generated outputs found in ${output_dir}" >&2
    return 1
  fi

  open_generated_outputs "${output_files[@]}"
}

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}."
  echo "Create the shared environment first:"
  echo "  cd ${ROOT_DIR}"
  echo "  python3 -m venv .venv"
  echo "  ./.venv/bin/pip install -U pip"
  echo "  ./.venv/bin/pip install -r v1.0/requirements.txt -r v1.1/requirements.txt -r v2.0/requirements.txt"
  echo "  ./.venv/bin/pip install -e ./v2.0"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required for the v2.0 frontend build."
  exit 1
fi

echo "==> Running v1.0 tests"
cd "${ROOT_DIR}/v1.0"
"${PYTHON_BIN}" -m pytest -q

echo "==> Running v1.0 visualization"
cd "${ROOT_DIR}/v1.0/src"
"${PYTHON_BIN}" visualization.py
open_outputs_in_dir "${ROOT_DIR}/v1.0/src/plots"

echo "==> Running v1.1 tests"
cd "${ROOT_DIR}/v1.1"
"${PYTHON_BIN}" -m pytest -q

echo "==> Running v1.1 visualization"
cd "${ROOT_DIR}/v1.1/src"
"${PYTHON_BIN}" visualization.py
open_outputs_in_dir "${ROOT_DIR}/v1.1/src/plots"

echo "==> Running v2.0 tests"
cd "${ROOT_DIR}/v2.0"
"${PYTHON_BIN}" -m pytest -q

echo "==> Generating v2.0 3D/4D visualization artifacts"
"${PYTHON_BIN}" scripts/generate_visuals.py
open_outputs_in_dir "${ROOT_DIR}/v2.0/docs/plots"

echo "==> Running v2.0 performance benchmark"
"${PYTHON_BIN}" scripts/benchmark_load.py

echo "==> Running v2.0 frontend build"
cd "${ROOT_DIR}/v2.0/frontend"
npm run build

if command -v pdflatex >/dev/null 2>&1 && [[ -f "${PRIVATE_DOCS_DIR}/repo_code_walkthrough.tex" ]]; then
  echo "==> Building private walkthrough PDF in ${PRIVATE_DOCS_DIR}"
  cd "${PRIVATE_DOCS_DIR}"
  pdflatex -interaction=nonstopmode -halt-on-error repo_code_walkthrough.tex >/dev/null
  pdflatex -interaction=nonstopmode -halt-on-error repo_code_walkthrough.tex >/dev/null
elif command -v pdflatex >/dev/null 2>&1; then
  echo "==> Skipping private walkthrough PDF build because ${PRIVATE_DOCS_DIR}/repo_code_walkthrough.tex was not found"
fi

echo "==> All versions executed successfully"
echo "==> Launching live v2.0 project"
exec "${ROOT_DIR}/run_live_webapps.sh"
