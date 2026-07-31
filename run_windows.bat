@echo off
chcp 65001 >nul
title 账单整理工具

cd /d "%~dp0"

echo =========================================
echo   账单整理工具 启动中...
echo =========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 Python，请先安装 Python 3
    echo    下载地址: https://www.python.org/downloads/
    echo    安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo ✅ 检测到 Python:
python --version
echo.

:: 安装依赖
echo 📦 正在检查/安装依赖...
pip install -r requirements.txt -q

echo.
echo 🌐 正在启动网页服务...
echo    请在浏览器中打开: http://localhost:8501
echo.
echo    关闭此窗口将停止服务
echo =========================================
echo.

streamlit run app.py

pause
