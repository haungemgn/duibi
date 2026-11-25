@echo off
setlocal
cd /d "%~dp0"

echo Starting Data Compare Tool...
for %%P in (python.exe) do set "PYTHON_EXE=%%~$PATH:P"
if not defined PYTHON_EXE goto :no_python
"%PYTHON_EXE%" -c "import sys; sys.exit(sys.version_info < (3, 10))"
if errorlevel 1 goto :no_python

"%PYTHON_EXE%" -c "import PySide6"
if errorlevel 1 goto :no_pyside6

for %%P in ("%PYTHON_EXE%") do set "PYTHONW_EXE=%%~dpPpythonw.exe"
if not exist "%PYTHONW_EXE%" goto :run_console

start "" "%PYTHONW_EXE%" -m app
if errorlevel 1 goto :run_failed
exit /b 0

:run_console
"%PYTHON_EXE%" -m app
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
