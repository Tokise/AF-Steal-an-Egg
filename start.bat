@echo off
title Steal an Egg - Auto Fishing Console
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    if exist "gui_autofish.py" (
        python gui_autofish.py
        goto :eof
    )
)

if exist "StealAnEgg_AutoFish.exe" (
    start "" "StealAnEgg_AutoFish.exe"
    goto :eof
)

echo [ERROR] Neither Python script (gui_autofish.py) nor executable (StealAnEgg_AutoFish.exe) found!
pause
