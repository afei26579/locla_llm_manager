@echo off
chcp 65001 >nul
title AI 助手

cd /d "%~dp0"

python main.py

if errorlevel 1 (
    echo.
    echo 程序异常退出
    pause
)