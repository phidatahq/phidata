@echo off
setlocal

set "CURR_DIR=%~dp0"
set "REPO_ROOT=%~dp0.."
set "VENV_DIR=%REPO_ROOT%\phienv"

set "UTILS_BAT=%CURR_DIR%_utils.bat"

call "%UTILS_BAT%" print_heading "phidata dev setup"
call "%UTILS_BAT%" print_heading "Creating venv: %VENV_DIR%"

call "%UTILS_BAT%" print_heading "Removing existing venv: %VENV_DIR%"
rd /s /q "%VENV_DIR%"

call "%UTILS_BAT%" print_heading "Creating python3 venv: %VENV_DIR%"
python -m venv "%VENV_DIR%"

call "%UTILS_BAT%" print_heading "Upgrading pip to the latest version"
call "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo Failed to upgrade pip. Please run the script as Administrator or check your network connection.
    exit /b %ERRORLEVEL%
)

call "%UTILS_BAT%" print_heading "Installing base python packages"
call "%VENV_DIR%\Scripts\pip" install pip-tools twine build
if %ERRORLEVEL% neq 0 (
    echo Failed to install required packages. Attempting to retry installation...
    call "%VENV_DIR%\Scripts\pip" install pip-tools twine build
)

:: Install workspace
call "%VENV_DIR%\Scripts\activate"
call "%CURR_DIR%install.bat"

call "%UTILS_BAT%" print_heading "Activate using: call %VENV_DIR%\Scripts\activate"

endlocal
