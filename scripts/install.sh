#!/bin/bash

############################################################################
#
# Install phidata
# Usage:
#   ./scripts/install.sh
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname ${CURR_DIR} )"
source ${CURR_DIR}/_utils.sh

main() {
  print_info "Installing phidata"

  print_info "Installing requirements.txt"
  pip install --no-deps \
    -r ${REPO_ROOT}/requirements.txt

  print_info "Installing phidata with [dev] extras"
  pip3 install --editable "${REPO_ROOT}[dev]"
}

main "$@"
