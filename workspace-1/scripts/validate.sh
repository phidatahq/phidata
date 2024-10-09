#!/bin/bash

############################################################################
#
# Run this script to validate the workspace:
# 1. Type check using mypy
# 2. Lint using ruff
# Usage:
#   ./scripts/validate.sh
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname $CURR_DIR)"
source ${CURR_DIR}/_utils.sh

main() {
  print_heading "Validating workspace..."
  print_heading "Running: ruff check ${REPO_ROOT}"
  ruff check ${REPO_ROOT}
  print_heading "Running: mypy ${REPO_ROOT}"
  mypy ${REPO_ROOT}
}

main "$@"
