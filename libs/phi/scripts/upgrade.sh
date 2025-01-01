#!/bin/bash

############################################################################
#
# Upgrade python dependencies. Please run this inside a virtual env
# Usage:
# 1. Update dependencies added to pyproject.toml:
#     ./scripts/upgrade.sh:
#       - Update requirements.txt with any new dependencies added to pyproject.toml
# 3. Upgrade all python modules to latest version:
#     ./scripts/upgrade.sh all:
#       - Upgrade all packages in pyproject.toml to latest pinned version
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$( dirname $CURR_DIR )"
source ${CURR_DIR}/_utils.sh

main() {
  UPGRADE_ALL=0

  if [[ "$#" -eq 1 ]] && [[ "$1" = "all" ]]; then
    UPGRADE_ALL=1
  fi

  print_heading "Upgrading phidata dependencies"
  print_heading "Installing pip & pip-tools"
  python -m pip install --upgrade pip pip-tools

  cd ${ROOT_DIR}
  if [[ UPGRADE_ALL -eq 1 ]];
  then
    print_heading "Upgrading all dependencies to latest version"
    CUSTOM_COMPILE_COMMAND="./scripts/upgrade.sh all" \
      pip-compile --upgrade --no-annotate --pip-args "--no-cache-dir" \
      -o ${ROOT_DIR}/requirements.txt \
      ${ROOT_DIR}/pyproject.toml
    print_horizontal_line
  else
    print_heading "Updating requirements.txt"
    CUSTOM_COMPILE_COMMAND="./scripts/upgrade.sh" \
      pip-compile --no-annotate --pip-args "--no-cache-dir" \
      -o ${ROOT_DIR}/requirements.txt \
      ${ROOT_DIR}/pyproject.toml
    print_horizontal_line
  fi
}

main "$@"
