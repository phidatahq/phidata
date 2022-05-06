#!/bin/bash

############################################################################
#
# Update phidata dependencies
# Usage:
#   ./scripts/update_dependencies.sh
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname ${CURR_DIR} )"
source ${CURR_DIR}/_utils.sh

print_info "Updating phidata dependencies"
cd ${REPO_ROOT}
CUSTOM_COMPILE_COMMAND="./scripts/update_dependencies.sh" \
    pip-compile --upgrade --pip-args "--no-cache-dir"
