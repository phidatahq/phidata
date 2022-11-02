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
  print_heading "Installing phidata"

  print_heading "Installing requirements.txt"
  pip install --no-deps \
    -r ${ROOT_DIR}/requirements.txt

  print_heading "Installing phidata with [dev] extras"
  pip3 install --editable "${ROOT_DIR}[dev]"
}

main "$@"
