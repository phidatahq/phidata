#!/bin/bash

############################################################################
#
# Collection of helper functions to import in other scripts
#
############################################################################

space_to_continue() {
  read -n1 -r -p "Press Enter/Space to continue...  " key
  if [ "$key" = '' ]; then
    # Space pressed, pass
    :
  else
    exit 1
  fi
  echo ""
}

print_horizontal_line() {
  echo "------------------------------------------------------------"
}

print_info() {
  print_horizontal_line
  echo "--*--> $1"
  print_horizontal_line
}

print_info_2() {
  echo "--*--> $1"
}

print_status() {
  echo "* $1"
}
