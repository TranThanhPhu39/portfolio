@echo off
cd /d "%~dp0"
if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
  "%VIRTUAL_ENV%\Scripts\python.exe" "%~dp0launch_report.py" --open-latest
) else if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0launch_report.py" --open-latest
) else (
  python "%~dp0launch_report.py" --open-latest
)
if errorlevel 1 pause
