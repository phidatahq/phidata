#!/bin/bash

############################################################################
# Agno Development Setup
# - Create a virtual environment and install libraries in editable mode.
# - Please install uv before running this script.
# - Please deactivate the existing virtual environment before running.
# Usage: ./scripts/dev_setup.sh
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${CURR_DIR}")"
AGNO_DIR="${REPO_ROOT}/libs/agno"
PHI_DIR="${REPO_ROOT}/libs/phi"
source "${CURR_DIR}/_utils.sh"

VENV_DIR="${REPO_ROOT}/.venv"
PYTHON_VERSION=$(python3 --version)

print_heading "Development setup..."

print_heading "Creating virtual env at ${VENV_DIR}"
print_info "VIRTUAL_ENV=${VENV_DIR} uv venv"
VIRTUAL_ENV=${VENV_DIR} uv venv

print_heading "Installing Agno"
print_info "VIRTUAL_ENV=${VENV_DIR} uv pip sync ${AGNO_DIR}/requirements.txt"
VIRTUAL_ENV=${VENV_DIR} uv pip sync ${AGNO_DIR}/requirements.txt

print_heading "Installing Agno in editable mode with all dependencies"
VIRTUAL_ENV=${VENV_DIR} uv pip install -e ${AGNO_DIR}[all]

print_heading "Development setup complete"
print_heading "Activate venv using: source .venv/bin/activate"
