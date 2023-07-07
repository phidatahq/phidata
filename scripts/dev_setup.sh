#!/bin/bash

############################################################################
#
# Install editable phidata in a virtual environment
# Usage:
#   ./scripts/dev_setup.sh
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname ${CURR_DIR} )"
VENV_DIR="${REPO_ROOT}/phienv"
source ${CURR_DIR}/_utils.sh

create_venv() {
  print_info "Creating venv: ${VENV_DIR}"

  print_status "Removing existing venv: ${VENV_DIR}"
  rm -rf ${VENV_DIR}

  print_status "Creating python3 venv: ${VENV_DIR}"
  python3 -m venv ${VENV_DIR}

  # Install workspace
  source ${VENV_DIR}/bin/activate
  source ${CURR_DIR}/install.sh

  print_info "Activate using: source ${VENV_DIR}/bin/activate"

  print_info_2 "Installing base python packages"
  pip3 install --upgrade pip pip-tools twine build
}

main() {
  print_info "phidata dev setup"
  create_venv

  print_info "Installing requirements.txt"
  pip install --no-deps \
    -r ${REPO_ROOT}/requirements.txt

  print_info "Installing phidata with [dev] extras"
  pip install --editable "${REPO_ROOT}[dev]"
}

main "$@"
