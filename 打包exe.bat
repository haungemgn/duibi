@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   打包数据对比工具为单文件 exe
echo ============================================
echo.
echo [1/2] 安装/检查 PyInstaller...
python -m pip install pyinstaller >nul 2>nul

echo [2/2] 开始打包（首次较慢，请耐心等待）...
python -m PyInstaller --noconfirm --onefile --windowed --name "数据对比工具" app\main.py

echo.
if exist "dist\数据对比工具.exe" (
    echo 打包成功！exe 位于： dist\数据对比工具.exe
) else (
    echo 打包失败，请查看上面的错误信息。
)
pause
