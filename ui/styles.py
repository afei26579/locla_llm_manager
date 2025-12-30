"""Mac 风格样式定义"""

# 颜色主题
COLORS = {
    'bg': '#1e1e1e',
    'sidebar': '#252526',
    'chat_bg': '#1e1e1e',
    'input_bg': '#2d2d2d',
    'card_bg': '#2d2d2d',
    'hover': '#3c3c3c',
    'accent': '#007AFF',
    'accent_hover': '#0056b3',
    'text': '#ffffff',
    'text_secondary': '#8e8e93',
    'text_dim': '#6e6e73',
    'border': '#3d3d3d',
    'user_bubble': '#007AFF',
    'ai_bubble': '#3a3a3c',
    'success': '#30d158',
    'warning': '#ff9f0a',
    'error': '#ff453a',
    'notification_bg': '#1c1c1e',
}

# 全局样式表
GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Microsoft YaHei UI', 'SF Pro Display', sans-serif;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {COLORS['bg']};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_dim']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    height: 0px;
}}

QPushButton {{
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:disabled {{
    opacity: 0.5;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px;
    background-color: {COLORS['input_bg']};
    color: {COLORS['text']};
    font-size: 14px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}

QComboBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    background-color: {COLORS['input_bg']};
    color: {COLORS['text']};
    font-size: 13px;
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['card_bg']};
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QLabel {{
    color: {COLORS['text']};
}}

QToolTip {{
    background-color: {COLORS['card_bg']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px;
}}
"""

# 侧边栏样式
SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background-color: {COLORS['sidebar']};
    border-right: 1px solid {COLORS['border']};
}}
"""

# 按钮样式
PRIMARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['accent']};
    color: {COLORS['text']};
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:pressed {{
    background-color: #004494;
}}
"""

SECONDARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['card_bg']};
    color: {COLORS['text']};
}}
QPushButton:hover {{
    background-color: {COLORS['hover']};
}}
"""

DANGER_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['error']};
    color: {COLORS['text']};
}}
QPushButton:hover {{
    background-color: #cc362e;
}}
"""

SUCCESS_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['success']};
    color: {COLORS['text']};
}}
QPushButton:hover {{
    background-color: #28a745;
}}
"""

# 历史记录项样式
HISTORY_ITEM_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: {COLORS['text']};
    text-align: left;
    padding: 12px 15px;
    border-radius: 8px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {COLORS['hover']};
}}
"""

HISTORY_ITEM_ACTIVE_STYLE = f"""
QPushButton {{
    background-color: {COLORS['hover']};
    color: {COLORS['text']};
    text-align: left;
    padding: 12px 15px;
    border-radius: 8px;
    font-size: 13px;
}}
"""

# 消息气泡样式
USER_BUBBLE_STYLE = f"""
QLabel {{
    background-color: {COLORS['user_bubble']};
    color: {COLORS['text']};
    border-radius: 15px;
    padding: 12px 16px;
    font-size: 14px;
}}
"""

AI_BUBBLE_STYLE = f"""
QLabel {{
    background-color: {COLORS['ai_bubble']};
    color: {COLORS['text']};
    border-radius: 15px;
    padding: 12px 16px;
    font-size: 14px;
}}
"""

# 卡片样式
CARD_STYLE = f"""
QFrame {{
    background-color: {COLORS['card_bg']};
    border-radius: 12px;
    padding: 20px;
}}
"""

# 通知栏样式
NOTIFICATION_STYLE = f"""
QWidget#notification {{
    background-color: {COLORS['notification_bg']};
    border-top: 1px solid {COLORS['border']};
}}
"""