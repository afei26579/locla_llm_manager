#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本地大模型助手"""

import sys
import os
import traceback

# 支持 PyInstaller 启动画面
try:
    import pyi_splash
    # 更新启动画面文字
    pyi_splash.update_text('正在初始化...')
except ImportError:
    pyi_splash = None

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 初始化日志系统（最优先）
from core.logger import get_logger
logger = get_logger('main')

try:
    logger.info("应用启动开始")
    
    # 更新启动画面
    if pyi_splash:
        pyi_splash.update_text('正在加载配置...')
    
    # 首次启动时自动初始化（导入模型和人格配置）
    logger.info("开始执行初始化检查...")
    from core.initialization import auto_initialize_on_startup
    auto_initialize_on_startup()
    
    # 首次启动时自动迁移数据（从旧的 JSON 格式）
    logger.info("开始执行数据迁移检查...")
    from core.migration import auto_migrate_on_startup
    auto_migrate_on_startup()
    
    # 更新启动画面
    if pyi_splash:
        pyi_splash.update_text('正在启动应用...')
    
    logger.info("开始加载主界面...")
    from ui.app import main
    
    if __name__ == "__main__":
        # 关闭启动画面
        if pyi_splash:
            pyi_splash.close()
        
        logger.info("进入主程序")
        main()

except Exception as e:
    error_msg = f"应用启动失败: {e}\n{traceback.format_exc()}"
    logger.critical(error_msg)
    
    # 关闭启动画面
    if pyi_splash:
        try:
            pyi_splash.close()
        except:
            pass
    
    # 显示错误对话框
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "启动失败",
            f"应用启动时发生错误:\n\n{e}\n\n详细信息已保存到 logs 目录"
        )
    except:
        print(error_msg)
    
    sys.exit(1)