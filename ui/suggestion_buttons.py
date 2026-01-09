#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""推荐选项按钮组件"""

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics

from .themes import get_theme_manager


class SuggestionButton(QPushButton):
    """场景/推荐选项按钮"""
    clicked_with_text = Signal(str)
    
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.full_text = text
        self.theme = get_theme_manager()
        
        self.setFont(QFont("Microsoft YaHei UI", 11))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(36)
        
        # 直接显示完整文字
        self.setText(text)
        self.setToolTip(text)
        
        # 根据文字长度自适应宽度
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.adjustSize()
        
        self.clicked.connect(lambda: self.clicked_with_text.emit(self.full_text))
        self.apply_style()
        
        # 连接主题变更
        self.theme.theme_changed.connect(self.apply_style)
    
    def apply_style(self):
        """应用主题样式"""
        c = self.theme.colors
        
        # 获取主题背景色作为按钮背景
        bg_color = c.get('bg_secondary', c.get('bg', '#1a1a2e'))
        accent = c['accent']
        
        # 提取 accent RGB 用于边框
        try:
            r = int(accent[1:3], 16)
            g = int(accent[3:5], 16)
            b = int(accent[5:7], 16)
        except:
            r, g, b = 0, 122, 255  # 默认蓝色
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid rgba({r}, {g}, {b}, 0.5);
                border-radius: 18px;
                padding: 8px 20px;
                color: {c['text']};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {c.get('bg_tertiary', bg_color)};
                border-color: {c['accent']};
            }}
            QPushButton:pressed {{
                background-color: {c['accent']};
                color: white;
            }}
        """)


class SuggestionButtonGroup(QWidget):
    """按钮组容器（每行一个，垂直排列，左对齐）"""
    button_clicked = Signal(str)
    
    def __init__(self, suggestions: list, parent=None):
        super().__init__(parent)
        self.theme = get_theme_manager()
        self.suggestions = suggestions[:3]  # 最多显示3个
        self.buttons = []
        
        # 主布局（垂直）
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 10, 20, 10)
        self.main_layout.setSpacing(8)
        self.main_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        
        # 创建按钮并布局
        self._create_buttons()
        
        self.apply_style()
        self.theme.theme_changed.connect(self.apply_style)
    
    def _create_buttons(self):
        """创建按钮，每行一个，自适应宽度"""
        # 清除旧布局
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.buttons = []
        
        for text in self.suggestions:
            # 用水平布局包裹按钮，实现左对齐
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setAlignment(Qt.AlignLeft)
            
            btn = SuggestionButton(text, self)
            btn.clicked_with_text.connect(self.button_clicked.emit)
            self.buttons.append(btn)
            
            row.addWidget(btn)
            row.addStretch()  # 右侧弹性空间
            self.main_layout.addLayout(row)
    
    def apply_style(self):
        """应用主题样式"""
        self.setStyleSheet("background-color: transparent;")


class SuggestionLoadingWidget(QWidget):
    """推荐选项加载中状态"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme_manager()
        self.setObjectName("suggestionLoading")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 加载提示
        self.label = QLabel("✨ 正在生成推荐回复...")
        self.label.setFont(QFont("Microsoft YaHei UI", 10))
        self.label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.label)
        
        # 动画效果
        self.dot_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(500)
        
        self.apply_style()
        self.theme.theme_changed.connect(self.apply_style)
    
    def _animate(self):
        """动画效果"""
        dots = "." * (self.dot_count % 4)
        self.label.setText(f"✨ 正在生成推荐回复{dots}")
        self.dot_count += 1
    
    def apply_style(self):
        """应用主题样式"""
        c = self.theme.colors
        self.label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
        self.setStyleSheet("background-color: transparent;")
    
    def stop(self):
        """停止动画"""
        self.timer.stop()
