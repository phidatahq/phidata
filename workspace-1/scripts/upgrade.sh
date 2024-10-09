#!/bin/bash

############################################################################
#
# Upgrade python dependencies. Run this inside a virtual env.
# Usage:
# 1. Create + activate virtual env using:
#     python3 -m venv aienv
#     source aienv/bin/activate
# 2. Update dependencies from pyproject.toml:
#     ./scripts/upgrade.sh:
#       - Updates requirements.txt with any new dependencies added to pyproject.toml
# 3. Upgrade all python modules to latest version:
#     ./scripts/upgrade.sh all:
#       - Upgrade all packages in pyproject.toml to latest pinned version
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname $CURR_DIR)"
source ${CURR_DIR}/_utils.sh

main() {
  UPGRADE_ALL=0

  if [[ "$#" -eq 1 ]] && [[ "$1" = "all" ]]; then
    UPGRADE_ALL=1
  fi

  print_heading "Upgrading dependencies for workspace: ${REPO_ROOT}"
  print_heading "Installing pip & pip-tools"
  python -m pip install --upgrade pip pip-tools

  cd ${REPO_ROOT}
  if [[ UPGRADE_ALL -eq 1 ]];
  then
    print_heading "Upgrading all dependencies to latest version"
    CUSTOM_COMPILE_COMMAND="./scripts/upgrade.sh all" \
      pip-compile --upgrade --no-annotate --pip-args "--no-cache-dir" \
      -o ${REPO_ROOT}/requirements.txt \
      ${REPO_ROOT}/pyproject.toml
    print_horizontal_line
  else
    print_heading "Updating requirements.txt"
    CUSTOM_COMPILE_COMMAND="./scripts/upgrade.sh" \
      pip-compile --no-annotate --pip-args "--no-cache-dir" \
      -o ${REPO_ROOT}/requirements.txt \
      ${REPO_ROOT}/pyproject.toml
    print_horizontal_line
  fi
}

main "$@"
