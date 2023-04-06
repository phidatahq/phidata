#!/bin/bash

############################################################################
#
# To validate the workspace, run this script from the root directory:
# 1. Format using black
# 2. Type check using mypy
# 3. Test using pytest
# 4. Lint using ruff
# Usage:
#   ./scripts/validate.sh
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname $CURR_DIR )"
source ${CURR_DIR}/_utils.sh

main() {
  print_heading "Validating workspace..."
  print_heading "Running: black ${REPO_ROOT}"
  black ${REPO_ROOT}
  print_heading "Running: mypy ${REPO_ROOT}"
  mypy ${REPO_ROOT}
  print_heading "Running: pytest ${REPO_ROOT}"
  pytest ${REPO_ROOT}
  print_heading "Running: ruff ${REPO_ROOT}"
  ruff ${REPO_ROOT}
}

main "$@"
