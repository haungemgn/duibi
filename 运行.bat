@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动数据对比工具...
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw app\main.py
) else (
    python app\main.py
)
