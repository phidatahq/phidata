@echo off
:: Collection of helper functions to import in other scripts

:: Function to pause the script until a key is pressed
:space_to_continue
echo Press any key to continue...
pause > nul
goto :eof

:: Function to print a horizontal line
:print_horizontal_line
echo ------------------------------------------------------------
goto :eof

:: Function to print a heading with horizontal lines
:print_heading
call :print_horizontal_line
echo -*- %~1
call :print_horizontal_line
goto :eof

:: Function to print a status message
:print_info
echo -*- %~1
goto :eof
