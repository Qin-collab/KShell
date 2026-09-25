@echo off
REM KShell Windows 启动脚本

python kshell.py %*

if %errorlevel% neq 0 (
    echo 启动失败，请确保 Python 3.6+ 已安装
    pause
)