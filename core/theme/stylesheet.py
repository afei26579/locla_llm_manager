"""样式表生成器

根据主题配置生成 Qt 样式表
"""

from typing import Dict, Any


class StylesheetGenerator:
    """样式表生成器"""
    
    def __init__(self):
        self._cache = {}
    
    def generate(self, theme_data: Dict[str, Any]) -> str:
        """生成完整样式表
        
        Args:
            theme_data: 主题数据
            
        Returns:
            Qt 样式表字符串
        """
        theme_name = theme_data.get('meta', {}).get('name', 'unknown')
        
        # 检查缓存
        if theme_name in self._cache:
            return self._cache[theme_name]
        
        # 提取颜色配置
        colors = theme_data.get('colors', {})
        typography = theme_data.get('typography', {})
        spacing = theme_data.get('spacing', {})
        radius = theme_data.get('radius', {})
        
        # 生成样式表
        stylesheet = self._generate_stylesheet(colors, typography, spacing, radius)
        
        # 缓存样式表
        self._cache[theme_name] = stylesheet
        return stylesheet
    
    def _generate_stylesheet(self, colors: Dict, typography: Dict, 
                            spacing: Dict, radius: Dict) -> str:
        """生成样式表内容"""
        
        # 提取常用颜色
        bg = colors.get('background', {})
        surface = colors.get('surface', {})
        border = colors.get('border', {})
        accent = colors.get('accent', {})
        text = colors.get('text', {})
        semantic = colors.get('semantic', {})
        scrollbar = colors.get('scrollbar', {})
        
        # 提取字体配置
        font_family = typography.get('font_family', 'Microsoft YaHei UI, sans-serif')
        font_size = typography.get('font_size', {})
        
        # 提取圆角配置
        radius_sm = radius.get('small', 6)
        radius_md = radius.get('medium', 10)
        radius_lg = radius.get('large', 16)
        
        return f"""
/* ==================== 全局样式 ==================== */
QMainWindow, QWidget {{
    background-color: {bg.get('primary', '#1e1e1e')};
    color: {text.get('primary', '#e8e8e8')};
    font-family: {font_family};
    font-size: {font_size.get('normal', 13)}px;
}}

/* ==================== 按钮样式 ==================== */
QPushButton {{
    border: none;
    border-radius: {radius_md}px;
    padding: 10px 20px;
    font-size: {font_size.get('normal', 13)}px;
    font-weight: 500;
    background-color: {surface.get('card', '#2d2d2d')};
    color: {text.get('primary', '#e8e8e8')};
}}

QPushButton:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QPushButton:pressed {{
    background-color: {surface.get('active', '#454545')};
}}

QPushButton:disabled {{
    opacity: 0.5;
    color: {text.get('dim', '#909090')};
}}

/* 主要按钮 */
QPushButton[primary="true"] {{
    background-color: {accent.get('primary', '#007AFF')};
    color: white;
    font-weight: 600;
}}

QPushButton[primary="true"]:hover {{
    background-color: {accent.get('hover', '#0056b3')};
}}

/* 危险按钮 */
QPushButton[danger="true"] {{
    background-color: {semantic.get('error', '#ff453a')};
    color: white;
}}

QPushButton[danger="true"]:hover {{
    background-color: #c82333;
}}

/* ==================== 输入框样式 ==================== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    border: 2px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    padding: 10px 12px;
    background-color: {surface.get('input', '#3c3c3c')};
    color: {text.get('primary', '#e8e8e8')};
    font-size: {font_size.get('normal', 13)}px;
    selection-background-color: {accent.get('primary', '#007AFF')};
    selection-color: #ffffff;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {accent.get('primary', '#007AFF')};
}}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {text.get('dim', '#909090')};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {bg.get('secondary', '#252526')};
    color: {text.get('dim', '#909090')};
}}

QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
    color: {text.get('placeholder', '#707070')};
}}

/* ==================== 下拉框样式 ==================== */
QComboBox {{
    border: 2px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    padding: 8px 15px;
    padding-right: 35px;
    background-color: {surface.get('input', '#3c3c3c')};
    color: {text.get('primary', '#e8e8e8')};
    font-size: {font_size.get('normal', 13)}px;
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {accent.get('primary', '#007AFF')};
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QComboBox:focus {{
    border-color: {accent.get('primary', '#007AFF')};
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
    border-top: 7px solid {text.get('secondary', '#b0b0b0')};
    margin-right: 8px;
}}

QComboBox::down-arrow:hover {{
    border-top-color: {accent.get('primary', '#007AFF')};
}}

QComboBox QAbstractItemView {{
    background-color: {surface.get('card', '#2d2d2d')};
    color: {text.get('primary', '#e8e8e8')};
    selection-background-color: {accent.get('primary', '#007AFF')};
    selection-color: white;
    border: 2px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    padding: 6px;
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 10px 15px;
    border-radius: {radius_sm}px;
    margin: 2px 0;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {accent.get('primary', '#007AFF')};
    color: white;
}}

/* ==================== 复选框样式 ==================== */
QCheckBox {{
    spacing: 8px;
    color: {text.get('primary', '#e8e8e8')};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {border.get('default', '#3d3d3d')};
    background-color: {surface.get('input', '#3c3c3c')};
}}

QCheckBox::indicator:hover {{
    border-color: {accent.get('primary', '#007AFF')};
}}

QCheckBox::indicator:checked {{
    background-color: {accent.get('primary', '#007AFF')};
    border-color: {accent.get('primary', '#007AFF')};
    image: none;
}}

/* ==================== 单选框样式 ==================== */
QRadioButton {{
    spacing: 8px;
    color: {text.get('primary', '#e8e8e8')};
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid {border.get('default', '#3d3d3d')};
    background-color: {surface.get('input', '#3c3c3c')};
}}

QRadioButton::indicator:hover {{
    border-color: {accent.get('primary', '#007AFF')};
}}

QRadioButton::indicator:checked {{
    background-color: {accent.get('primary', '#007AFF')};
    border-color: {accent.get('primary', '#007AFF')};
}}

/* ==================== 滑块样式 ==================== */
QSlider::groove:horizontal {{
    height: 6px;
    background: {surface.get('input', '#3c3c3c')};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    background: {accent.get('primary', '#007AFF')};
}}

QSlider::handle:horizontal:hover {{
    background: {accent.get('hover', '#0056b3')};
}}

/* ==================== 进度条样式 ==================== */
QProgressBar {{
    border: none;
    border-radius: 4px;
    background-color: {surface.get('input', '#3c3c3c')};
    height: 8px;
    text-align: center;
    color: {text.get('primary', '#e8e8e8')};
}}

QProgressBar::chunk {{
    background-color: {accent.get('primary', '#007AFF')};
    border-radius: 4px;
}}

/* ==================== 标签页样式 ==================== */
QTabWidget::pane {{
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    background-color: {surface.get('card', '#2d2d2d')};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {bg.get('secondary', '#252526')};
    color: {text.get('secondary', '#b0b0b0')};
    padding: 10px 20px;
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-bottom: none;
    border-top-left-radius: {radius_md}px;
    border-top-right-radius: {radius_md}px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
    color: {text.get('primary', '#e8e8e8')};
}}

QTabBar::tab:selected {{
    background-color: {surface.get('card', '#2d2d2d')};
    color: {accent.get('primary', '#007AFF')};
    font-weight: 600;
}}

QTabBar::tab:!selected {{
    margin-top: 2px;
}}

/* ==================== 滚动条样式 ==================== */
/* 垂直滚动条 */
QScrollBar:vertical {{
    background-color: {scrollbar.get('track', 'transparent')};
    width: 10px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background-color: {scrollbar.get('thumb', '#4a4a4a')};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {scrollbar.get('thumb_hover', '#5a5a5a')};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}

/* 水平滚动条 */
QScrollBar:horizontal {{
    background-color: {scrollbar.get('track', 'transparent')};
    height: 10px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background-color: {scrollbar.get('thumb', '#4a4a4a')};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {scrollbar.get('thumb_hover', '#5a5a5a')};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ==================== 滚动区域样式 ==================== */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* ==================== 分组框样式 ==================== */
QGroupBox {{
    border: 2px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: {text.get('primary', '#e8e8e8')};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: {bg.get('primary', '#1e1e1e')};
}}

/* ==================== 分隔线样式 ==================== */
QFrame[frameShape="4"], /* HLine */
QFrame[frameShape="5"]  /* VLine */
{{
    background-color: {border.get('default', '#3d3d3d')};
    border: none;
}}

/* ==================== 标签样式 ==================== */
QLabel {{
    color: {text.get('primary', '#e8e8e8')};
    background-color: transparent;
}}

QLabel[secondary="true"] {{
    color: {text.get('secondary', '#b0b0b0')};
}}

QLabel[dim="true"] {{
    color: {text.get('dim', '#909090')};
}}

/* ==================== 工具提示样式 ==================== */
QToolTip {{
    background-color: {surface.get('card', '#2d2d2d')};
    color: {text.get('primary', '#e8e8e8')};
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_sm}px;
    padding: 6px 10px;
}}

/* ==================== 菜单样式 ==================== */
QMenu {{
    background-color: {surface.get('card', '#2d2d2d')};
    color: {text.get('primary', '#e8e8e8')};
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    padding: 8px;
}}

QMenu::item {{
    padding: 10px 20px;
    border-radius: {radius_sm}px;
}}

QMenu::item:selected {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QMenu::separator {{
    height: 1px;
    background-color: {border.get('default', '#3d3d3d')};
    margin: 6px 10px;
}}

/* ==================== 对话框样式 ==================== */
QDialog {{
    background-color: {bg.get('primary', '#1e1e1e')};
}}

QMessageBox {{
    background-color: {bg.get('primary', '#1e1e1e')};
}}

QMessageBox QLabel {{
    color: {text.get('primary', '#e8e8e8')};
}}

QMessageBox QPushButton {{
    min-width: 80px;
    padding: 8px 16px;
}}

/* ==================== 列表视图样式 ==================== */
QListView {{
    background-color: {surface.get('card', '#2d2d2d')};
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    color: {text.get('primary', '#e8e8e8')};
    outline: none;
}}

QListView::item {{
    padding: 8px;
    border-radius: {radius_sm}px;
}}

QListView::item:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QListView::item:selected {{
    background-color: {accent.get('primary', '#007AFF')};
    color: white;
}}

/* ==================== 树形视图样式 ==================== */
QTreeView {{
    background-color: {surface.get('card', '#2d2d2d')};
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    color: {text.get('primary', '#e8e8e8')};
    outline: none;
}}

QTreeView::item {{
    padding: 6px;
}}

QTreeView::item:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QTreeView::item:selected {{
    background-color: {accent.get('primary', '#007AFF')};
    color: white;
}}

/* ==================== 表格视图样式 ==================== */
QTableView {{
    background-color: {surface.get('card', '#2d2d2d')};
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    color: {text.get('primary', '#e8e8e8')};
    gridline-color: {border.get('default', '#3d3d3d')};
    outline: none;
}}

QTableView::item {{
    padding: 6px;
}}

QTableView::item:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QTableView::item:selected {{
    background-color: {accent.get('primary', '#007AFF')};
    color: white;
}}

QHeaderView::section {{
    background-color: {bg.get('secondary', '#252526')};
    color: {text.get('primary', '#e8e8e8')};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {border.get('default', '#3d3d3d')};
    font-weight: 600;
}}

/* ==================== 数字输入框样式 ==================== */
QSpinBox, QDoubleSpinBox {{
    background-color: {surface.get('input', '#3c3c3c')};
    border: 2px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    padding: 6px 10px;
    color: {text.get('primary', '#e8e8e8')};
    font-size: {font_size.get('normal', 13)}px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {accent.get('primary', '#007AFF')};
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {text.get('dim', '#909090')};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {border.get('default', '#3d3d3d')};
    border-top-right-radius: {radius_md}px;
    background-color: {bg.get('secondary', '#252526')};
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid {border.get('default', '#3d3d3d')};
    border-bottom-right-radius: {radius_md}px;
    background-color: {bg.get('secondary', '#252526')};
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {text.get('primary', '#e8e8e8')};
    width: 0px;
    height: 0px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text.get('primary', '#e8e8e8')};
    width: 0px;
    height: 0px;
}}

/* ==================== 日期时间选择器样式 ==================== */
QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {surface.get('input', '#3c3c3c')};
    border: 2px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_md}px;
    padding: 6px 10px;
    color: {text.get('primary', '#e8e8e8')};
}}

QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
    border-color: {accent.get('primary', '#007AFF')};
}}

QCalendarWidget {{
    background-color: {surface.get('card', '#2d2d2d')};
    color: {text.get('primary', '#e8e8e8')};
}}

/* ==================== 状态栏样式 ==================== */
QStatusBar {{
    background-color: {bg.get('secondary', '#252526')};
    color: {text.get('secondary', '#b0b0b0')};
    border-top: 1px solid {border.get('default', '#3d3d3d')};
}}

/* ==================== 工具栏样式 ==================== */
QToolBar {{
    background-color: {bg.get('secondary', '#252526')};
    border: none;
    spacing: 4px;
    padding: 4px;
}}

QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: {radius_sm}px;
    padding: 6px;
    color: {text.get('primary', '#e8e8e8')};
}}

QToolButton:hover {{
    background-color: {surface.get('hover', '#3c3c3c')};
}}

QToolButton:pressed {{
    background-color: {surface.get('active', '#454545')};
}}

/* ==================== 停靠窗口样式 ==================== */
QDockWidget {{
    color: {text.get('primary', '#e8e8e8')};
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}

QDockWidget::title {{
    background-color: {bg.get('secondary', '#252526')};
    padding: 6px;
    border: 1px solid {border.get('default', '#3d3d3d')};
}}

/* ==================== 自定义卡片样式 ==================== */
QFrame[card="true"] {{
    background-color: {surface.get('card', '#2d2d2d')};
    border: 1px solid {border.get('default', '#3d3d3d')};
    border-radius: {radius_lg}px;
}}
"""
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
