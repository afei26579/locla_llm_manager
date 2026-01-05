"""快速测试主题切换"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ui.app import MainWindow
from core.logger import get_logger

logger = get_logger('test')

app = QApplication.instance() or QApplication(sys.argv)
window = MainWindow()
window.show()

logger.info("=" * 60)
logger.info("快速测试 - 请切换主题并观察日志输出")
logger.info("=" * 60)

# 5秒后自动切换到设置页面
def go_to_settings():
    logger.info("自动切换到设置页面...")
    window.show_settings()

QTimer.singleShot(2000, go_to_settings)

sys.exit(app.exec())
