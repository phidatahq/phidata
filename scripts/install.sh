#!/bin/bash

############################################################################
# Create a venv and install workspace dependencies.
# Usage: ./scripts/install.sh
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname $CURR_DIR)"
VENV_DIR="${REPO_ROOT}/.venv"
source ${CURR_DIR}/_utils.sh

print_heading "Installing workspace..."

print_heading "Creating virtual env"
print_status "VIRTUAL_ENV=${VENV_DIR} uv venv"
VIRTUAL_ENV=${VENV_DIR} uv venv

print_heading "Installing requirements"
print_status "VIRTUAL_ENV=${VENV_DIR} uv pip sync ${REPO_ROOT}/requirements.txt"
VIRTUAL_ENV=${VENV_DIR} uv pip sync ${REPO_ROOT}/requirements.txt

print_heading "Installing workspace in editable mode"
VIRTUAL_ENV=${VENV_DIR} uv pip install -e ${REPO_ROOT}

print_heading "Workspace installed"
print_heading "Activate venv using: source .venv/bin/activate"

