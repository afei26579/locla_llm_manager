@echo off
chcp 65001 >nul
title AI 助手 - 安装

echo ==========================================
echo            AI 助手 - 安装程序
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    echo 请安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/2] 正在安装依赖...
pip install PySide6 modelscope requests psutil -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [2/2] 检查 Ollama...
if exist "runtime\ollama\ollama.exe" (
    echo ✅ Ollama 已就绪
) else (
    echo ⚠️ 请将 ollama.exe 放到 runtime\ollama\ 目录
)

echo.
echo ==========================================
echo              安装完成!
echo ==========================================
echo 运行 start.bat 启动程序
pause