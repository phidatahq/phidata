@echo off

:: Formats phidata

:: Usage:
:: .\scripts\format.bat

set "CURR_DIR=%~dp0"
set "REPO_ROOT=%~dp0.."

:: Ensure that _utils.bat is correctly located and called
call "%CURR_DIR%\_utils.bat"

:main
call :print_heading "Formatting phidata"

call :print_heading "Running: ruff format %REPO_ROOT%"
call "%REPO_ROOT%\phienv\Scripts\ruff" format "%REPO_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo Failed to format with ruff.
    goto :eof
)

call :print_heading "Running: ruff check %REPO_ROOT%"
call "%REPO_ROOT%\phienv\Scripts\ruff" check "%REPO_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo Failed ruff check.
    goto :eof
)

call :print_heading "Running: mypy %REPO_ROOT%"
call "%REPO_ROOT%\phienv\Scripts\mypy" "%REPO_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo Failed mypy check.
    goto :eof
)

call :print_heading "Running: pytest %REPO_ROOT%"
call "%REPO_ROOT%\phienv\Scripts\pytest" "%REPO_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo Failed pytest.
    goto :eof
)

goto :eof