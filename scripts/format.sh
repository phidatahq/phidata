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

main() {
  print_heading "Formatting phidata"
  print_heading "Running: ruff format ${REPO_ROOT}"
  ruff format ${REPO_ROOT}
  print_heading "Running: ruff check ${REPO_ROOT}"
  ruff check ${REPO_ROOT}
  print_heading "Running: mypy ${REPO_ROOT}"
  mypy ${REPO_ROOT}
  print_heading "Running: pytest ${REPO_ROOT}"
  pytest ${REPO_ROOT}
}

main "$@"
