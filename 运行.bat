@echo off
setlocal
cd /d "%~dp0"

echo Starting Data Compare Tool...
where python >nul 2>nul
if errorlevel 1 goto :no_python

python -c "import PySide6" >nul 2>nul
if errorlevel 1 goto :no_pyside6

where pythonw >nul 2>nul
if errorlevel 1 goto :run_console

start "" pythonw -m app
exit /b 0

:run_console
python -m app
if errorlevel 1 goto :run_failed
exit /b 0

:no_python
echo Python 3.10 or newer was not found in PATH.
echo Download Python and enable "Add Python to PATH" during installation.
goto :failed

:no_pyside6
echo PySide6 is not installed.
echo Run: python -m pip install -r requirements.txt
goto :failed

:run_failed
echo The application failed to start. Review the error above.

:failed
pause
exit /b 1
