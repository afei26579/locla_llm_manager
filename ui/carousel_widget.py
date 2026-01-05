#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""3D 旋转木马组件"""

import math
import os
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QTransform

from .themes import get_theme_manager


class CarouselCard(QPushButton):
    """旋转木马卡片 - 方案2：渐变背景风格"""
    
    def __init__(self, key: str, persona: dict, parent=None):
        super().__init__(parent)
        self.key = key
        self.persona = persona
        self.scale_factor = 1.0
        self.opacity_value = 1.0
        self.z_order = 0
        self.theme = get_theme_manager()
        
        # 初始尺寸（会在 set_transform 中动态调整）
        self.setFixedSize(160, 220)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        # 使用绝对定位
        from PySide6.QtWidgets import QLabel
        
        # 头像区域 - 填满边框内部（不留内边距），利用边框圆角裁剪
        self.icon_label = QLabel(self)
        self.icon_label.setGeometry(0, 0, 160, 180)  # 完全填满上方区域
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setScaledContents(True)  # 让图片自动填满 label
        
        icon_path = self.persona.get("icon_path", "")
        if icon_path:
            from core.media_manager import get_media_manager
            media_manager = get_media_manager()
            abs_path = media_manager.get_absolute_path(icon_path)
            
            if os.path.exists(abs_path):
                pixmap = QPixmap(abs_path)
                if not pixmap.isNull():
                    # 横向填满，保持比例，裁剪超出部分
                    scaled_pixmap = pixmap.scaled(
                        160, 180,  # 卡片头像区域尺寸
                        Qt.KeepAspectRatioByExpanding,  # 填满区域，保持比例
                        Qt.SmoothTransformation
                    )
                    # 从中心裁剪到目标尺寸
                    if scaled_pixmap.width() > 160 or scaled_pixmap.height() > 180:
                        x_offset = max(0, (scaled_pixmap.width() - 160) // 2)
                        y_offset = max(0, (scaled_pixmap.height() - 180) // 2)
                        scaled_pixmap = scaled_pixmap.copy(x_offset, y_offset, 160, 180)
                    self.icon_label.setPixmap(scaled_pixmap)
                    self.icon_label.setScaledContents(False)  # 已裁剪好，不需要拉伸
                else:
                    self.icon_label.setScaledContents(False)
                    self.icon_label.setText(self.persona.get("icon", "🤖"))
                    self.icon_label.setFont(QFont("Segoe UI Emoji", 72))
            else:
                self.icon_label.setScaledContents(False)
                self.icon_label.setText(self.persona.get("icon", "🤖"))
                self.icon_label.setFont(QFont("Segoe UI Emoji", 72))
        else:
            self.icon_label.setScaledContents(False)
            self.icon_label.setText(self.persona.get("icon", "🤖"))
            self.icon_label.setFont(QFont("Segoe UI Emoji", 72))
        
        # 名称区域 - 下方40px，完全填满
        self.name_container = QLabel(self)
        self.name_container.setGeometry(0, 180, 160, 40)
        
        # 名称标签
        self.name_label = QLabel(self.persona.get("name", "未知"), self)
        self.name_label.setGeometry(5, 185, 150, 30)
        self.name_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        
        # 确保层级顺序
        self.icon_label.lower()
        self.name_container.raise_()
        self.name_label.raise_()
    
    def set_transform(self, scale: float, opacity: float, z_order: int, is_center: bool = False):
        """设置变换效果"""
        self.scale_factor = scale
        self.opacity_value = opacity
        self.z_order = z_order
        
        c = self.theme.colors
        
        # 获取父组件的基础尺寸
        parent_widget = self.parent()
        if isinstance(parent_widget, CarouselWidget):
            base_width = parent_widget.base_card_width
            base_height = parent_widget.base_card_height
        else:
            base_width = 160
            base_height = 220
        
        # 更新大小
        new_width = int(base_width * scale)
        new_height = int(base_height * scale)
        self.setFixedSize(new_width, new_height)
        
        # 更新子组件大小和位置（图片填满边框内部）
        icon_height = int((base_height * 180 / 220) * scale)
        icon_width = new_width
        
        # 图片区域完全填满，不留内边距
        self.icon_label.setGeometry(0, 0, icon_width, icon_height)
        
        name_height = int((base_height * 40 / 220) * scale)
        self.name_container.setGeometry(0, icon_height, new_width, name_height)
        
        self.name_label.setGeometry(
            int(5 * scale),
            icon_height + int(5 * scale),
            new_width - int(10 * scale),
            name_height - int(10 * scale)
        )
        
        # 中心卡片特殊样式
        if is_center:
            # 卡片边框
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['card_bg']};
                    border: 3px solid {c['accent']};
                    border-radius: 20px;
                }}
                QPushButton:hover {{
                    border-color: {c['accent_hover']};
                }}
            """)
            
            # 头像区域背景 + 顶部圆角（圆角值需要减去边框宽度）
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {c['card_bg']};
                    border-top-left-radius: 17px;
                    border-top-right-radius: 17px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    padding: 0px;
                }}
            """)
            
            # 名称区域渐变背景（主题色渐变）+ 底部圆角
            self.name_container.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c['accent']},
                        stop:1 {c['accent_hover']}
                    );
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 17px;
                    border-bottom-right-radius: 17px;
                }}
            """)
            
            # 名称文字（白色）
            self.name_label.setStyleSheet("""
                QLabel {
                    color: white;
                    background: transparent;
                }
            """)
        else:
            # 非中心卡片
            border_opacity = int(opacity * 150)
            
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['card_bg']};
                    border: 2px solid rgba(150, 150, 150, {border_opacity});
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    border-color: {c['accent']};
                }}
            """)
            
            # 头像区域背景 + 顶部圆角
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {c['card_bg']};
                    border-top-left-radius: 16px;
                    border-top-right-radius: 16px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    padding: 0px;
                }}
            """)
            
            # 名称区域渐变背景（较淡的渐变）+ 底部圆角
            accent_r = int(c['accent'][1:3], 16) if c['accent'].startswith('#') else 0
            accent_g = int(c['accent'][3:5], 16) if c['accent'].startswith('#') else 122
            accent_b = int(c['accent'][5:7], 16) if c['accent'].startswith('#') else 255
            
            self.name_container.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba({accent_r}, {accent_g}, {accent_b}, {int(180 * opacity)}),
                        stop:1 rgba({accent_r}, {accent_g}, {accent_b}, {int(220 * opacity)})
                    );
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 16px;
                    border-bottom-right-radius: 16px;
                }}
            """)
            
            # 名称文字（白色，稍淡）
            text_opacity = max(0.7, opacity)
            self.name_label.setStyleSheet(f"""
                QLabel {{
                    color: rgba(255, 255, 255, {int(text_opacity * 255)});
                    background: transparent;
                }}
            """)
        
        # 更新字体大小
        icon_size = int(72 * scale)  # 调整为72，因为有内边距
        name_size = max(9, int(12 * scale))
        
        if not self.icon_label.pixmap():
            self.icon_label.setFont(QFont("Segoe UI Emoji", icon_size))
        else:
            # 重新缩放图片（填满区域，保持比例）
            icon_path = self.persona.get("icon_path", "")
            if icon_path:
                from core.media_manager import get_media_manager
                media_manager = get_media_manager()
                abs_path = media_manager.get_absolute_path(icon_path)
                
                if os.path.exists(abs_path):
                    pixmap = QPixmap(abs_path)
                    if not pixmap.isNull():
                        # 横向填满，保持比例
                        scaled_pixmap = pixmap.scaled(
                            icon_width, icon_height,
                            Qt.KeepAspectRatioByExpanding,  # 填满区域，保持比例
                            Qt.SmoothTransformation
                        )
                        # 从中心裁剪到目标尺寸
                        if scaled_pixmap.width() > icon_width or scaled_pixmap.height() > icon_height:
                            x_offset = max(0, (scaled_pixmap.width() - icon_width) // 2)
                            y_offset = max(0, (scaled_pixmap.height() - icon_height) // 2)
                            scaled_pixmap = scaled_pixmap.copy(x_offset, y_offset, icon_width, icon_height)
                        self.icon_label.setPixmap(scaled_pixmap)
        
        self.name_label.setFont(QFont("Microsoft YaHei UI", name_size, QFont.Bold))


class CarouselWidget(QWidget):
    """3D 旋转木马组件"""
    
    persona_selected = Signal(str)  # 选中的助手 key
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme_manager()
        self.cards = []
        self.current_index = 0
        self.is_animating = False
        self.auto_rotate_timer = None
        
        # 布局参数（会根据窗口大小自动调整）
        self.radius = 350  # 旋转半径
        self.center_x = 400
        self.center_y = 250
        self.visible_cards = 5  # 可见卡片数量
        self.base_card_width = 160  # 基础卡片宽度
        self.base_card_height = 220  # 基础卡片高度
        
        self.setMinimumSize(800, 500)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 连接主题变更
        self.theme.theme_changed.connect(self.apply_theme)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新计算布局"""
        super().resizeEvent(event)
        
        width = self.width()
        height = self.height()
        
        # 根据窗口大小自动调整参数
        self.center_x = width // 2
        # 垂直居中
        self.center_y = height // 2
        
        # 半径根据窗口大小调整（使用较小的维度）
        min_dimension = min(width, height)
        self.radius = int(min_dimension * 0.35)
        
        # 根据窗口大小调整卡片基础尺寸
        # 窗口越大，卡片越大
        scale_factor = min(width / 1000, height / 600)  # 基准：1000x600
        scale_factor = max(0.6, min(scale_factor, 1.5))  # 限制在 0.6 ~ 1.5 倍
        
        self.base_card_width = int(160 * scale_factor)
        self.base_card_height = int(220 * scale_factor)
        
        # 可见卡片数量根据窗口宽度调整
        if width < 900:
            self.visible_cards = 3
        elif width < 1300:
            self.visible_cards = 5
        else:
            self.visible_cards = 7
        
        # 重新布局
        self.update_positions()
    
    def set_personas(self, personas: dict):
        """设置助手列表"""
        # 清空现有卡片
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        
        # 排序：default（通用AI）放在第一位
        sorted_personas = []
        if 'default' in personas:
            sorted_personas.append(('default', personas['default']))
        for key, persona in personas.items():
            if key != 'default':
                sorted_personas.append((key, persona))
        
        # 创建新卡片
        for key, persona in sorted_personas:
            card = CarouselCard(key, persona, self)
            card.clicked.connect(lambda checked, k=key: self.on_card_clicked(k))
            card.hide()
            self.cards.append(card)
        
        self.current_index = 0
        self.update_positions()
    
    def update_positions(self):
        """更新所有卡片位置"""
        if not self.cards:
            return
        
        total_cards = len(self.cards)
        if total_cards == 0:
            return
        
        # 计算每个卡片的角度
        angle_step = 360.0 / total_cards
        
        # 当前索引可能是浮点数（动画中），需要处理
        current_idx = self.current_index
        
        for i, card in enumerate(self.cards):
            # 计算相对于当前中心卡片的偏移
            offset = (i - current_idx + total_cards) % total_cards
            
            # 如果偏移超过一半，从另一侧计算
            if offset > total_cards / 2:
                offset = offset - total_cards
            
            # 只显示可见范围内的卡片
            half_visible = self.visible_cards // 2
            if abs(offset) > half_visible:
                card.hide()
                continue
            
            # 计算角度（0度在正前方）
            angle = offset * angle_step
            angle_rad = math.radians(angle)
            
            # 3D 透视效果：椭圆轨迹
            x_offset = self.radius * math.sin(angle_rad)
            z_offset = self.radius * 0.6 * math.cos(angle_rad)
            
            # 计算实际位置
            x = self.center_x + int(x_offset) - card.width() // 2
            y = self.center_y - card.height() // 2
            
            # 根据深度计算缩放和透明度
            z_normalized = (z_offset + self.radius * 0.6) / (self.radius * 1.2)
            
            # 缩放：0.5 ~ 1.3（中心卡片更大）
            # 判断是否是中心卡片（偏移量接近0）
            is_center = abs(offset) < 0.5
            if is_center:
                scale = 1.3
            else:
                scale = 0.5 + z_normalized * 0.6
            
            # 透明度：0.4 ~ 1.0
            opacity = 0.4 + z_normalized * 0.6
            
            # z-order
            z_order = int(z_normalized * 1000)
            
            # 应用变换
            card.set_transform(scale, opacity, z_order, is_center)
            card.move(x, y)
            card.show()
            
            # 确保中心卡片在最上层
            if is_center:
                card.raise_()
            else:
                # 其他卡片按z顺序排列
                center_index = int(current_idx) % len(self.cards)
                if 0 <= center_index < len(self.cards):
                    card.stackUnder(self.cards[center_index])
                else:
                    card.stackUnder(card)
    
    def rotate_to(self, index: int, animated: bool = True):
        """旋转到指定索引"""
        if not self.cards or self.is_animating:
            return
        
        index = index % len(self.cards)
        
        if animated:
            self.is_animating = True
            # 使用定时器实现平滑动画
            self.animation_steps = 20
            self.animation_current = 0
            self.animation_start = self.current_index
            self.animation_target = index
            
            # 计算最短旋转路径
            diff = self.animation_target - self.animation_start
            if abs(diff) > len(self.cards) / 2:
                if diff > 0:
                    self.animation_target -= len(self.cards)
                else:
                    self.animation_target += len(self.cards)
            
            self.animation_timer = QTimer(self)
            self.animation_timer.timeout.connect(self._animate_step)
            self.animation_timer.start(16)  # ~60 FPS
        else:
            self.current_index = index
            self.update_positions()
    
    def _animate_step(self):
        """动画步进"""
        self.animation_current += 1
        
        # 使用缓动函数
        progress = self.animation_current / self.animation_steps
        eased_progress = self._ease_in_out_cubic(progress)
        
        # 计算当前位置
        current_pos = self.animation_start + (self.animation_target - self.animation_start) * eased_progress
        
        # 临时设置位置（不改变 current_index）
        old_index = self.current_index
        self.current_index = current_pos
        self.update_positions()
        
        if self.animation_current >= self.animation_steps:
            self.animation_timer.stop()
            self.current_index = self.animation_target % len(self.cards)
            self.update_positions()
            self.is_animating = False
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """三次缓动函数"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def next_card(self):
        """下一张卡片"""
        if self.cards:
            self.rotate_to((self.current_index + 1) % len(self.cards))
    
    def prev_card(self):
        """上一张卡片"""
        if self.cards:
            self.rotate_to((self.current_index - 1 + len(self.cards)) % len(self.cards))
    
    def on_card_clicked(self, key: str):
        """卡片点击事件"""
        # 找到点击的卡片索引
        clicked_index = -1
        for i, card in enumerate(self.cards):
            if card.key == key:
                clicked_index = i
                break
        
        if clicked_index == -1:
            return
        
        # 如果点击的是中心卡片，发送选中信号
        if clicked_index == self.current_index:
            self.persona_selected.emit(key)
        else:
            # 否则旋转到该卡片
            self.rotate_to(clicked_index)
    
    def start_auto_rotate(self, interval: int = 3000):
        """开始自动旋转"""
        if self.auto_rotate_timer:
            self.auto_rotate_timer.stop()
        
        self.auto_rotate_timer = QTimer(self)
        self.auto_rotate_timer.timeout.connect(self.next_card)
        self.auto_rotate_timer.start(interval)
    
    def stop_auto_rotate(self):
        """停止自动旋转"""
        if self.auto_rotate_timer:
            self.auto_rotate_timer.stop()
    
    def apply_theme(self):
        """应用主题"""
        c = self.theme.colors
        self.setStyleSheet(f"background-color: {c['bg']};")
        
        # 更新所有卡片样式
        for i, card in enumerate(self.cards):
            if i == self.current_index:
                card.set_transform(card.scale_factor, card.opacity_value, card.z_order, True)
            else:
                card.set_transform(card.scale_factor, card.opacity_value, card.z_order, False)
    
    def enterEvent(self, event):
        """鼠标进入时暂停自动旋转"""
        self.stop_auto_rotate()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开时恢复自动旋转"""
        self.start_auto_rotate()
        super().leaveEvent(event)
    
    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        if event.angleDelta().y() > 0:
            self.prev_card()
        else:
            self.next_card()
        event.accept()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Left:
            self.prev_card()
        elif event.key() == Qt.Key_Right:
            self.next_card()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.cards and 0 <= self.current_index < len(self.cards):
                current_card = self.cards[self.current_index]
                self.persona_selected.emit(current_card.key)
        else:
            super().keyPressEvent(event)
