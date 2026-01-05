"""主题管理 - 兼容层

此文件保留用于向后兼容，实际主题管理已迁移到 core.theme 模块
"""

from PySide6.QtCore import QObject, Signal
import json
import os

# 导入新的主题管理器
try:
    from core.theme import get_theme_manager as _get_new_theme_manager
    _USE_NEW_THEME_SYSTEM = True
except ImportError:
    _USE_NEW_THEME_SYSTEM = False
    print("警告: 无法导入新主题系统，使用旧版主题")

# 深色主题（兼容旧代码）
DARK_THEME = {
    'name': 'dark',
    'display_name': '深色',
    'bg': '#1e1e1e',
    'bg_secondary': '#252526',
    'bg_tertiary': '#2d2d2d',
    'card_bg': '#2d2d2d',
    'input_bg': '#3c3c3c',
    'hover': '#3c3c3c',
    'active': '#454545',
    'border': '#3d3d3d',
    'accent': '#007AFF',
    'accent_hover': '#0056b3',
    'accent_light': '#0a84ff',
    'text': '#e8e8e8',
    'text_secondary': '#b0b0b0',
    'text_dim': '#909090',
    'user_bubble': '#007AFF',
    'ai_bubble': '#3a3a3c',
    'think_bubble': '#2a2a3c',  # 思考气泡背景色（深色偏紫）
    'success': '#30d158',
    'warning': '#ff9f0a',
    'error': '#ff453a',
    'scrollbar': '#4a4a4a',
    'scrollbar_hover': '#5a5a5a',
    'sidebar_bg': '#252526',
    'notification_bg': '#1c1c1e',
    'settings_nav_bg': '#1c1c1e',
    'settings_nav_active': '#2d2d2d',
    'progress_bg': '#3a3a3c',
    'progress_fill': '#007AFF',
    'info_row_bg': '#353535',
}

# 浅色主题（兼容旧代码）
LIGHT_THEME = {
    'name': 'light',
    'display_name': '浅色',
    'bg': '#f5f5f7',
    'bg_secondary': '#ffffff',
    'bg_tertiary': '#e8e8ed',
    'card_bg': '#ffffff',
    'input_bg': '#ffffff',
    'hover': '#e8e8ed',
    'active': '#d1d1d6',
    'border': '#c7c7cc',
    'accent': '#007AFF',
    'accent_hover': '#0056b3',
    'accent_light': '#40a9ff',
    'text': '#1d1d1f',
    'text_secondary': '#48484a',
    'text_dim': '#6e6e73',
    'user_bubble': '#007AFF',
    'ai_bubble': '#e8e8ed',
    'think_bubble': '#f0f0f8',  # 思考气泡背景色（浅色偏紫）
    'success': '#28a745',
    'warning': '#fd7e14',
    'error': '#dc3545',
    'scrollbar': '#c7c7cc',
    'scrollbar_hover': '#a9a9ae',
    'sidebar_bg': '#ffffff',
    'notification_bg': '#ffffff',
    'settings_nav_bg': '#e8e8ed',
    'settings_nav_active': '#ffffff',
    'progress_bg': '#e8e8ed',
    'progress_fill': '#007AFF',
    'info_row_bg': '#f0f0f5',
}

THEMES = {
    'dark': DARK_THEME,
    'light': LIGHT_THEME,
}


class ThemeManager(QObject):
    """主题管理器（兼容层）
    
    此类保留用于向后兼容，实际功能委托给新的主题系统
    """
    
    theme_changed = Signal(dict)
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        
        # 使用新主题系统
        if _USE_NEW_THEME_SYSTEM:
            self._new_manager = _get_new_theme_manager()
            # 连接新管理器的信号
            self._new_manager.theme_changed.connect(self._on_new_theme_changed)
        else:
            self._current_theme = DARK_THEME
            self._load_config()
    
    def _on_new_theme_changed(self, theme_data):
        """新主题系统的主题变更回调"""
        # 发出兼容的信号
        self.theme_changed.emit(theme_data)
    
    def _load_config(self):
        """加载配置（旧系统）"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    theme_name = config.get('theme', 'dark')
                    self._current_theme = THEMES.get(theme_name, DARK_THEME)
            except:
                pass
    
    def _get_config_path(self):
        """获取配置文件路径"""
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'config.json')
    
    @property
    def current(self) -> dict:
        """获取当前主题"""
        if _USE_NEW_THEME_SYSTEM:
            return self._new_manager.current
        return self._current_theme
    
    @property
    def colors(self) -> dict:
        """获取当前主题颜色"""
        if _USE_NEW_THEME_SYSTEM:
            return self._new_manager.colors
        return self._current_theme
    
    def set_theme(self, theme_name: str):
        """设置主题"""
        if _USE_NEW_THEME_SYSTEM:
            self._new_manager.set_theme(theme_name)
        else:
            if theme_name in THEMES:
                self._current_theme = THEMES[theme_name]
                self.theme_changed.emit(self._current_theme)
    
    def toggle_theme(self):
        """切换主题"""
        if _USE_NEW_THEME_SYSTEM:
            self._new_manager.toggle_theme()
        else:
            if self._current_theme['name'] == 'dark':
                self.set_theme('light')
            else:
                self.set_theme('dark')
    
    def get_available_themes(self) -> list:
        """获取可用主题列表"""
        if _USE_NEW_THEME_SYSTEM:
            return self._new_manager.get_available_themes()
        return [(k, v['display_name']) for k, v in THEMES.items()]


def get_theme_manager() -> ThemeManager:
    """获取主题管理器实例"""
    return ThemeManager()


def get_stylesheet(theme: dict = None) -> str:
    """生成样式表（兼容层）
    
    优先使用新主题系统生成样式表，如果不可用则使用旧方法
    """
    if _USE_NEW_THEME_SYSTEM:
        manager = _get_new_theme_manager()
        return manager.get_stylesheet()
    
    # 旧的样式表生成逻辑（保留作为后备）
    if theme is None:
        theme = get_theme_manager().current
    
    c = theme
    
    return f"""
    /* 全局样式 */
    QMainWindow, QWidget {{
        background-color: {c['bg']};
        color: {c['text']};
        font-family: 'Microsoft YaHei UI', 'SF Pro Display', -apple-system, sans-serif;
        font-size: 13px;
    }}
    
    /* 滚动区域 */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    /* 滚动条 */
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar']};
        border-radius: 4px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        height: 0;
        background: none;
    }}
    
    QScrollBar:horizontal {{
        height: 0;
    }}
    
    /* 按钮 */
    QPushButton {{
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
        background-color: {c['bg_tertiary']};
        color: {c['text']};
    }}
    
    QPushButton:hover {{
        background-color: {c['hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {c['active']};
    }}
    
    QPushButton:disabled {{
        opacity: 0.5;
        color: {c['text_dim']};
    }}
    
    /* 输入框 */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 10px;
        background-color: {c['input_bg']};
        color: {c['text']};
        font-size: 14px;
        selection-background-color: {c['accent']};
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {c['accent']};
    }}
    
    /* 下拉框 */
    QComboBox {{
        border: 2px solid {c['border']};
        border-radius: 10px;
        padding: 8px 15px;
        padding-right: 35px;
        background-color: {c['input_bg']};
        color: {c['text']};
        font-size: 13px;
        min-height: 20px;
    }}
    
    QComboBox:hover {{
        border-color: {c['accent']};
        background-color: {c['hover']};
    }}
    
    QComboBox:focus {{
        border-color: {c['accent']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 35px;
        padding-right: 5px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 7px solid {c['text_secondary']};
        margin-right: 8px;
    }}
    
    QComboBox::down-arrow:hover {{
        border-top-color: {c['accent']};
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {c['card_bg']};
        color: {c['text']};
        selection-background-color: {c['accent']};
        selection-color: white;
        border: 2px solid {c['border']};
        border-radius: 10px;
        padding: 6px;
        outline: none;
    }}
    
    QComboBox QAbstractItemView::item {{
        padding: 10px 15px;
        border-radius: 6px;
        margin: 2px 0;
    }}
    
    QComboBox QAbstractItemView::item:hover {{
        background-color: {c['hover']};
    }}
    
    QComboBox QAbstractItemView::item:selected {{
        background-color: {c['accent']};
        color: white;
    }}
    
    /* 进度条 */
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {c['progress_bg']};
        height: 8px;
        text-align: center;
    }}
    
    QProgressBar::chunk {{
        background-color: {c['progress_fill']};
        border-radius: 4px;
    }}
    
    /* 标签 */
    QLabel {{
        color: {c['text']};
        background-color: transparent;
    }}
    
    /* 提示框 */
    QToolTip {{
        background-color: {c['card_bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    
    /* 消息框 */
    QMessageBox {{
        background-color: {c['bg']};
    }}
    
    QMessageBox QLabel {{
        color: {c['text']};
    }}
    
    QMessageBox QPushButton {{
        min-width: 80px;
        padding: 8px 16px;
    }}
    """