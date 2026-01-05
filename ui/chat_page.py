from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QComboBox, QMessageBox,
    QFileDialog, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont
from datetime import datetime
import os

from .themes import get_theme_manager
from .components import ChatBubble
from .suggestion_buttons import SuggestionButtonGroup, SuggestionLoadingWidget
from .chat_settings_panel import CollapsiblePanel


class ChatPage(QWidget):
    """聊天页面"""
    
    settings_clicked = Signal()
    send_message = Signal(str, dict)  # 消息文本, 模型参数
    stop_generation = Signal()  # 停止生成信号
    model_changed = Signal(str)
    new_chat_with_persona = Signal(str)  # 新增
    request_suggestions = Signal(str)  # 请求生成推荐选项（传递最后一条 AI 消息）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_ai_bubble = None
        self.theme = get_theme_manager()
        self._is_generating = False  # 跟踪生成状态
        
        # 用户和 AI 配置
        self.user_name = "我"
        self.ai_name = ""  # 默认使用模型名
        self.user_avatar_path = None
        self.user_avatar_color = "#007AFF"  # 默认头像颜色
        self.ai_avatar_path = None
        self.ai_icon = "🤖"  # AI 的 emoji 图标
        self.current_model_name = ""  # 当前模型名（简化版）
        self.is_roleplay = False  # 是否是角色扮演模式
        
        # 模型名称映射（显示名称 -> ollama 完整名称）
        self.model_name_map = {}
        
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)

        self.chat_backgrounds = []
        self.background_interval = 5
        self.current_bg_index = 0
        self.bg_timer = None
    
    def setup_ui(self):
        # 主布局：水平布局（聊天区 + 右侧面板）
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧聊天区域容器
        chat_container = QWidget()
        layout = QVBoxLayout(chat_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.create_header(layout)
        self.create_chat_area(layout)
        self.create_input_area(layout)
        
        main_layout.addWidget(chat_container, 1)
        
        # 右侧设置面板
        self.settings_panel = CollapsiblePanel()
        main_layout.addWidget(self.settings_panel, 0)
        
        self.apply_theme()
    
    def create_header(self, parent_layout):
        self.header = QWidget()
        self.header.setFixedHeight(70)
        
        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(25, 0, 25, 0)
        
        # 模型选择容器
        model_container = QWidget()
        model_layout = QHBoxLayout(model_container)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(10)
        
        # 模型图标
        self.model_icon = QLabel("🤖")
        self.model_icon.setFont(QFont("Segoe UI Emoji", 18))
        self.model_icon.setFixedSize(30, 30)
        model_layout.addWidget(self.model_icon)
        
        # 模型下拉框
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(240)
        self.model_combo.setFixedHeight(42)
        self.model_combo.setPlaceholderText("选择模型...")
        self.model_combo.setCursor(Qt.PointingHandCursor)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        
        layout.addWidget(model_container)
        
        # 标题
        self.title_label = QLabel("新对话")
        self.title_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label, 1)
        
        # 设置按钮
        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.setFont(QFont("Segoe UI Emoji", 13))
        self.settings_btn.setFixedHeight(50)  # 增加高度确保 emoji 完整显示
        self.settings_btn.setMinimumWidth(100)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)
        
        parent_layout.addWidget(self.header)
    
    def create_chat_area(self, parent_layout):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 20, 0, 20)
        self.chat_layout.setSpacing(5)
        self.chat_layout.addStretch()
        
        self.scroll_area.setWidget(self.chat_container)
        parent_layout.addWidget(self.scroll_area, 1)
        
        # 初始化时不显示欢迎界面，等待 personas 数据加载后再显示
        self.welcome_widget = None
        self.carousel = None
    
    def create_input_area(self, parent_layout):
        self.input_container = QWidget()
        self.input_container.setFixedHeight(140)
        
        layout = QVBoxLayout(self.input_container)
        layout.setContentsMargins(25, 15, 25, 20)
        layout.setSpacing(10)
        
        self.input_frame = QFrame()
        input_layout = QHBoxLayout(self.input_frame)
        input_layout.setContentsMargins(18, 12, 12, 12)
        input_layout.setSpacing(12)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入消息，按 Enter 发送...")
        self.input_text.setMaximumHeight(70)
        self.input_text.setFont(QFont("Microsoft YaHei UI", 12))
        self.input_text.installEventFilter(self)
        input_layout.addWidget(self.input_text)
        
        self.send_btn = QPushButton("发送 ➤")
        self.send_btn.setFixedSize(90, 45)
        self.send_btn.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.on_send_clicked)
        input_layout.addWidget(self.send_btn)
        
        layout.addWidget(self.input_frame)
        
        self.hint_label = QLabel("按 Enter 发送 · Shift + Enter 换行")
        self.hint_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint_label)
        
        parent_layout.addWidget(self.input_container)
    
    def set_personas(self, personas: dict):
        """设置可用人格列表"""
        self.personas = personas
        
        # 如果欢迎界面已存在且有旋转木马，更新它
        if hasattr(self, 'carousel') and self.carousel:
            self.carousel.set_personas(personas)
        # 如果欢迎界面存在但没有旋转木马，重新创建
        elif hasattr(self, 'welcome_widget') and self.welcome_widget:
            self.clear_welcome()
            self.show_welcome(personas)
        # 如果是首次设置且当前没有消息，显示欢迎界面
        elif not hasattr(self, 'welcome_widget') or not self.welcome_widget:
            # 检查聊天区域是否为空（只有stretch）
            if self.chat_layout.count() <= 1:
                self.show_welcome(personas)

    def set_chat_backgrounds(self, backgrounds: list, interval: int = 5):
        """设置聊天背景"""
        self.chat_backgrounds = [bg for bg in backgrounds if os.path.exists(bg)]
        self.background_interval = interval
        self.current_bg_index = 0
        
        if self.chat_backgrounds:
            self._start_bg_slideshow()
            self._update_background()
        else:
            self._stop_bg_slideshow()
            self._clear_background()

    def _start_bg_slideshow(self):
        """启动背景轮播"""
        from PySide6.QtCore import QTimer
        
        if self.bg_timer:
            self.bg_timer.stop()
        
        if len(self.chat_backgrounds) > 1:
            self.bg_timer = QTimer(self)
            self.bg_timer.timeout.connect(self._next_background)
            self.bg_timer.start(self.background_interval * 1000)

    def _stop_bg_slideshow(self):
        """停止背景轮播"""
        if self.bg_timer:
            self.bg_timer.stop()
            self.bg_timer = None

    def _next_background(self):
        """切换到下一张背景"""
        if self.chat_backgrounds:
            self.current_bg_index = (self.current_bg_index + 1) % len(self.chat_backgrounds)
            self._update_background()

    def _update_background(self):
        """更新背景图片"""
        if self.chat_backgrounds and 0 <= self.current_bg_index < len(self.chat_backgrounds):
            bg_path = self.chat_backgrounds[self.current_bg_index]
            
            # 使用 QPalette 设置背景图片（更可靠的方法）
            from PySide6.QtGui import QPalette, QBrush, QPixmap
            
            pixmap = QPixmap(bg_path)
            if not pixmap.isNull():
                # 缩放图片以适应窗口大小
                viewport_size = self.scroll_area.viewport().size()
                scaled_pixmap = pixmap.scaled(
                    viewport_size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                
                # 设置到 viewport 而不是 scroll_area
                viewport = self.scroll_area.viewport()
                palette = viewport.palette()
                palette.setBrush(QPalette.Window, QBrush(scaled_pixmap))
                viewport.setPalette(palette)
                viewport.setAutoFillBackground(True)
                
                # 聊天容器完全透明
                self.chat_container.setStyleSheet("background-color: transparent;")
    
    def update_background_on_resize(self):
        """窗口大小改变时更新背景"""
        # 重新应用当前背景以适应新的窗口大小
        if self.chat_backgrounds:
            self._update_background()
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        
        # 如果有旋转木马组件，通知它更新布局
        if hasattr(self, 'carousel') and self.carousel:
            # 强制触发 carousel 的 resizeEvent
            from PySide6.QtCore import QEvent, QSize
            resize_event = event.__class__(QSize(self.carousel.width(), self.carousel.height()), event.oldSize())
            self.carousel.resizeEvent(resize_event)

    def _clear_background(self):
        """清除背景"""
        # 恢复默认背景色
        viewport = self.scroll_area.viewport()
        viewport.setAutoFillBackground(False)
        c = self.theme.colors
        # 恢复背景色，同时保留滚动条样式
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {c['bg']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 10px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c['scrollbar']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {c['scrollbar_hover']};
            }}
            QScrollBar::handle:vertical:pressed {{
                background-color: {c['text_dim']}80;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        self.chat_container.setStyleSheet(f"background-color: {c['bg']};")

    def _on_model_changed(self, model_name: str):
        """模型选择变化"""
        if model_name:
            # 提取简化的模型名（去掉量化版本和 :latest）
            self.current_model_name = self._simplify_model_name(model_name)
            self.model_changed.emit(model_name)
            # 恢复正常样式（如果之前是错误状态）
            self._restore_model_combo_style()
    
    def _simplify_model_name(self, full_name: str) -> str:
        """简化模型名称，去掉量化版本"""
        # 去掉 :latest
        name = full_name.split(':')[0]
        
        # 常见量化后缀
        quant_suffixes = [
            '-q2_k', '-q3_k_m', '-q3_k_s', '-q4_0', '-q4_k_m', '-q4_k_s',
            '-q5_0', '-q5_k_m', '-q5_k_s', '-q6_k', '-q8_0', '-bf16', '-f16',
            '-Q2_K', '-Q3_K_M', '-Q3_K_S', '-Q4_0', '-Q4_K_M', '-Q4_K_S',
            '-Q5_0', '-Q5_K_M', '-Q5_K_S', '-Q6_K', '-Q8_0', '-BF16', '-F16',
            '_q2k', '_q3km', '_q4km', '_q5km', '_q6k', '_q80', '_bf16', '_f16'
        ]
        
        for suffix in quant_suffixes:
            if suffix.lower() in name.lower():
                idx = name.lower().find(suffix.lower())
                name = name[:idx]
                break
        
        return name
    
    def get_ai_display_name(self) -> str:
        """获取 AI 显示名称"""
        if self.ai_name:
            return self.ai_name
        return self.current_model_name if self.current_model_name else "AI"
    
    def set_user_name(self, name: str):
        """设置用户名称"""
        self.user_name = name if name else "我"
    
    def set_ai_name(self, name: str):
        """设置 AI 名称（自定义）"""
        self.ai_name = name
    
    def set_roleplay_mode(self, is_roleplay: bool):
        """设置是否为角色扮演模式"""
        self.is_roleplay = is_roleplay
    
    def set_user_avatar(self, path: str = None, color: str = None):
        """设置用户头像（支持图片或颜色）"""
        print(f"[DEBUG] set_user_avatar called: path={path}, color={color}")
        self.user_avatar_path = path
        self.user_avatar_color = color if color else "#007AFF"
    
    def set_ai_avatar(self, path: str):
        """设置 AI 头像"""
        self.ai_avatar_path = path
    
    def set_ai_icon(self, icon: str):
        """设置 AI 图标 emoji"""
        self.ai_icon = icon if icon else "🤖"
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        
        # 头部样式
        self.header.setStyleSheet(f"""
            QWidget {{
                background-color: {c['bg']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        
        # 模型下拉框样式 - 优化版
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c['card_bg']};
                border: 2px solid {c['border']};
                border-radius: 12px;
                padding: 8px 15px;
                padding-right: 35px;
                color: {c['text']};
                font-size: 14px;
                font-weight: 500;
            }}
            
            QComboBox:hover {{
                border-color: {c['accent']};
                background-color: {c['hover']};
            }}
            
            QComboBox:focus {{
                border-color: {c['accent']};
                background-color: {c['card_bg']};
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
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 10px 15px;
                border-radius: 8px;
                margin: 2px 0;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {c['hover']};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {c['accent']};
                color: white;
            }}
        """)
        
        # 设置按钮样式
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                padding: 10px 20px;
                border-radius: 12px;
                border: 2px solid transparent;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {c['text']};
                border-color: {c['border']};
            }}
        """)
        
        # 标题样式
        self.title_label.setStyleSheet(f"color: {c['text']};")
        
        # 聊天区域样式（包含美化的滚动条）
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {c['bg']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 10px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c['scrollbar']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {c['scrollbar_hover']};
            }}
            QScrollBar::handle:vertical:pressed {{
                background-color: {c['text_dim']}80;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        self.chat_container.setStyleSheet(f"background-color: {c['bg']};")
        self.input_container.setStyleSheet(f"background-color: {c['bg']};")
        
        # 输入框样式
        self.input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['input_bg']};
                border: 2px solid {c['border']};
                border-radius: 16px;
            }}
        """)
        
        self.input_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {c['text']};
            }}
        """)
        
        # 发送按钮样式
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {c['text_dim']};
                opacity: 0.6;
            }}
        """)
        
        self.hint_label.setStyleSheet(f"color: {c['text_dim']};")
        
        # 更新欢迎页面（如果存在）
        if hasattr(self, 'welcome_widget') and self.welcome_widget:
            self._update_welcome_theme()
    
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        
        if obj == self.input_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return:
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                else:
                    current_model = self.model_combo.currentText()
                    if not current_model:
                        # 不弹窗，给模型下拉框添加红色边框提示
                        self._highlight_model_combo_error()
                        return True
                    
                    self.on_send_clicked()
                    return True
        
        return super().eventFilter(obj, event)
    
    def show_welcome(self, personas: dict = None):
        """显示欢迎界面（3D旋转木马 - 仅助手）"""
        from .carousel_widget import CarouselWidget
        
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部标题区域（固定高度）
        header_widget = QWidget()
        header_widget.setFixedHeight(120)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        title = QLabel("选择助手开始对话")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.theme.colors['accent_light']};")
        header_layout.addWidget(title)
        
        # 操作提示（整合到标题下方）
        hint_container = QWidget()
        hint_layout = QHBoxLayout(hint_container)
        hint_layout.setAlignment(Qt.AlignCenter)
        hint_layout.setSpacing(20)
        hint_layout.setContentsMargins(0, 5, 0, 0)
        
        hints = [
            ("← →", "切换助手"),
            ("滚轮", "旋转"),
            ("Enter", "确认选择")
        ]
        
        for key, desc_text in hints:
            hint_item = QWidget()
            hint_item_layout = QHBoxLayout(hint_item)
            hint_item_layout.setSpacing(6)
            hint_item_layout.setContentsMargins(0, 0, 0, 0)
            
            key_label = QLabel(key)
            key_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
            key_label.setStyleSheet(f"""
                background-color: {self.theme.colors['card_bg']};
                color: {self.theme.colors['accent']};
                padding: 3px 6px;
                border-radius: 4px;
                border: 1px solid {self.theme.colors['border']};
            """)
            hint_item_layout.addWidget(key_label)
            
            desc_label = QLabel(desc_text)
            desc_label.setFont(QFont("Microsoft YaHei UI", 9))
            desc_label.setStyleSheet(f"color: {self.theme.colors['text_dim']};")
            hint_item_layout.addWidget(desc_label)
            
            hint_layout.addWidget(hint_item)
        
        header_layout.addWidget(hint_container)
        
        layout.addWidget(header_widget)
        
        # 3D 旋转木马 - 只显示助手（占据剩余空间）
        if personas:
            # 筛选出助手（排除角色扮演）
            assistants = {k: v for k, v in personas.items() if v.get('type', 'assistant') == 'assistant'}
            
            if assistants:
                self.carousel = CarouselWidget(self.welcome_widget)
                self.carousel.set_personas(assistants)
                self.carousel.persona_selected.connect(self.new_chat_with_persona.emit)
                layout.addWidget(self.carousel, 1)  # stretch=1 让它占据剩余空间
                
                # 应用主题
                c = self.theme.colors
                self.carousel.setStyleSheet(f"background-color: {c['bg']};")
        
        self.chat_layout.insertWidget(0, self.welcome_widget)
    
    def _create_persona_section(self, title: str, personas: dict):
        """创建人格分类区域"""
        from PySide6.QtWidgets import QGridLayout, QSizePolicy
        
        section = QWidget()
        section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(15)
        section_layout.setContentsMargins(20, 0, 20, 0)
        
        # 分类标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setStyleSheet(f"color: {self.theme.colors['text']};")
        section_layout.addWidget(title_label)
        
        # 使用 FlowLayout 实现自适应布局
        grid_container = QWidget()
        grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # 使用网格布局，但动态计算列数
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        personas_list = list(personas.items())
        
        # 根据容器宽度动态计算列数
        # 每个按钮宽度 120px + 间距 15px = 135px
        # 最少2列，最多8列
        row = 0
        col = 0
        max_cols = 5  # 默认每行5个
        
        for key, persona in personas_list:
            btn = self._create_persona_button(key, persona)
            grid_layout.addWidget(btn, row, col, Qt.AlignLeft | Qt.AlignTop)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # 添加弹性空间，使按钮靠左对齐
        grid_layout.setColumnStretch(max_cols, 1)
        
        section_layout.addWidget(grid_container)
        
        return section
    
    def _create_persona_button(self, key: str, persona: dict):
        """创建人格选择按钮"""
        from PySide6.QtGui import QPixmap
        from core.media_manager import get_media_manager
        
        btn = QPushButton()
        btn.setFixedSize(130, 110)  # 稍微增大按钮尺寸
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.new_chat_with_persona.emit(key))
        
        btn_layout = QVBoxLayout(btn)
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.setSpacing(6)
        btn_layout.setContentsMargins(8, 8, 8, 8)
        
        # 头像显示（优先使用自定义图片）
        icon_label = QLabel()
        icon_label.setFixedSize(50, 50)
        icon_label.setAlignment(Qt.AlignCenter)
        
        icon_path = persona.get("icon_path", "")
        if icon_path:
            # 转换为绝对路径
            media_manager = get_media_manager()
            abs_path = media_manager.get_absolute_path(icon_path)
            
            if os.path.exists(abs_path):
                # 显示自定义图片头像
                pixmap = QPixmap(abs_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        50, 50,
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation
                    )
                    icon_label.setPixmap(scaled_pixmap)
                    icon_label.setStyleSheet("""
                        border-radius: 25px;
                        background: transparent;
                    """)
                else:
                    # 图片加载失败，使用 emoji
                    icon_label.setText(persona.get("icon", "🤖"))
                    icon_label.setFont(QFont("Segoe UI Emoji", 28))
            else:
                # 文件不存在，使用 emoji
                icon_label.setText(persona.get("icon", "🤖"))
                icon_label.setFont(QFont("Segoe UI Emoji", 28))
        else:
            # 没有自定义图片，使用 emoji
            icon_label.setText(persona.get("icon", "🤖"))
            icon_label.setFont(QFont("Segoe UI Emoji", 28))
        
        btn_layout.addWidget(icon_label)
        
        name_label = QLabel(persona.get("name", "未知"))
        name_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(110)
        btn_layout.addWidget(name_label)
        
        c = self.theme.colors
        
        # 设置名称标签的颜色
        name_label.setStyleSheet(f"color: {c['text']}; background: transparent;")
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['card_bg']};
                border: 2px solid {c['border']};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['accent']};
            }}
            QPushButton:pressed {{
                background-color: {c['active']};
            }}
        """)
        
        return btn
    
    def show_welcome_assistants_only(self):
        """显示欢迎界面（只显示助手 - 3D旋转木马）"""
        from .carousel_widget import CarouselWidget
        
        personas = getattr(self, 'personas', None)
        if not personas:
            return
        
        # 只筛选助手
        assistants = {k: v for k, v in personas.items() if v.get('type', 'assistant') == 'assistant'}
        
        if not assistants:
            return
        
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部标题区域（固定高度）
        header_widget = QWidget()
        header_widget.setFixedHeight(120)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        title = QLabel("选择助手")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.theme.colors['accent_light']};")
        header_layout.addWidget(title)
        
        # 操作提示（整合到标题下方）
        hint_container = QWidget()
        hint_layout_inner = QHBoxLayout(hint_container)
        hint_layout_inner.setAlignment(Qt.AlignCenter)
        hint_layout_inner.setSpacing(20)
        hint_layout_inner.setContentsMargins(0, 5, 0, 0)
        
        hints = [
            ("← →", "切换助手"),
            ("滚轮", "旋转"),
            ("Enter", "确认选择")
        ]
        
        for key, desc_text in hints:
            hint_item = QWidget()
            hint_item_layout = QHBoxLayout(hint_item)
            hint_item_layout.setSpacing(6)
            hint_item_layout.setContentsMargins(0, 0, 0, 0)
            
            key_label = QLabel(key)
            key_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
            key_label.setStyleSheet(f"""
                background-color: {self.theme.colors['card_bg']};
                color: {self.theme.colors['accent']};
                padding: 3px 6px;
                border-radius: 4px;
                border: 1px solid {self.theme.colors['border']};
            """)
            hint_item_layout.addWidget(key_label)
            
            desc_label = QLabel(desc_text)
            desc_label.setFont(QFont("Microsoft YaHei UI", 9))
            desc_label.setStyleSheet(f"color: {self.theme.colors['text_dim']};")
            hint_item_layout.addWidget(desc_label)
            
            hint_layout_inner.addWidget(hint_item)
        
        header_layout.addWidget(hint_container)
        
        layout.addWidget(header_widget)
        
        # 3D 旋转木马（占据剩余空间）
        self.carousel = CarouselWidget(self.welcome_widget)
        self.carousel.set_personas(assistants)
        self.carousel.persona_selected.connect(self.new_chat_with_persona.emit)
        layout.addWidget(self.carousel, 1)  # stretch=1 让它占据剩余空间
        
        # 应用主题
        c = self.theme.colors
        self.carousel.setStyleSheet(f"background-color: {c['bg']};")
        
        self.chat_layout.insertWidget(0, self.welcome_widget)
    
    def show_welcome_roles_only(self):
        """显示欢迎界面（只显示角色 - 3D旋转木马）"""
        from .carousel_widget import CarouselWidget
        
        personas = getattr(self, 'personas', None)
        if not personas:
            return
        
        # 只筛选角色
        roles = {k: v for k, v in personas.items() if v.get('type', 'assistant') == 'roleplay'}
        
        if not roles:
            return
        
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部标题区域（固定高度）
        header_widget = QWidget()
        header_widget.setFixedHeight(120)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        title = QLabel("选择角色")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.theme.colors['accent_light']};")
        header_layout.addWidget(title)
        
        # 操作提示（整合到标题下方）
        hint_container = QWidget()
        hint_layout_inner = QHBoxLayout(hint_container)
        hint_layout_inner.setAlignment(Qt.AlignCenter)
        hint_layout_inner.setSpacing(20)
        hint_layout_inner.setContentsMargins(0, 5, 0, 0)
        
        hints = [
            ("← →", "切换角色"),
            ("滚轮", "旋转"),
            ("Enter", "确认选择")
        ]
        
        for key, desc_text in hints:
            hint_item = QWidget()
            hint_item_layout = QHBoxLayout(hint_item)
            hint_item_layout.setSpacing(6)
            hint_item_layout.setContentsMargins(0, 0, 0, 0)
            
            key_label = QLabel(key)
            key_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
            key_label.setStyleSheet(f"""
                background-color: {self.theme.colors['card_bg']};
                color: {self.theme.colors['accent']};
                padding: 3px 6px;
                border-radius: 4px;
                border: 1px solid {self.theme.colors['border']};
            """)
            hint_item_layout.addWidget(key_label)
            
            desc_label = QLabel(desc_text)
            desc_label.setFont(QFont("Microsoft YaHei UI", 9))
            desc_label.setStyleSheet(f"color: {self.theme.colors['text_dim']};")
            hint_item_layout.addWidget(desc_label)
            
            hint_layout_inner.addWidget(hint_item)
        
        header_layout.addWidget(hint_container)
        
        layout.addWidget(header_widget)
        
        # 3D 旋转木马（占据剩余空间）
        self.carousel = CarouselWidget(self.welcome_widget)
        self.carousel.set_personas(roles)
        self.carousel.persona_selected.connect(self.new_chat_with_persona.emit)
        layout.addWidget(self.carousel, 1)  # stretch=1 让它占据剩余空间
        
        # 应用主题
        c = self.theme.colors
        self.carousel.setStyleSheet(f"background-color: {c['bg']};")
        
        self.chat_layout.insertWidget(0, self.welcome_widget)

    def clear_welcome(self):
        if hasattr(self, 'welcome_widget') and self.welcome_widget:
            self.welcome_widget.deleteLater()
            self.welcome_widget = None
        if hasattr(self, 'carousel') and self.carousel:
            self.carousel = None
    
    def _update_welcome_theme(self):
        """更新欢迎页面的主题"""
        if not hasattr(self, 'welcome_widget') or not self.welcome_widget:
            return
        
        c = self.theme.colors
        
        # 更新所有标签的颜色
        for widget in self.welcome_widget.findChildren(QLabel):
            # 检查是否是描述文本（通过字体大小判断）
            if widget.font().pointSize() == 14:
                widget.setStyleSheet(f"color: {c['text_secondary']};")
            elif widget.font().pointSize() in [28, 56]:
                # 标题和图标，保持原样
                pass
            else:
                # 其他文本
                widget.setStyleSheet(f"color: {c['text']}; background: transparent;")
        
        # 更新所有按钮
        for btn in self.welcome_widget.findChildren(QPushButton):
            # 查找按钮内的名称标签
            for label in btn.findChildren(QLabel):
                if label.text() and not label.pixmap():  # 文本标签，不是图片
                    label.setStyleSheet(f"color: {c['text']}; background: transparent;")
            
            # 更新按钮样式
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['card_bg']};
                    border: 2px solid {c['border']};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c['hover']};
                    border-color: {c['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {c['active']};
                }}
            """)
    
    def clear_messages(self):
        """清空消息区域（不显示欢迎界面）"""
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def add_user_message(self, text: str, timestamp: str = None):
        """添加用户消息"""
        self.clear_welcome()
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        bubble = ChatBubble(
            text=text,
            is_user=True,
            name=self.user_name,
            avatar_path=self.user_avatar_path,
            timestamp=timestamp
        )
        print(f"[DEBUG] 创建用户气泡: user_name={self.user_name}, avatar_path={self.user_avatar_path}")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll_to_bottom()
    
    def add_ai_message(self, text: str, timestamp: str = None, model_name: str = None):
        """添加 AI 消息"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 优先使用设置的 AI 名称，如果没有则使用模型名
        if self.ai_name:
            display_name = self.ai_name
        elif model_name:
            display_name = self._simplify_model_name(model_name)
        else:
            display_name = self.get_ai_display_name()
        
        bubble = ChatBubble(
            text=text,
            is_user=False,
            name=display_name,
            avatar_path=self.ai_avatar_path,
            icon=self.ai_icon,
            timestamp=timestamp,
            is_roleplay=self.is_roleplay
        )
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll_to_bottom()
    
    def start_ai_response(self):
        """开始 AI 回复（流式）"""
        display_name = self.get_ai_display_name()
        
        self.current_ai_bubble = ChatBubble(
            text="",
            is_user=False,
            name=display_name,
            avatar_path=self.ai_avatar_path,
            icon=self.ai_icon,
            timestamp=datetime.now().isoformat(),
            is_roleplay=self.is_roleplay,
            is_streaming=True  # 标记为流式响应，启用加载动画
        )
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_ai_bubble)
        self.scroll_to_bottom()
    
    @Slot(str)
    def update_ai_response(self, text: str):
        """更新 AI 回复内容"""
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(text)
            self.scroll_to_bottom()
    
    def finish_ai_response(self):
        self.current_ai_bubble = None
    
    def add_suggestion_buttons(self, suggestions: list):
        """添加推荐选项按钮组"""
        if not suggestions:
            return
        
        # 先清除已有的推荐按钮组和加载状态
        self.clear_suggestion_buttons()
        
        btn_group = SuggestionButtonGroup(suggestions, self)
        btn_group.setObjectName("suggestionGroup")
        btn_group.button_clicked.connect(self._on_suggestion_clicked)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, btn_group)
        self.scroll_to_bottom()
    
    def show_suggestion_loading(self):
        """显示推荐选项加载中状态"""
        # 先清除已有的
        self.clear_suggestion_buttons()
        
        loading = SuggestionLoadingWidget(self)
        loading.setObjectName("suggestionLoading")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, loading)
        self.scroll_to_bottom()
    
    def hide_suggestion_loading(self):
        """隐藏推荐选项加载状态"""
        for i in range(self.chat_layout.count() - 1, -1, -1):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "suggestionLoading":
                    widget.stop()
                    widget.deleteLater()
    
    def clear_suggestion_buttons(self):
        """清除所有推荐选项按钮组和加载状态"""
        for i in range(self.chat_layout.count() - 1, -1, -1):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() in ("suggestionGroup", "suggestionLoading"):
                    if hasattr(widget, 'stop'):
                        widget.stop()
                    widget.deleteLater()
    
    def _on_suggestion_clicked(self, text: str):
        """点击推荐选项后自动发送"""
        # 先清除推荐按钮组
        self.clear_suggestion_buttons()
        # 填入文本并发送
        self.input_text.setPlainText(text)
        self.on_send_clicked()
    
    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
    
    def on_send_clicked(self):
        current_model = self.model_combo.currentText()
        if not current_model:
            # 不弹窗，给模型下拉框添加红色边框提示
            self._highlight_model_combo_error()
            return
        
        text = self.input_text.toPlainText().strip()
        if text:
            self.input_text.clear()
            # 获取模型参数
            model_options = self.settings_panel.get_model_options()
            self.send_message.emit(text, model_options)
    
    def _highlight_model_combo_error(self):
        """高亮模型下拉框为错误状态（红色边框）"""
        c = self.theme.colors
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c['card_bg']};
                border: 3px solid #dc3545;
                border-radius: 12px;
                padding: 8px 15px;
                padding-right: 35px;
                color: {c['text']};
                font-size: 14px;
                font-weight: 500;
            }}
            
            QComboBox:hover {{
                border-color: #dc3545;
                background-color: {c['hover']};
            }}
            
            QComboBox:focus {{
                border-color: #dc3545;
                background-color: {c['card_bg']};
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
                border-top: 7px solid #dc3545;
                margin-right: 8px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {c['card_bg']};
                color: {c['text']};
                selection-background-color: {c['accent']};
                selection-color: white;
                border: 2px solid {c['border']};
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 10px 15px;
                border-radius: 8px;
                margin: 2px 0;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {c['hover']};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {c['accent']};
                color: white;
            }}
        """)
        
        # 更新占位符文本
        self.model_combo.setPlaceholderText("⚠️ 请先选择模型...")
        
        # 3秒后恢复正常样式
        QTimer.singleShot(3000, self._restore_model_combo_style)
    
    def _restore_model_combo_style(self):
        """恢复模型下拉框正常样式"""
        c = self.theme.colors
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c['card_bg']};
                border: 2px solid {c['border']};
                border-radius: 12px;
                padding: 8px 15px;
                padding-right: 35px;
                color: {c['text']};
                font-size: 14px;
                font-weight: 500;
            }}
            
            QComboBox:hover {{
                border-color: {c['accent']};
                background-color: {c['hover']};
            }}
            
            QComboBox:focus {{
                border-color: {c['accent']};
                background-color: {c['card_bg']};
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
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 10px 15px;
                border-radius: 8px;
                margin: 2px 0;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {c['hover']};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {c['accent']};
                color: white;
            }}
        """)
        
        # 恢复占位符文本
        self.model_combo.setPlaceholderText("选择模型...")
    
    @Slot(str)
    def set_title(self, title: str):
        self.title_label.setText(title)
    
    @Slot(bool)
    def set_send_enabled(self, enabled: bool):
        self._is_generating = not enabled
        self.input_text.setEnabled(enabled)
        
        if enabled:
            # 恢复发送状态
            self.send_btn.setText("发送 ➤")
            self.send_btn.setEnabled(True)
            self.input_text.setPlaceholderText("输入消息，按 Enter 发送...")
            try:
                self.send_btn.clicked.disconnect()
            except:
                pass
            self.send_btn.clicked.connect(self.on_send_clicked)
            self._apply_send_btn_style()
        else:
            # 生成中状态 - 显示停止按钮
            self.send_btn.setText("⏹ 停止")
            self.send_btn.setEnabled(True)  # 保持可点击
            self.input_text.setPlaceholderText("AI 正在回复中...")
            try:
                self.send_btn.clicked.disconnect()
            except:
                pass
            self.send_btn.clicked.connect(self._on_stop_clicked)
            self._apply_stop_btn_style()
    
    def _on_stop_clicked(self):
        """点击停止按钮"""
        # 禁用按钮并显示停止中状态
        self.send_btn.setText("停止中...")
        self.send_btn.setEnabled(False)
        self._apply_stopping_btn_style()
        self.stop_generation.emit()
    
    def _apply_send_btn_style(self):
        """应用发送按钮样式"""
        c = self.theme.colors
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {c['accent']};
            }}
            QPushButton:disabled {{
                background-color: {c['border']};
                color: {c['text_secondary']};
            }}
        """)
    
    def _apply_stop_btn_style(self):
        """应用停止按钮样式"""
        c = self.theme.colors
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #c82333;
            }}
            QPushButton:pressed {{
                background-color: #bd2130;
            }}
        """)
    
    def _apply_stopping_btn_style(self):
        """应用停止中按钮样式（禁用状态）"""
        c = self.theme.colors
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background-color: #6c757d;
                color: #adb5bd;
            }}
        """)
    
    def update_models(self, models: list):
        """更新模型列表"""
        current = self.model_combo.currentText()
        self.model_combo.clear()
        
        # 存储模型名称映射（显示名称 -> ollama 完整名称）
        self.model_name_map = {}
        
        for model in models:
            if isinstance(model, dict):
                full_name = model.get('name', '')
                ollama_name = model.get('ollama_name', full_name)
            else:
                full_name = model
                ollama_name = model
            
            # 简化显示名称
            display_name = self._simplify_model_display_name(full_name)
            
            self.model_combo.addItem(display_name)
            self.model_name_map[display_name] = ollama_name
        
        if current:
            # 尝试匹配当前选中的模型
            index = self.model_combo.findText(current)
            if index < 0:
                # 如果找不到，尝试用简化后的名称匹配
                simplified_current = self._simplify_model_display_name(current)
                index = self.model_combo.findText(simplified_current)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
    
    def _simplify_model_display_name(self, full_name: str) -> str:
        """简化模型显示名称，移除 :latest 和量化后缀"""
        if not full_name:
            return full_name
        
        # 移除 :latest 或其他标签
        name = full_name.split(':')[0]
        
        # 移除量化后缀（如 -Q4_K_M, -q8_0 等）
        import re
        # 匹配常见量化格式：-Q2_K, -Q3_K_M, -Q4_0, -q8_0, -BF16, -F16 等
        name = re.sub(r'-[Qq]\d+[_]?[KkMmSsLl0-9]*$', '', name)
        name = re.sub(r'-[Bb][Ff]16$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'-[Ff]16$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'-[Ff]32$', '', name, flags=re.IGNORECASE)
        
        return name
    
    def get_current_ollama_name(self) -> str:
        """获取当前选中模型的完整 ollama 名称"""
        display_name = self.model_combo.currentText()
        return self.model_name_map.get(display_name, display_name)
    
    def set_model(self, model_name: str):
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
    
    def load_messages(self, messages: list):
        """加载历史消息"""
        self.clear_messages()
        self.clear_welcome()
        
        current_model = None
        for msg in messages:
            model = msg.get("model", "")
            role = msg.get("role", "")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            # 如果模型切换了，显示分隔提示
            if model and model != current_model:
                if current_model is not None:
                    self._add_model_separator(self._simplify_model_name(model))
                current_model = model
            
            if role == "user":
                self.add_user_message(content, timestamp)
            elif role == "assistant":
                self.add_ai_message(content, timestamp, model)
    
    def _add_model_separator(self, model_name: str):
        """添加模型切换分隔线"""
        separator = QWidget()
        layout = QHBoxLayout(separator)
        layout.setContentsMargins(20, 10, 20, 10)
        
        c = self.theme.colors
        
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet(f"background-color: {c['border']};")
        line1.setFixedHeight(1)
        layout.addWidget(line1, 1)
        
        label = QLabel(f"  切换到 {model_name}  ")
        label.setFont(QFont("Microsoft YaHei UI", 10))
        label.setStyleSheet(f"color: {c['text_dim']};")
        layout.addWidget(label)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet(f"background-color: {c['border']};")
        line2.setFixedHeight(1)
        layout.addWidget(line2, 1)
        
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, separator)