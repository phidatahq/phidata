#!/bin/bash

############################################################################
#
# Release phidata to pypi
# Usage:
#   ./scripts/release.sh
#
# Note:
#   build & twine must be available in the venv
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname ${CURR_DIR} )"
source ${CURR_DIR}/_utils.sh

main() {
  print_info "Releasing *phidata*"

  cd ${REPO_ROOT}
  print_info "pwd: $(pwd)"

  print_info "Upgrading phiterm dependency"
  CUSTOM_COMPILE_COMMAND="./scripts/upgrade.sh" \
    pip-compile --upgrade-package phiterm --no-annotate --pip-args "--no-cache-dir" \
      -o ${REPO_ROOT}/requirements.txt \
      ${REPO_ROOT}/pyproject.toml
  print_info "Proceed?"
  space_to_continue

  print_info "Building phidata"
  python3 -m build

  print_info "Release phidata to testpypi?"
  space_to_continue
  python3 -m twine upload --repository testpypi ${REPO_ROOT}/dist/*

  print_info "Release phidata to pypi"
  space_to_continue
  python3 -m twine upload --repository pypi ${REPO_ROOT}/dist/*
}

main "$@"
