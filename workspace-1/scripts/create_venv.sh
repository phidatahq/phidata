#!/bin/bash

############################################################################
#
# Create Virtual Environment & Install Requirements
# Usage:
#   ./scripts/create_venv.sh
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname ${CURR_DIR})"
VENV_DIR="${REPO_ROOT}/aienv"
source ${CURR_DIR}/_utils.sh

main() {
  print_heading "Setup: ${VENV_DIR}"

  print_status "Removing existing venv: ${VENV_DIR}"
  rm -rf ${VENV_DIR}

  print_status "Creating python3 venv: ${VENV_DIR}"
  python3 -m venv ${VENV_DIR}

  # Install workspace
  source ${VENV_DIR}/bin/activate
  source ${CURR_DIR}/install.sh

  print_heading "Activate using: source aienv/bin/activate"
}

main "$@"
