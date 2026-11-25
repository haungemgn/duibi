@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Build Data Compare Tool as a single EXE
echo ============================================

python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if errorlevel 1 goto :no_python

echo [1/2] Installing or checking build dependencies...
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :build_failed

echo [2/2] Building. The first build may take a while...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "数据对比工具" app\main.py
if errorlevel 1 goto :build_failed

if not exist "dist\数据对比工具.exe" goto :build_failed
echo Build succeeded: dist\数据对比工具.exe
pause
exit /b 0

:no_python
echo Python 3.10 or newer was not found in PATH.
goto :failed

:build_failed
echo Build failed. Review the error above.

:failed
pause
exit /b 1
