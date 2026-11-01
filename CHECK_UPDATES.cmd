@echo off
setlocal
cd /d "%~dp0"
echo AZSE Official Windows Updater - read-only check
set /p GROOT=Path to original game folder: 
py -3 -m tools.official_update_manager check --game-root "%GROOT%"
if errorlevel 1 echo Check failed; no game files were changed.
pause
