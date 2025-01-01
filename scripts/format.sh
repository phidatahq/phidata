#!/bin/bash

############################################################################
# Format all libraries
# Usage: ./scripts/format.sh
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${CURR_DIR}")"
AGNO_DIR="${REPO_ROOT}/libs/agno"
PHI_DIR="${REPO_ROOT}/libs/phi"
source ${CURR_DIR}/_utils.sh

print_heading "Formatting all libraries"
source ${AGNO_DIR}/scripts/format.sh
