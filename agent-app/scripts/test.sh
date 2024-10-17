#!/bin/bash

############################################################################
# Test workspace using pytest:
# Usage: ./scripts/test.sh
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname $CURR_DIR)"
source ${CURR_DIR}/_utils.sh

print_heading "Testing workspace..."
pytest ${REPO_ROOT}
