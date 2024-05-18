@echo off

rem ############################################################################
rem #
rem # Upgrade python dependencies. Please run this inside a virtual env
rem # Usage:
rem # 1. Update dependencies added to pyproject.toml:
rem #     ./scripts/upgrade.bat:
rem #       - Update requirements.txt with any new dependencies added to pyproject.toml
rem # 3. Upgrade all python modules to latest version:
rem #     ./scripts/upgrade.bat all:
rem #       - Upgrade all packages in pyproject.toml to latest pinned version
rem ############################################################################

set "CURR_DIR=%~dp0"
set "REPO_ROOT=%~dp0.."

set "UTILS_BAT=%CURR_DIR%_utils.bat"

set UPGRADE_ALL=0

if "%1" == "all" (
  set UPGRADE_ALL=1
)

call "%UTILS_BAT%" print_heading "Upgrading phidata dependencies"
call "%UTILS_BAT%" print_heading "Installing pip and pip-tools"
python -m pip install --upgrade pip 
python -m pip install --upgrade pip-tools

cd %REPO_ROOT%
if %UPGRADE_ALL% == 1 (
  call "%UTILS_BAT%" print_heading "Upgrading all dependencies to latest version"
  set CUSTOM_COMPILE_COMMAND="./scripts/upgrade.bat"
  pip-compile --upgrade --no-annotate --pip-args "--no-cache-dir" -o %REPO_ROOT%\requirements.txt %REPO_ROOT%\pyproject.toml
  call "%UTILS_BAT%" print_horizontal_line
) else (
  call "%UTILS_BAT%" print_heading "Updating requirements.txt"
  set CUSTOM_COMPILE_COMMAND="./scripts/upgrade.bat"
  pip-compile --no-annotate --pip-args "--no-cache-dir" -o %REPO_ROOT%\requirements.txt %REPO_ROOT%\pyproject.toml
  call "%UTILS_BAT%" print_horizontal_line
)
