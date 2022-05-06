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

print_info "Installing phidata"
pip install -r ${REPO_ROOT}/requirements.txt --no-deps
pip3 install --editable ${REPO_ROOT}
