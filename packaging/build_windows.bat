@echo off
REM ============================================================
REM KShell Windows 打包脚本
REM 功能: 用 PyInstaller 构建 Windows exe
REM 用法: build_windows.bat
REM 要求: Python 3.6+, PyInstaller (pip install pyinstaller)
REM ============================================================

cd /d "%~dp0.."

echo ============================================
echo  KShell Windows 打包
echo ============================================

REM 检查 PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 安装 PyInstaller...
    pip install pyinstaller
)

echo 构建 exe...
python -m PyInstaller kshell.spec --noconfirm --clean

if errorlevel 1 (
    echo 打包失败!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  打包完成! 可执行文件位于: dist\kshell.exe
echo ============================================
pause
