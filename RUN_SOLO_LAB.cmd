@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m tools.solo_lab_gui
) else (
    python -m tools.solo_lab_gui
)
if errorlevel 1 (
    echo.
    echo Solo Cheat Lab requires Python 3.10+ with Tkinter on Windows.
    echo All game file modifications are opt-in. No trainer is launched.
    pause
)
