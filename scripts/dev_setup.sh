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
AGNO_DOCKER_DIR="${REPO_ROOT}/libs/infra/agno_docker"
source "${CURR_DIR}/_utils.sh"

VENV_DIR="${REPO_ROOT}/.venv"
PYTHON_VERSION=$(python3 --version)

print_heading "Development setup..."

print_heading "Removing virtual env"
print_info "rm -rf ${VENV_DIR}"
rm -rf ${VENV_DIR}

print_heading "Creating virtual env"
print_info "VIRTUAL_ENV=${VENV_DIR} uv venv"
VIRTUAL_ENV=${VENV_DIR} uv venv

print_heading "Installing agno"
print_info "VIRTUAL_ENV=${VENV_DIR} uv pip install -r ${AGNO_DIR}/requirements.txt"
VIRTUAL_ENV=${VENV_DIR} uv pip install -r ${AGNO_DIR}/requirements.txt

print_heading "Installing agno in editable mode with dev dependencies"
VIRTUAL_ENV=${VENV_DIR} uv pip install -e ${AGNO_DIR}[dev]

print_heading "Installing agno-docker"
print_info "VIRTUAL_ENV=${VENV_DIR} uv pip install -r ${AGNO_DOCKER_DIR}/requirements.txt"
VIRTUAL_ENV=${VENV_DIR} uv pip install -r ${AGNO_DOCKER_DIR}/requirements.txt

print_heading "Installing agno-docker in editable mode with dev dependencies"
VIRTUAL_ENV=${VENV_DIR} uv pip install -e ${AGNO_DOCKER_DIR}[dev]

print_heading "uv pip list"
VIRTUAL_ENV=${VENV_DIR} uv pip list

print_heading "Development setup complete"
print_heading "Activate venv using: source .venv/bin/activate"
