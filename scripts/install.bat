@echo off
:: Install phidata
:: Usage:
::   .\scripts\install.bat

set "CURR_DIR=%~dp0"
set "REPO_ROOT=%~dp0.."
call "%CURR_DIR%_utils.bat"

:main
call :print_heading "Installing phidata"

call :print_heading "Installing requirements.txt"
call "%REPO_ROOT%\phienv\Scripts\pip" install --no-deps -r "%REPO_ROOT%\requirements.txt"

call :print_heading "Installing phidata with [dev] extras"
call "%REPO_ROOT%\phienv\Scripts\pip" install --editable "%REPO_ROOT%[dev]"

goto :eof
