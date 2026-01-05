#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""推荐选项按钮组件"""

from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from .themes import get_theme_manager


class SuggestionButton(QPushButton):
    """场景/推荐选项按钮"""
    clicked_with_text = Signal(str)
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.suggestion_text = text
        self.theme = get_theme_manager()
        
        self.setFont(QFont("Microsoft YaHei UI", 11))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        
        self.clicked.connect(lambda: self.clicked_with_text.emit(self.suggestion_text))
        self.apply_style()
        
        # 连接主题变更
        self.theme.theme_changed.connect(self.apply_style)
    
    def apply_style(self):
        """应用主题样式"""
        c = self.theme.colors
        
        # 提取 RGB
        accent = c['accent']
        try:
            r = int(accent[1:3], 16)
            g = int(accent[3:5], 16)
            b = int(accent[5:7], 16)
        except:
            r, g, b = 0, 122, 255  # 默认蓝色
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({r}, {g}, {b}, 0.1),
                    stop:1 rgba({r}, {g}, {b}, 0.2)
                );
                border: 2px solid {c['accent']};
                border-radius: 20px;
                padding: 10px 20px;
                color: {c['text']};
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({r}, {g}, {b}, 0.25),
                    stop:1 rgba({r}, {g}, {b}, 0.35)
                );
                border-color: {c['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {c['accent']};
                color: white;
            }}
        """)


class SuggestionButtonGroup(QWidget):
    """按钮组容器（横向排列，自动换行）"""
    button_clicked = Signal(str)
    
    def __init__(self, suggestions: list, parent=None):
        super().__init__(parent)
        self.theme = get_theme_manager()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        for text in suggestions:
            btn = SuggestionButton(text, self)
            btn.clicked_with_text.connect(self.button_clicked.emit)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # 应用背景色
        self.apply_style()
        self.theme.theme_changed.connect(self.apply_style)
    
    def apply_style(self):
        """应用主题样式"""
        c = self.theme.colors
        self.setStyleSheet(f"background-color: transparent;")
