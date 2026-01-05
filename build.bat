@echo off
chcp 65001 >nul
echo ============================================================
echo 本地大模型助手 - 打包脚本
echo ============================================================
echo.

REM 检查是否在虚拟环境中
if not defined VIRTUAL_ENV (
    echo [警告] 未检测到虚拟环境
    echo 建议在虚拟环境中打包以减小体积
    echo.
    set /p continue="是否继续？(Y/N): "
    if /i not "%continue%"=="Y" exit /b
)

REM 检查 PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] 未安装 PyInstaller
    echo 正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo 安装失败，请手动安装: pip install pyinstaller
        pause
        exit /b 1
    )
)

REM 检查启动资源
if not exist "splash.png" (
    echo [提示] 未找到启动画面，正在创建...
    python create_splash.py
    if errorlevel 1 (
        echo 创建失败，将使用默认配置
    )
)

if not exist "icon.ico" (
    echo [警告] 未找到图标文件 icon.ico
    echo 将使用默认图标
)

echo.
echo ============================================================
echo 开始打包...
echo ============================================================
echo.

REM 清理旧文件
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM 执行打包
python build_config.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 打包完成！
echo ============================================================
echo.
echo 可执行文件位置: dist\本地大模型助手.exe
echo.

REM 询问是否运行
set /p run="是否运行测试？(Y/N): "
if /i "%run%"=="Y" (
    echo 正在启动...
    start "" "dist\本地大模型助手.exe"
)

pause
