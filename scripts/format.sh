#!/bin/bash

############################################################################
#
# Formats phidata
# Usage:
#   ./scripts/format.sh
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname ${CURR_DIR} )"
source ${CURR_DIR}/_utils.sh

print_info "Formatting phidata"
print_info "Running: black ${REPO_ROOT}"
black ${REPO_ROOT}
print_info "Running: mypy ${REPO_ROOT} --config-file ${REPO_ROOT}/pyproject.toml"
mypy ${REPO_ROOT} --config-file ${REPO_ROOT}/pyproject.toml