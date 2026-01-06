@echo off
REM Wrapper to run launch_and_connect.py and capture output
cd /d "%~dp0"

echo Starting launch_and_connect.py... > launch_and_connect_task.log
echo Time: %date% %time% >> launch_and_connect_task.log

".venv\Scripts\python.exe" "launch_and_connect.py" >> launch_and_connect_task.log 2>&1

echo Exit code: %errorlevel% >> launch_and_connect_task.log
echo Completed at: %date% %time% >> launch_and_connect_task.log
