#!/bin/bash

############################################################################
#
# Script to merge/push existing branch to the mainbranch:
# Usage:
#   ./scripts/merge_main.sh
#     - commit current branch
#     - merge to `main` branch
#     - push to remote origin `main` branch
#
#   ./scripts/merge_main.sh y
#     - Default yes to user validation
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$( dirname ${CURR_DIR} )"
source ${CURR_DIR}/_utils.sh

main() {
  YES=0
  if [[ "$#" -eq 1 ]] && [[ "$1" = "y" ]]; then
    YES=1
  fi

  GIT_BRANCH=`git -C ${REPO_ROOT} rev-parse --abbrev-ref HEAD`
  GIT_COMMIT=`git -C ${REPO_ROOT} rev-parse HEAD`

  print_horizontal_line
  print_info_2 "REPO_ROOT        : ${REPO_ROOT}"
  print_info_2 "GIT_BRANCH       : ${GIT_BRANCH}"
  print_info_2 "GIT_COMMIT       : ${GIT_COMMIT}"
  print_info_2 "DATETIME         : $(date)"
  print_horizontal_line

  print_info_2 "Auto commiting all files in ${REPO_ROOT}"
  if [[ ${YES} -ne 1 ]]; then
    space_to_continue
  fi
  git -C ${REPO_ROOT} add .
  git -C ${REPO_ROOT} commit -am "Auto commit on $(date)"

  print_info "Merging ${GIT_BRANCH} to main branch"
  git -C ${REPO_ROOT} checkout main
  git -C ${REPO_ROOT} merge --no-ff ${GIT_BRANCH}
  git -C ${REPO_ROOT} push origin main
  print_info "${REPO_ROOT} pushed to main"
}

main "$@"
