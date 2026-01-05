"""
PyInstaller 打包配置文件

使用方法：
1. 准备图标和启动画面：
   - icon.ico (应用图标)
   - splash.png (启动画面，建议 400x300 或 600x400)

2. 安装依赖：
   pip install pyinstaller

3. 执行打包：
   python build_config.py
"""

import PyInstaller.__main__
import os
import sys

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置参数
APP_NAME = "本地大模型助手"
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")  # 应用图标
SPLASH_PATH = os.path.join(BASE_DIR, "splash.png")  # 启动画面

# 需要包含的数据文件
datas = [
    (os.path.join(BASE_DIR, "themes"), "themes"),  # 主题配置
    (os.path.join(BASE_DIR, "config.json"), "."),  # 配置文件
    (os.path.join(BASE_DIR, "models.json"), "."),  # 模型配置（首次运行导入）
    (os.path.join(BASE_DIR, "icon.ico"), "."),  # 应用图标（运行时使用）
]

# 可选：如果有 personas.json，也打包进去
personas_file = os.path.join(BASE_DIR, "personas.json")
if os.path.exists(personas_file):
    datas.append((personas_file, "."))
    print("包含 personas.json")

# 需要包含的隐藏导入
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'sqlite3',
    'json',
    'requests',
    'PIL',
    'modelscope',  # ModelScope SDK（用于下载模型）
    'modelscope.hub',
    'modelscope.hub.snapshot_download',
]

# PyInstaller 参数
pyinstaller_args = [
    'main.py',  # 主程序入口
    '--name', APP_NAME,  # 应用名称
    '--onefile',  # 打包成单个文件
    '--windowed',  # 无控制台窗口
    '--clean',  # 清理临时文件
    
    # 图标
    '--icon', ICON_PATH if os.path.exists(ICON_PATH) else 'NONE',
    
    # 启动画面
    '--splash', SPLASH_PATH if os.path.exists(SPLASH_PATH) else 'NONE',
    
    # 优化选项
    '--optimize', '2',  # 字节码优化级别
    '--log-level', 'WARN',  # 只显示警告和错误，减少输出
    
    # 输出目录
    '--distpath', os.path.join(BASE_DIR, 'dist'),
    '--workpath', os.path.join(BASE_DIR, 'build'),
    '--specpath', os.path.join(BASE_DIR, 'build'),
]

# 添加数据文件
for src, dst in datas:
    if os.path.exists(src):
        pyinstaller_args.extend(['--add-data', f'{src};{dst}'])

# 添加隐藏导入
for module in hiddenimports:
    pyinstaller_args.extend(['--hidden-import', module])

# 执行打包
if __name__ == '__main__':
    print("=" * 60)
    print("开始打包应用程序")
    print("=" * 60)
    print(f"应用名称: {APP_NAME}")
    print(f"图标文件: {ICON_PATH if os.path.exists(ICON_PATH) else '未设置'}")
    print(f"启动画面: {SPLASH_PATH if os.path.exists(SPLASH_PATH) else '未设置'}")
    print("=" * 60)
    
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\n" + "=" * 60)
    print("打包完成！")
    print(f"可执行文件位置: {os.path.join(BASE_DIR, 'dist', APP_NAME + '.exe')}")
    print("=" * 60)
