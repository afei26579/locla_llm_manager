from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QComboBox, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont
from datetime import datetime
import os

from .themes import get_theme_manager
from .components import ChatBubble


class ChatPage(QWidget):
    """聊天页面"""
    
    settings_clicked = Signal()
    send_message = Signal(str)
    model_changed = Signal(str)
    new_chat_with_persona = Signal(str)  # 新增

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_ai_bubble = None
        self.theme = get_theme_manager()
        
        # 用户和 AI 配置
        self.user_name = "我"
        self.ai_name = ""  # 默认使用模型名
        self.user_avatar_path = None
        self.user_avatar_color = "#007AFF"  # 默认头像颜色
        self.ai_avatar_path = None
        self.current_model_name = ""  # 当前模型名（简化版）
        
        # 模型名称映射（显示名称 -> ollama 完整名称）
        self.model_name_map = {}
        
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)

        self.chat_backgrounds = []
        self.background_interval = 5
        self.current_bg_index = 0
        self.bg_timer = None
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.create_header(layout)
        self.create_chat_area(layout)
        self.create_input_area(layout)
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
        self.settings_btn.setFont(QFont("Microsoft YaHei UI", 13))
        self.settings_btn.setFixedHeight(42)
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
        
        self.show_welcome()
    
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
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 45)
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
    
    def set_user_avatar(self, path: str = None, color: str = None):
        """设置用户头像（支持图片或颜色）"""
        self.user_avatar_path = path
        self.user_avatar_color = color if color else "#007AFF"
    
    def set_ai_avatar(self, path: str):
        """设置 AI 头像"""
        self.ai_avatar_path = path
    
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
                        QMessageBox.warning(self, "提示", "请先选择模型")
                        return True
                    
                    self.on_send_clicked()
                    return True
        
        return super().eventFilter(obj, event)
    
    def show_welcome(self, personas: dict = None):
        """显示欢迎界面（含人格选择）"""
        from PySide6.QtWidgets import QScrollArea, QGridLayout
        
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部标题区域
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("🤖")
        icon.setFont(QFont("Segoe UI Emoji", 56))
        icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon)
        
        title = QLabel("开始新对话")
        title.setFont(QFont("Microsoft YaHei UI", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.theme.colors['accent_light']};")
        header_layout.addWidget(title)
        
        desc = QLabel("选择一个助手或角色开始对话")
        desc.setFont(QFont("Microsoft YaHei UI", 14))
        desc.setStyleSheet(f"color: {self.theme.colors['text']};")
        desc.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(desc)
        
        layout.addWidget(header_widget)
        
        # 人格选择区域（带滚动）
        if personas:
            # 分类助手和角色
            assistants = {}
            roles = {}
            
            for key, persona in personas.items():
                persona_type = persona.get('type', 'assistant')
                if persona_type == 'roleplay':
                    roles[key] = persona
                else:
                    assistants[key] = persona
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background: transparent;
                }
            """)
            
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setSpacing(30)
            scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            
            # 添加助手分类
            if assistants:
                assistant_section = self._create_persona_section("🤖 助手", assistants)
                scroll_layout.addWidget(assistant_section)
            
            # 添加角色分类
            if roles:
                role_section = self._create_persona_section("🎭 角色扮演", roles)
                scroll_layout.addWidget(role_section)
            
            scroll_area.setWidget(scroll_content)
            layout.addWidget(scroll_area, 1)
        
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
        """显示欢迎界面（只显示助手）"""
        from PySide6.QtWidgets import QScrollArea, QGridLayout
        
        personas = getattr(self, 'personas', None)
        if not personas:
            return
        
        # 只筛选助手
        assistants = {k: v for k, v in personas.items() if v.get('type', 'assistant') == 'assistant'}
        
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部标题区域
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("🤖")
        icon.setFont(QFont("Segoe UI Emoji", 56))
        icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon)
        
        title = QLabel("选择助手")
        title.setFont(QFont("Microsoft YaHei UI", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.theme.colors['accent_light']};")
        header_layout.addWidget(title)
        
        desc = QLabel("选择一个助手开始对话")
        desc.setFont(QFont("Microsoft YaHei UI", 14))
        desc.setStyleSheet(f"color: {self.theme.colors['text']};")
        desc.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(desc)
        
        layout.addWidget(header_widget)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(30)
        scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        if assistants:
            assistant_section = self._create_persona_section("🤖 助手", assistants)
            scroll_layout.addWidget(assistant_section)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)
        
        self.chat_layout.insertWidget(0, self.welcome_widget)
    
    def show_welcome_roles_only(self):
        """显示欢迎界面（只显示角色）"""
        from PySide6.QtWidgets import QScrollArea, QGridLayout
        
        personas = getattr(self, 'personas', None)
        if not personas:
            return
        
        # 只筛选角色
        roles = {k: v for k, v in personas.items() if v.get('type', 'assistant') == 'roleplay'}
        
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部标题区域
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("🎭")
        icon.setFont(QFont("Segoe UI Emoji", 56))
        icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon)
        
        title = QLabel("选择角色")
        title.setFont(QFont("Microsoft YaHei UI", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.theme.colors['accent_light']};")
        header_layout.addWidget(title)
        
        desc = QLabel("选择一个角色开始对话")
        desc.setFont(QFont("Microsoft YaHei UI", 14))
        desc.setStyleSheet(f"color: {self.theme.colors['text']};")
        desc.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(desc)
        
        layout.addWidget(header_widget)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(30)
        scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        if roles:
            role_section = self._create_persona_section("🎭 角色扮演", roles)
            scroll_layout.addWidget(role_section)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)
        
        self.chat_layout.insertWidget(0, self.welcome_widget)

    def clear_welcome(self):
        if hasattr(self, 'welcome_widget') and self.welcome_widget:
            self.welcome_widget.deleteLater()
            self.welcome_widget = None
    
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
            timestamp=timestamp
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
            timestamp=datetime.now().isoformat()
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
    
    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
    
    def on_send_clicked(self):
        current_model = self.model_combo.currentText()
        if not current_model:
            QMessageBox.warning(self, "提示", "请先选择模型")
            return
        
        text = self.input_text.toPlainText().strip()
        if text:
            self.input_text.clear()
            self.send_message.emit(text)
    
    @Slot(str)
    def set_title(self, title: str):
        self.title_label.setText(title)
    
    @Slot(bool)
    def set_send_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
        self.input_text.setEnabled(enabled)
        if enabled:
            self.send_btn.setText("发送")
            self.input_text.setPlaceholderText("输入消息，按 Enter 发送...")
        else:
            self.send_btn.setText("生成中...")
            self.input_text.setPlaceholderText("AI 正在回复中...")
    
    def update_models(self, models: list):
        """更新模型列表"""
        current = self.model_combo.currentText()
        self.model_combo.clear()
        
        # 存储模型名称映射（显示名称 -> ollama 完整名称）
        self.model_name_map = {}
        
        for model in models:
            if isinstance(model, dict):
                display_name = model.get('name', '')
                ollama_name = model.get('ollama_name', display_name)
                self.model_combo.addItem(display_name)
                self.model_name_map[display_name] = ollama_name
            else:
                self.model_combo.addItem(model)
                self.model_name_map[model] = model
        
        if current:
            index = self.model_combo.findText(current)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
    
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