@echo off
schtasks /run /tn "Auto Meter Application Open"
timeout /t 2 /nobreak >nul
exit /b
