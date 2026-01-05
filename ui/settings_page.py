import logging
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QStackedWidget, QButtonGroup,
    QTabWidget, QSizePolicy, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QPixmap

from .themes import get_theme_manager, THEMES
from .components import StatusIndicator, ModelCard

logger = logging.getLogger(__name__)


class ModelCategoryTab(QWidget):
    """模型分类标签页"""
    
    download_clicked = Signal(str, str)
    load_clicked = Signal(str)
    uninstall_clicked = Signal(str)
    
    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self.category = category
        self.theme = get_theme_manager()
        self.model_cards = {}
        self.available_vram_gb = 0  # 可用显存
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.container = QWidget()
        self.models_layout = QVBoxLayout(self.container)
        self.models_layout.setContentsMargins(5, 5, 5, 5)
        self.models_layout.setSpacing(10)
        self.models_layout.addStretch()
        
        scroll.setWidget(self.container)
        layout.addWidget(scroll)
        
        self.apply_theme()
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        self.setStyleSheet(f"background-color: transparent;")
        self.container.setStyleSheet(f"background-color: transparent;")
    
    def update_models(self, models: list, installed_models: list, downloading_models: dict = None):
        """更新模型列表
        
        Args:
            models: 推荐模型列表
            installed_models: Ollama 已安装的模型列表
            downloading_models: 正在下载的模型状态 {model_name: {"percent": 0, "text": "xxx"}}
        """
        if downloading_models is None:
            downloading_models = {}
        
        # 清空现有卡片
        while self.models_layout.count() > 1:
            item = self.models_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.model_cards.clear()
        
        if not models:
            c = self.theme.colors
            empty_label = QLabel("暂无可用模型")
            empty_label.setFont(QFont("Microsoft YaHei UI", 12))
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"color: {c['text_dim']}; padding: 40px;")
            self.models_layout.insertWidget(0, empty_label)
            return
        
        installed_set = self._build_installed_set(installed_models)
        
        for model_info in models:
            name = model_info.get('name', '')
            if not name:
                continue
            
            is_installed = self._check_model_installed(name, model_info, installed_set)
            
            # 传入显存信息
            card = ModelCard(name, model_info, is_installed, self.available_vram_gb)
            card.download_clicked.connect(self._on_download)
            card.load_clicked.connect(self.load_clicked.emit)
            card.uninstall_clicked.connect(self.uninstall_clicked.emit)
            
            self.model_cards[name] = card
            self.models_layout.insertWidget(self.models_layout.count() - 1, card)
            
            # 恢复下载状态
            if name in downloading_models:
                status = downloading_models[name]
                card.start_download()
                card.update_progress(status["percent"], status["text"])
    
    def set_available_vram(self, vram_gb: float):
        """设置可用显存"""
        self.available_vram_gb = vram_gb

    def _build_installed_set(self, installed_models: list) -> set:
        """构建已安装模型的匹配集合"""
        installed_set = set()
        
        for m in installed_models:
            # 获取完整的 ollama 名称（用于匹配）
            ollama_name = m.get('ollama_name', '') or m.get('name', '')
            if not ollama_name:
                continue
            
            # 添加完整名称（包含 :latest）
            installed_set.add(ollama_name.lower())
            
            # 也添加不带标签的版本
            base_name = ollama_name.split(':')[0]
            installed_set.add(base_name.lower())
        
        return installed_set

    def _check_model_installed(self, model_name: str, model_info: dict, installed_set: set) -> bool:
        """检查模型是否已安装"""
        quantizations = model_info.get('quantizations', [])
        
        for quant in quantizations:
            # 标准化量化版本（统一大小写）
            quant_lower = quant.lower()
            quant_upper = quant.upper()
            
            # 尝试多种可能的命名格式
            possible_names = [
                f"{model_name}-{quant}:latest",  # 标准格式带标签
                f"{model_name}-{quant}",  # 标准格式不带标签
                f"{model_name}-{quant_lower}:latest",  # 小写量化
                f"{model_name}-{quant_lower}",
                f"{model_name}-{quant_upper}:latest",  # 大写量化
                f"{model_name}-{quant_upper}",
            ]
            
            # 检查所有可能的名称
            for name in possible_names:
                if name.lower() in installed_set:
                    return True
        
        return False

    def _generate_possible_ollama_names(self, model_name: str, model_info: dict) -> list:
        """生成模型可能的 ollama 名称列表"""
        names = []
        
        # 基础名称
        base_name = model_name.lower()
        names.append(base_name)
        
        # 简化名称
        simple_name = base_name.replace('-', '').replace('.', '').replace('_', '')
        names.append(simple_name)
        
        # 带下划线的版本
        underscore_name = ''.join(c if c.isalnum() else '_' for c in base_name).strip('_')
        names.append(underscore_name)
        
        # 遍历所有量化版本
        quantizations = model_info.get('quantizations', [])
        for quant in quantizations:
            quant_lower = quant.lower().replace('_', '')
            
            # 各种组合
            names.append(f"{simple_name}_{quant_lower}")
            names.append(f"{underscore_name}_{quant_lower}")
            names.append(f"{simple_name}{quant_lower}")
            
            # 带原始格式的量化
            quant_original = quant.lower()
            names.append(f"{simple_name}_{quant_original}")
            names.append(f"{underscore_name}_{quant_original}")
        
        # 去重并返回
        return list(set(names))
    
    def _on_download(self, model_name: str, quantization: str):
        self.download_clicked.emit(model_name, quantization)
    
    def get_card(self, model_name: str):
        return self.model_cards.get(model_name)
    
    def start_download(self, model_name: str):
        if model_name in self.model_cards:
            self.model_cards[model_name].start_download()
    
    def update_progress(self, model_name: str, percent: int, text: str):
        if model_name in self.model_cards:
            self.model_cards[model_name].update_progress(percent, text)
    
    def finish_download(self, model_name: str, success: bool):
        if model_name in self.model_cards:
            self.model_cards[model_name].finish_download(success)


class SettingsPage(QWidget):
    """设置页面"""
    
    back_clicked = Signal()
    start_ollama = Signal()
    refresh_status = Signal()
    download_model = Signal(str, str)  # model_name, quantization
    load_model = Signal(str)
    uninstall_model = Signal(str)
    theme_changed = Signal(str)
    personal_changed = Signal(str, str, str, list, int)  # user_name, avatar_path, avatar_color, backgrounds, interval
    persona_added = Signal(str, str, str, str, str, str, str, list, str, list, bool)  # key, name, type, icon, desc, prompt, icon_path, backgrounds, greeting, scenarios, enable_suggestions
    persona_edited = Signal(str, str, str, str, str, str, str, list, str, list, bool)  # key, name, type, icon, desc, prompt, icon_path, backgrounds, greeting, scenarios, enable_suggestions
    persona_deleted = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        from core.logger import get_logger
        logger = get_logger('settings')
        
        self.theme = get_theme_manager()
        logger.info(f"SettingsPage 初始化，当前主题: {self.theme.current.get('name', 'unknown')}")
        
        self.model_cards = {}
        self.category_tabs = {}
        self.hardware_info = {}
        self._installed_models = []
        self._downloading_models = {}
        self.personas = {}
        
        # 头像和名称设置
        self.user_name = "我"
        self.user_avatar_path = None
        self.user_avatar_color = "#007AFF"
        self.chat_backgrounds = []
        self.background_interval = 5
        
        # 加载 debug 配置
        self.debug_mode = self._load_debug_config()

        self._load_personal_settings()
        self.setup_ui()
        
        # 连接主题变更信号
        self.theme.theme_changed.connect(self.apply_theme)
        logger.info("已连接 theme_changed 信号到 apply_theme 方法")
    
    def _load_debug_config(self) -> bool:
        """加载 debug 配置"""
        import json
        import sys
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_path = os.path.join(base_dir, 'config.json')
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config.get('debug', False)
        except Exception as e:
            print(f"加载 debug 配置失败: {e}")
        
        return False
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.create_nav(layout)
        self.create_scrollable_content(layout)
        self.apply_theme()
    
    def create_nav(self, parent_layout):
        c = self.theme.colors
        self.nav = QWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(220)
        
        layout = QVBoxLayout(self.nav)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(8)
        
        self.back_btn = QPushButton("← 返回对话")
        self.back_btn.setFont(QFont("Microsoft YaHei UI", 13))
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self.back_btn)
        
        layout.addSpacing(20)
        
        self.nav_title = QLabel("设置")
        self.nav_title.setStyleSheet(f"color: {c['text']};")
        self.nav_title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Bold))
        layout.addWidget(self.nav_title)
        
        layout.addSpacing(20)
        
        self.nav_group = QButtonGroup(self)
        
        self.nav_ollama = SettingsNavItem("模型引擎", "🔧")
        self.nav_ollama.setChecked(True)
        self.nav_group.addButton(self.nav_ollama, 0)
        self.nav_ollama.clicked.connect(lambda: self.scroll_to_section(0))
        layout.addWidget(self.nav_ollama)
        
        self.nav_system = SettingsNavItem("系统信息", "💻")
        self.nav_group.addButton(self.nav_system, 1)
        self.nav_system.clicked.connect(lambda: self.scroll_to_section(1))
        layout.addWidget(self.nav_system)
        
        self.nav_models = SettingsNavItem("模型管理", "📦")
        self.nav_group.addButton(self.nav_models, 2)
        self.nav_models.clicked.connect(lambda: self.scroll_to_section(2))
        layout.addWidget(self.nav_models)
        
        self.nav_theme = SettingsNavItem("主题设置", "🎨")
        self.nav_group.addButton(self.nav_theme, 3)
        self.nav_theme.clicked.connect(lambda: self.scroll_to_section(3))
        layout.addWidget(self.nav_theme)

        self.nav_personal = SettingsNavItem("个性化", "👤")
        self.nav_group.addButton(self.nav_personal, 4)
        self.nav_personal.clicked.connect(lambda: self.scroll_to_section(4))
        layout.addWidget(self.nav_personal)

        self.nav_personas = SettingsNavItem("助手管理", "🎭")
        self.nav_group.addButton(self.nav_personas, 5)
        self.nav_personas.clicked.connect(lambda: self.scroll_to_section(5))
        layout.addWidget(self.nav_personas)

        layout.addStretch()
        
        version = QLabel("版本 1.0.0")
        version.setStyleSheet(f"color: {c['text_secondary']};")
        version.setFont(QFont("Microsoft YaHei UI", 10))
        layout.addWidget(version)
        
        parent_layout.addWidget(self.nav)
    
    def create_personal_page(self):
        """创建个性化设置页面"""
        page, layout, container = self.create_page_container("个性化设置")
        
        c = self.theme.colors
        
        # 用户设置卡片
        user_card = QFrame()
        user_card.setObjectName("personalCard")
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(25, 20, 25, 25)
        user_layout.setSpacing(15)
        
        user_title = QLabel("用户设置")
        user_title.setStyleSheet(f"color: {c['text']};")
        user_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        user_layout.addWidget(user_title)
        
        # 头像区域
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(15)
        
        self.user_avatar_preview = QLabel("👤")
        self.user_avatar_preview.setFixedSize(70, 70)
        self.user_avatar_preview.setAlignment(Qt.AlignCenter)
        self.user_avatar_preview.setFont(QFont("Segoe UI Emoji", 32))
        avatar_row.addWidget(self.user_avatar_preview)
        
        avatar_btn_layout = QVBoxLayout()
        avatar_btn_layout.setSpacing(8)
        
        self.user_avatar_btn = QPushButton("上传图片")
        self.user_avatar_btn.setFixedSize(100, 32)
        self.user_avatar_btn.setCursor(Qt.PointingHandCursor)
        self.user_avatar_btn.clicked.connect(self._select_user_avatar)
        avatar_btn_layout.addWidget(self.user_avatar_btn)
        
        self.user_color_btn = QPushButton("选择颜色")
        self.user_color_btn.setFixedSize(100, 32)
        self.user_color_btn.setCursor(Qt.PointingHandCursor)
        self.user_color_btn.clicked.connect(self._select_user_color)
        avatar_btn_layout.addWidget(self.user_color_btn)
        
        self.user_avatar_clear_btn = QPushButton("恢复默认")
        self.user_avatar_clear_btn.setFixedSize(100, 32)
        self.user_avatar_clear_btn.setCursor(Qt.PointingHandCursor)
        self.user_avatar_clear_btn.clicked.connect(self._clear_user_avatar)
        avatar_btn_layout.addWidget(self.user_avatar_clear_btn)
        
        avatar_row.addLayout(avatar_btn_layout)
        avatar_row.addStretch()
        user_layout.addLayout(avatar_row)
        
        # 用户名称
        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        name_label = QLabel("显示名称:")
        name_label.setStyleSheet(f"color: {c['text']};")
        name_label.setFont(QFont("Microsoft YaHei UI", 11))
        name_row.addWidget(name_label)
        
        from PySide6.QtWidgets import QLineEdit
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("我")
        self.user_name_input.setFixedWidth(150)
        self.user_name_input.setText(self.user_name)
        self.user_name_input.textChanged.connect(self._on_user_name_changed)
        name_row.addWidget(self.user_name_input)
        name_row.addStretch()
        user_layout.addLayout(name_row)
        
        layout.addWidget(user_card)
        
        # 聊天背景卡片 - 添加边框
        bg_card = QFrame()
        bg_card.setObjectName("settingsCard")
        bg_card.setProperty("bordered", True)
        bg_layout = QVBoxLayout(bg_card)
        bg_layout.setContentsMargins(25, 20, 25, 25)
        bg_layout.setSpacing(15)
        
        bg_title = QLabel("聊天背景")
        bg_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        bg_layout.addWidget(bg_title)
        
        bg_desc = QLabel("添加多张背景图片，聊天时自动轮播")
        bg_desc.setFont(QFont("Microsoft YaHei UI", 11))
        bg_desc.setStyleSheet(f"color: {c['text_secondary']};")
        bg_layout.addWidget(bg_desc)
        
        # 背景图片预览区域
        self.bg_preview_container = QWidget()
        self.bg_preview_layout = QHBoxLayout(self.bg_preview_container)
        self.bg_preview_layout.setContentsMargins(0, 10, 0, 10)
        self.bg_preview_layout.setSpacing(10)
        self.bg_preview_layout.setAlignment(Qt.AlignLeft)
        bg_layout.addWidget(self.bg_preview_container)
        
        # 添加背景按钮
        bg_btn_row = QHBoxLayout()
        
        self.add_bg_btn = QPushButton("➕ 添加背景图片")
        self.add_bg_btn.setFixedSize(160, 38)
        self.add_bg_btn.setCursor(Qt.PointingHandCursor)
        self.add_bg_btn.setProperty("styled", True)
        self.add_bg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        self.add_bg_btn.clicked.connect(self._add_chat_background)
        bg_btn_row.addWidget(self.add_bg_btn)
        
        self.clear_bg_btn = QPushButton("🗑️ 清空全部")
        self.clear_bg_btn.setFixedSize(110, 38)
        self.clear_bg_btn.setCursor(Qt.PointingHandCursor)
        self.clear_bg_btn.setProperty("styled", True)
        self.clear_bg_btn.setProperty("secondary", True)
        self.clear_bg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                border: 2px solid {c['border']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
        """)
        self.clear_bg_btn.clicked.connect(self._clear_chat_backgrounds)
        bg_btn_row.addWidget(self.clear_bg_btn)
        
        bg_btn_row.addStretch()
        
        # 轮播间隔设置
        interval_label = QLabel("轮播间隔:")
        interval_label.setStyleSheet(f"color: {c['text']};")
        interval_label.setFont(QFont("Microsoft YaHei UI", 11))
        bg_btn_row.addWidget(interval_label)
        
        from PySide6.QtWidgets import QSpinBox
        self.bg_interval_spin = QSpinBox()
        self.bg_interval_spin.setRange(3, 60)
        self.bg_interval_spin.setValue(5)
        self.bg_interval_spin.setSuffix(" 秒")
        self.bg_interval_spin.setFixedWidth(80)
        self.bg_interval_spin.valueChanged.connect(self._on_bg_interval_changed)
        bg_btn_row.addWidget(self.bg_interval_spin)
        
        bg_layout.addLayout(bg_btn_row)
        
        layout.addWidget(bg_card)
        layout.addStretch()
        
        self.user_card = user_card
        self.bg_card = bg_card
        
        # 应用样式
        self._apply_personal_card_style()
        
        return page

    def _get_personal_settings_path(self):
        """获取个性化设置文件路径"""
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'personal_settings.json')

    def _load_personal_settings(self):
        """加载个性化设置"""
        from core.database import get_database
        
        try:
            db = get_database()
            self.user_name = db.get_personal_setting('user_name', '我')
            self.user_avatar_path = db.get_personal_setting('user_avatar_path')
            self.user_avatar_color = db.get_personal_setting('user_avatar_color', '#007AFF')
            self.chat_backgrounds = db.get_personal_setting('chat_backgrounds', [])
            self.background_interval = db.get_personal_setting('background_interval', 5)
        except Exception as e:
            print(f"加载个性化设置失败: {e}")
            # 使用默认值
            self.user_name = '我'
            self.user_avatar_path = None
            self.user_avatar_color = '#007AFF'
            self.chat_backgrounds = []
            self.background_interval = 5

    def _save_personal_settings(self):
        """保存个性化设置"""
        from core.database import get_database
        
        try:
            db = get_database()
            db.set_personal_setting('user_name', self.user_name)
            db.set_personal_setting('user_avatar_path', self.user_avatar_path)
            db.set_personal_setting('user_avatar_color', self.user_avatar_color)
            db.set_personal_setting('chat_backgrounds', self.chat_backgrounds)
            db.set_personal_setting('background_interval', self.background_interval)
        except Exception as e:
            print(f"保存个性化设置失败: {e}")

    def _apply_personal_card_style(self):
        """应用个性化卡片样式"""
        c = self.theme.colors
        
        # 应用描述标签样式
        for widget in self.scroll_container.findChildren(QLabel):
            if widget.objectName() == "descLabel":
                widget.setStyleSheet(f"color: {c['text_secondary']};")
        
        # 用户名输入框样式
        if hasattr(self, 'user_name_input'):
            self.user_name_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {c['input_bg']};
                    border: 2px solid {c['border']};
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: {c['text']};
                    font-size: 13px;
                }}
                QLineEdit:focus {{
                    border-color: {c['accent']};
                }}
                QLineEdit:hover {{
                    border-color: {c['text_dim']};
                }}
            """)
        
        # 轮播间隔输入框样式
        if hasattr(self, 'bg_interval_spin'):
            self.bg_interval_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {c['input_bg']};
                    border: 2px solid {c['border']};
                    border-radius: 8px;
                    padding: 6px 10px;
                    color: {c['text']};
                    font-size: 13px;
                }}
                QSpinBox:focus {{
                    border-color: {c['accent']};
                }}
                QSpinBox:hover {{
                    border-color: {c['text_dim']};
                }}
                QSpinBox::up-button {{
                    subcontrol-origin: border;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left: 1px solid {c['border']};
                    border-top-right-radius: 6px;
                    background-color: {c['bg_tertiary']};
                }}
                QSpinBox::up-button:hover {{
                    background-color: {c['hover']};
                }}
                QSpinBox::down-button {{
                    subcontrol-origin: border;
                    subcontrol-position: bottom right;
                    width: 20px;
                    border-left: 1px solid {c['border']};
                    border-bottom-right-radius: 6px;
                    background-color: {c['bg_tertiary']};
                }}
                QSpinBox::down-button:hover {{
                    background-color: {c['hover']};
                }}
                QSpinBox::up-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-bottom: 5px solid {c['text']};
                    width: 0px;
                    height: 0px;
                }}
                QSpinBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid {c['text']};
                    width: 0px;
                    height: 0px;
                }}
            """)


    def _update_user_avatar_preview(self):
        """更新用户头像预览"""
        from core.media_manager import get_media_manager
        from PySide6.QtGui import QPixmap
        c = self.theme.colors
        
        if self.user_avatar_path:
            # 使用 MediaManager 获取绝对路径
            media_manager = get_media_manager()
            absolute_path = media_manager.get_absolute_path(self.user_avatar_path)
            
            if os.path.exists(absolute_path):
                pixmap = QPixmap(absolute_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self.user_avatar_preview.setPixmap(pixmap)
                    self.user_avatar_preview.setText("")
                    self.user_avatar_preview.setStyleSheet("QLabel { border-radius: 35px; }")
                    return
        
        # 如果没有有效的图片路径，显示默认头像
        self.user_avatar_preview.setPixmap(QPixmap())
        self.user_avatar_preview.setText("👤")
        bg_color = self.user_avatar_color if self.user_avatar_color else c['bg_tertiary']
        self.user_avatar_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border-radius: 35px;
            }}
        """)

    def _add_chat_background(self):
        """添加聊天背景图片"""
        from PySide6.QtWidgets import QFileDialog
        from core.media_manager import get_media_manager
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_paths:
            # 使用 MediaManager 保存背景图片
            media_manager = get_media_manager()
            relative_paths = media_manager.save_backgrounds(file_paths)
            self.chat_backgrounds.extend(relative_paths)
            self._update_bg_preview()
            self._save_personal_settings()
            self._emit_personal_changed()

    def _clear_chat_backgrounds(self):
        """清空聊天背景"""
        self.chat_backgrounds = []
        self._update_bg_preview()
        self._save_personal_settings()
        self._emit_personal_changed()

    def _update_bg_preview(self):
        """更新背景图片预览"""
        from PySide6.QtGui import QPixmap
        from core.media_manager import get_media_manager
        
        # 清空现有预览
        while self.bg_preview_layout.count():
            item = self.bg_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        c = self.theme.colors
        media_manager = get_media_manager()
        
        for i, relative_path in enumerate(self.chat_backgrounds[:5]):  # 最多显示5张
            # 获取绝对路径
            absolute_path = media_manager.get_absolute_path(relative_path)
            
            frame = QFrame()
            frame.setFixedSize(80, 80)
            frame.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {c['border']};
                    border-radius: 8px;
                }}
            """)
            
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(2, 2, 2, 2)
            
            preview = QLabel()
            preview.setFixedSize(72, 56)
            if os.path.exists(absolute_path):
                pixmap = QPixmap(absolute_path)
                pixmap = pixmap.scaled(72, 56, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                preview.setPixmap(pixmap)
            else:
                preview.setText("❌")
                preview.setStyleSheet(f"color: {c['error']};")
            preview.setAlignment(Qt.AlignCenter)
            frame_layout.addWidget(preview)
            
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(72, 18)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['error']}80;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 10px;
                }}
            """)
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_bg(idx))
            frame_layout.addWidget(del_btn)
            
            self.bg_preview_layout.addWidget(frame)
        
        if len(self.chat_backgrounds) > 5:
            more_label = QLabel(f"+{len(self.chat_backgrounds) - 5}")
            more_label.setFont(QFont("Microsoft YaHei UI", 12))
            more_label.setStyleSheet(f"color: {c['text_secondary']};")
            self.bg_preview_layout.addWidget(more_label)

    def _remove_bg(self, index: int):
        """删除指定背景图片"""
        if 0 <= index < len(self.chat_backgrounds):
            self.chat_backgrounds.pop(index)
            self._update_bg_preview()
            self._save_personal_settings()
            self._emit_personal_changed()

    def _on_bg_interval_changed(self, value: int):
        """背景轮播间隔变化"""
        self.background_interval = value
        self._save_personal_settings()
        self._emit_personal_changed()

    def create_personas_page(self):
        """创建助手管理页面"""
        page, layout, container = self.create_page_container("助手管理")
        
        c = self.theme.colors
        
        # 添加助手按钮
        add_btn = QPushButton("➕ 添加助手")
        add_btn.setFixedSize(150, 40)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._show_add_persona_dialog)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        layout.addWidget(add_btn)
        
        # 助手列表滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.personas_container = QWidget()
        self.personas_layout = QVBoxLayout(self.personas_container)
        self.personas_layout.setContentsMargins(0, 10, 0, 10)
        self.personas_layout.setSpacing(12)
        self.personas_layout.addStretch()
        
        scroll.setWidget(self.personas_container)
        layout.addWidget(scroll, 1)
        
        self.personas_scroll = scroll

        self.personas_container.setStyleSheet("background-color: transparent;")
        scroll.setStyleSheet("background-color: transparent; border: none;")

        return page

    def update_personas(self, personas: dict):
        """更新助手列表 - 分类显示"""
        from core.logger import get_logger
        logger = get_logger('settings')
        
        logger.info(f"update_personas 被调用，助手数量: {len(personas)}")
        
        self.personas = personas
        
        # 分类助手
        assistants = {}
        roleplays = {}
        
        for key, persona in personas.items():
            persona_type = persona.get('type', 'assistant')  # 默认为协作助手
            if persona_type == 'roleplay':
                roleplays[key] = persona
            else:
                assistants[key] = persona
        
        logger.info(f"分类完成 - 协作助手: {len(assistants)}, 角色扮演: {len(roleplays)}")
        
        # 更新协作助手列表
        while self.assistants_layout.count() > 1:
            item = self.assistants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 确保默认助手置顶
        if 'default' in assistants:
            default_persona = assistants.pop('default')
            card = self._create_persona_card('default', default_persona)
            self.assistants_layout.insertWidget(self.assistants_layout.count() - 1, card)
        
        # 添加其他助手（按名称排序）
        sorted_assistants = sorted(assistants.items(), key=lambda x: x[1].get('name', ''))
        for key, persona in sorted_assistants:
            card = self._create_persona_card(key, persona)
            self.assistants_layout.insertWidget(self.assistants_layout.count() - 1, card)
        
        # 更新角色扮演列表（按名称排序）
        while self.roleplays_layout.count() > 1:
            item = self.roleplays_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        sorted_roleplays = sorted(roleplays.items(), key=lambda x: x[1].get('name', ''))
        for key, persona in sorted_roleplays:
            card = self._create_persona_card(key, persona)
            self.roleplays_layout.insertWidget(self.roleplays_layout.count() - 1, card)
        
        # 确保容器透明
        if hasattr(self, 'assistants_container'):
            self.assistants_container.setStyleSheet("background-color: transparent;")
        if hasattr(self, 'roleplays_container'):
            self.roleplays_container.setStyleSheet("background-color: transparent;")
        
        logger.info(f"助手卡片创建完成，准备应用当前主题样式")
        
        # 立即应用当前主题的样式到新创建的卡片
        # 使用 QTimer.singleShot 确保卡片已经完全添加到布局中
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._update_persona_cards_style)
    
    def _update_persona_cards_style(self):
        """更新所有助手卡片的样式（主题切换时调用）"""
        from core.logger import get_logger
        logger = get_logger('settings')
        
        c = self.theme.colors
        logger.info(f"开始更新助手卡片样式，当前主题: {self.theme.current.get('name', 'unknown')}")
        logger.debug(f"card_bg 颜色: {c['card_bg']}, text 颜色: {c['text']}")
        
        updated_count = 0
        
        # 查找所有助手卡片
        if hasattr(self, 'assistants_container'):
            cards = self.assistants_container.findChildren(QFrame, "personaCard")
            logger.info(f"在 assistants_container 中找到 {len(cards)} 个助手卡片")
            
            for card in cards:
                persona_type = card.property("persona_type")
                persona_key = card.property("persona_key")
                logger.debug(f"更新卡片: key={persona_key}, type={persona_type}")
                
                # 更新卡片背景和边框
                border_color = c['accent'] if persona_type == 'roleplay' else c['border']
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c['card_bg']};
                        border-radius: 12px;
                        border: 1px solid {border_color};
                    }}
                """)
                updated_count += 1
                
                # 更新卡片内的标签样式
                for label in card.findChildren(QLabel):
                    obj_name = label.objectName()
                    if obj_name == "personaName":
                        label.setStyleSheet(f"color: {c['text']}; background: transparent;")
                    elif obj_name == "personaDesc":
                        label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
                    elif obj_name == "personaType":
                        label.setStyleSheet(f"""
                            QLabel {{
                                color: {c['accent'] if persona_type == 'roleplay' else c['text_secondary']};
                                background-color: {c['accent']}15;
                                border-radius: 10px;
                                padding: 0 8px;
                            }}
                        """)
                    elif obj_name == "personaDefault":
                        label.setStyleSheet(f"""
                            QLabel {{
                                color: {c['accent']};
                                background-color: {c['accent']}20;
                                border-radius: 12px;
                            }}
                        """)
                    elif obj_name == "personaDebug":
                        label.setStyleSheet(f"""
                            QLabel {{
                                color: {c['warning']};
                                background-color: {c['warning']}20;
                                border-radius: 12px;
                            }}
                        """)
                
                # 更新按钮样式
                for btn in card.findChildren(QPushButton):
                    obj_name = btn.objectName()
                    if obj_name == "editBtn":
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {c['accent']}20;
                                border-radius: 20px;
                                font-size: 16px;
                            }}
                            QPushButton:hover {{
                                background-color: {c['accent']}40;
                            }}
                        """)
                    elif obj_name == "deleteBtn":
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {c['error']}20;
                                border-radius: 20px;
                                font-size: 16px;
                            }}
                            QPushButton:hover {{
                                background-color: {c['error']}40;
                            }}
                        """)
        else:
            logger.warning("assistants_container 不存在")
        
        # 同样处理角色扮演容器
        if hasattr(self, 'roleplays_container'):
            cards = self.roleplays_container.findChildren(QFrame, "personaCard")
            logger.info(f"在 roleplays_container 中找到 {len(cards)} 个角色卡片")
            
            for card in cards:
                persona_type = card.property("persona_type")
                persona_key = card.property("persona_key")
                logger.debug(f"更新卡片: key={persona_key}, type={persona_type}")
                
                # 更新卡片背景和边框
                border_color = c['accent'] if persona_type == 'roleplay' else c['border']
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c['card_bg']};
                        border-radius: 12px;
                        border: 1px solid {border_color};
                    }}
                """)
                updated_count += 1
                
                # 更新卡片内的标签样式
                for label in card.findChildren(QLabel):
                    obj_name = label.objectName()
                    if obj_name == "personaName":
                        label.setStyleSheet(f"color: {c['text']}; background: transparent;")
                    elif obj_name == "personaDesc":
                        label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
                    elif obj_name == "personaType":
                        label.setStyleSheet(f"""
                            QLabel {{
                                color: {c['accent'] if persona_type == 'roleplay' else c['text_secondary']};
                                background-color: {c['accent']}15;
                                border-radius: 10px;
                                padding: 0 8px;
                            }}
                        """)
                    elif obj_name == "personaDefault":
                        label.setStyleSheet(f"""
                            QLabel {{
                                color: {c['accent']};
                                background-color: {c['accent']}20;
                                border-radius: 12px;
                            }}
                        """)
                    elif obj_name == "personaDebug":
                        label.setStyleSheet(f"""
                            QLabel {{
                                color: {c['warning']};
                                background-color: {c['warning']}20;
                                border-radius: 12px;
                            }}
                        """)
                
                # 更新按钮样式
                for btn in card.findChildren(QPushButton):
                    obj_name = btn.objectName()
                    if obj_name == "editBtn":
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {c['accent']}20;
                                border-radius: 20px;
                                font-size: 16px;
                            }}
                            QPushButton:hover {{
                                background-color: {c['accent']}40;
                            }}
                        """)
                    elif obj_name == "deleteBtn":
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {c['error']}20;
                                border-radius: 20px;
                                font-size: 16px;
                            }}
                            QPushButton:hover {{
                                background-color: {c['error']}40;
                            }}
                        """)
        else:
            logger.warning("roleplays_container 不存在")
        
        logger.info(f"助手卡片样式更新完成，共更新 {updated_count} 个卡片")

    def _create_persona_card(self, key: str, persona: dict):
        """创建助手卡片"""
        c = self.theme.colors
        persona_type = persona.get('type', 'assistant')
    
        card = QFrame()
        card.setFixedHeight(100)
        card.setObjectName("personaCard")  # 设置对象名称以便后续查找
        card.setProperty("persona_key", key)  # 保存 key
        card.setProperty("persona_type", persona_type)  # 保存类型
        
        # 根据类型设置不同的边框颜色
        border_color = c['accent'] if persona_type == 'roleplay' else c['border']
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c['card_bg']};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # 图标（支持自定义图片）
        icon_label = QLabel()
        icon_label.setFixedSize(50, 50)
        icon_label.setAlignment(Qt.AlignCenter)
        
        icon_path = persona.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(icon_path).scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText(persona.get("icon", "🤖"))
            icon_label.setFont(QFont("Segoe UI Emoji", 28))
        
        layout.addWidget(icon_label)
        
        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # 名称和类型标签
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        
        name_label = QLabel(persona.get("name", "未知"))
        name_label.setObjectName("personaName")
        name_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        name_label.setStyleSheet(f"color: {c['text']}; background: transparent;")
        name_row.addWidget(name_label)
        
        # 类型标签
        type_label = QLabel("🎭 角色" if persona_type == 'roleplay' else "💼 助手")
        type_label.setObjectName("personaType")
        type_label.setFont(QFont("Microsoft YaHei UI", 10))
        type_label.setFixedHeight(20)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setStyleSheet(f"""
            QLabel {{
                color: {c['accent'] if persona_type == 'roleplay' else c['text_secondary']};
                background-color: {c['accent']}15 if persona_type == 'roleplay' else {c['bg_tertiary']};
                border-radius: 10px;
                padding: 0 8px;
            }}
        """)
        name_row.addWidget(type_label)
        name_row.addStretch()
        
        info_layout.addLayout(name_row)
        
        desc_label = QLabel(persona.get("description", ""))
        desc_label.setObjectName("personaDesc")
        desc_label.setFont(QFont("Microsoft YaHei UI", 11))
        desc_label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, 1)
        
        # 操作按钮（debug 模式下允许编辑默认助手）
        if key != "default" or self.debug_mode:
            # 编辑按钮
            edit_btn = QPushButton("✏️")
            edit_btn.setObjectName("editBtn")
            edit_btn.setFixedSize(40, 40)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent']}20;
                    border-radius: 20px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: {c['accent']}40;
                }}
            """)
            edit_btn.clicked.connect(lambda checked, k=key, p=persona: self._show_add_persona_dialog(k, p))
            layout.addWidget(edit_btn)
            
            # 删除按钮
            del_btn = QPushButton("🗑️")
            del_btn.setObjectName("deleteBtn")
            del_btn.setFixedSize(40, 40)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['error']}20;
                    border-radius: 20px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: {c['error']}40;
                }}
            """)
            del_btn.clicked.connect(lambda checked, k=key: self.persona_deleted.emit(k))
            layout.addWidget(del_btn)
            
            # debug 模式下显示标识
            if key == "default" and self.debug_mode:
                debug_label = QLabel("🔧")
                debug_label.setObjectName("personaDebug")
                debug_label.setFont(QFont("Segoe UI Emoji", 14))
                debug_label.setFixedSize(30, 24)
                debug_label.setAlignment(Qt.AlignCenter)
                debug_label.setToolTip("Debug 模式：允许编辑默认助手")
                debug_label.setStyleSheet(f"""
                    QLabel {{
                        color: {c['warning']};
                        background-color: {c['warning']}20;
                        border-radius: 12px;
                    }}
                """)
                layout.addWidget(debug_label)
        else:
            default_label = QLabel("默认")
            default_label.setObjectName("personaDefault")
            default_label.setFont(QFont("Microsoft YaHei UI", 10))
            default_label.setFixedSize(50, 24)
            default_label.setAlignment(Qt.AlignCenter)
            default_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['accent']};
                    background-color: {c['accent']}20;
                    border-radius: 12px;
                }}
            """)
            layout.addWidget(default_label)
        
        return card

    def _show_add_persona_dialog(self, edit_key: str = None, edit_data: dict = None, persona_type: str = None):
        """显示添加/编辑助手/角色对话框"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox, QLineEdit, QTextEdit, QGridLayout, QComboBox
        
        c = self.theme.colors
        is_edit = edit_key is not None
        
        # 确定类型
        if persona_type is None:
            persona_type = edit_data.get('type', 'assistant') if edit_data else 'assistant'
        
        dialog = QDialog(self)
        dialog_title = "编辑" if is_edit else "添加"
        dialog_title += "角色扮演" if persona_type == 'roleplay' else "协作助手"
        dialog.setWindowTitle(dialog_title)
        dialog.setFixedWidth(560)
        dialog.setMaximumHeight(700)  # 设置最大高度
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
            }}
            QLabel {{
                color: {c['text']};
                font-size: 13px;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {c['text']};
                margin-right: 8px;
            }}
        """)
        
        # 主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {c['bg']};
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
        
        # 滚动内容容器
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 类型固定，不显示选择（新建时根据传入的 persona_type 固定）
        self._current_persona_type = persona_type
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # 名称
        name_input = QLineEdit()
        name_input.setFixedHeight(36)
        name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c['input_bg']};
                border: 2px solid {c['border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {c['text']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent']};
            }}
            QLineEdit:hover {{
                border-color: {c['text_dim']};
            }}
        """)
        if persona_type == 'roleplay':
            name_input.setPlaceholderText("角色名称，如：猫娘阿里、霸道总裁")
        else:
            name_input.setPlaceholderText("助手名称，如：编程助手、写作助手")
        if is_edit and edit_data:
            name_input.setText(edit_data.get('name', ''))
        form_layout.addRow("名称:", name_input)
        
        # 描述
        desc_input = QLineEdit()
        desc_input.setFixedHeight(36)
        desc_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c['input_bg']};
                border: 2px solid {c['border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {c['text']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent']};
            }}
            QLineEdit:hover {{
                border-color: {c['text_dim']};
            }}
        """)
        if persona_type == 'roleplay':
            desc_input.setPlaceholderText("角色特点，如：可爱的猫娘，喜欢撒娇")
        else:
            desc_input.setPlaceholderText("助手功能，如：帮助编写和调试代码")
        if is_edit and edit_data:
            desc_input.setText(edit_data.get('description', ''))
        form_layout.addRow("描述:", desc_input)
        
        layout.addLayout(form_layout)
        
        # 图标选择区域
        icon_label = QLabel("选择图标:")
        icon_label.setStyleSheet(f"color: {c['text']};")
        icon_label.setFont(QFont("Microsoft YaHei UI", 11))
        layout.addWidget(icon_label)
        
        icon_container = QWidget()
        icon_grid = QGridLayout(icon_container)
        icon_grid.setSpacing(8)
        
        # 根据类型显示不同的预设图标
        if persona_type == 'roleplay':
            # 角色扮演图标
            default_emojis = ["🐱", "👸", "🧙", "🦸", "🎭", "🐶", "🦊", "🐰", "🐻", "🦄", "🧝", "👨‍🎤", "👩‍🎤", "🤴", "👑", "⚔️"]
        else:
            # 协作助手图标
            default_emojis = ["🤖", "👔", "💼", "📝", "💻", "🔧", "📊", "🎨", "🌐", "📚", "🔬", "👨‍🔬", "👨‍🎨", "👨‍💻", "👨‍🏫", "🎓"]
        
        self._selected_icon = edit_data.get('icon', default_emojis[0]) if (is_edit and edit_data) else default_emojis[0]
        self._selected_icon_path = edit_data.get('icon_path') if (is_edit and edit_data) else None
        self._selected_icon_pixmap = None  # 初始化 pixmap 属性
        self._icon_buttons = []
        
        for i, emoji in enumerate(default_emojis):
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.setFont(QFont("Segoe UI Emoji", 18))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(emoji == self._selected_icon and not self._selected_icon_path)
            btn.clicked.connect(lambda checked, e=emoji, b=btn: self._on_icon_selected(e, b))
            self._icon_buttons.append(btn)
            icon_grid.addWidget(btn, i // 8, i % 8)
        
        # 自定义上传按钮
        upload_btn = QPushButton("📁")
        upload_btn.setFixedSize(40, 40)
        upload_btn.setFont(QFont("Segoe UI Emoji", 18))
        upload_btn.setCursor(Qt.PointingHandCursor)
        upload_btn.setToolTip("上传自定义图片")
        upload_btn.clicked.connect(lambda: self._upload_persona_icon(dialog))
        icon_grid.addWidget(upload_btn, 2, 0)
        
        # 自定义图片预览
        self._custom_icon_preview = QLabel()
        self._custom_icon_preview.setFixedSize(40, 40)
        self._custom_icon_preview.setAlignment(Qt.AlignCenter)
        self._custom_icon_preview.setStyleSheet(f"border: 1px solid {c['border']}; border-radius: 8px;")
        if self._selected_icon_path:
            from PySide6.QtGui import QPixmap
            from core.media_manager import get_media_manager
            media_manager = get_media_manager()
            # 转换为绝对路径
            abs_path = media_manager.get_absolute_path(self._selected_icon_path)
            if abs_path and os.path.exists(abs_path):
                pixmap = QPixmap(abs_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._custom_icon_preview.setPixmap(pixmap)
        icon_grid.addWidget(self._custom_icon_preview, 2, 1)
        
        layout.addWidget(icon_container)
        self._update_icon_button_styles(c)
        
        # 提示词
        prompt_label = QLabel("系统提示词:")
        prompt_label.setStyleSheet(f"color: {c['text']};")
        prompt_label.setFont(QFont("Microsoft YaHei UI", 11))
        layout.addWidget(prompt_label)
        
        prompt_input = QTextEdit()
        prompt_input.setPlaceholderText("定义助手的行为方式...\n\n例如：你是一只可爱的猫娘，名叫阿里。")
        prompt_input.setMinimumHeight(120)
        prompt_input.setMaximumHeight(180)
        prompt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['input_bg']};
                border: 2px solid {c['border']};
                border-radius: 8px;
                padding: 10px;
                color: {c['text']};
                font-size: 13px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {c['accent']};
            }}
            QTextEdit:hover {{
                border-color: {c['text_dim']};
            }}
        """)
        if is_edit and edit_data:
            prompt_input.setText(edit_data.get('system_prompt', ''))
        layout.addWidget(prompt_input)
        
        # 角色对话专属字段（仅角色扮演类型显示）
        self._greeting_input = None
        self._scenarios_input = None
        self._enable_suggestions_checkbox = None
        
        if persona_type == 'roleplay':
            # 问候语
            greeting_label = QLabel("问候语:")
            greeting_label.setStyleSheet(f"color: {c['text']};")
            greeting_label.setFont(QFont("Microsoft YaHei UI", 11))
            layout.addWidget(greeting_label)
            
            self._greeting_input = QTextEdit()
            self._greeting_input.setPlaceholderText("角色的开场问候语...\n\n例如：你好主人～我是你的专属猫娘♡")
            self._greeting_input.setMinimumHeight(80)
            self._greeting_input.setMaximumHeight(100)
            self._greeting_input.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {c['input_bg']};
                    border: 2px solid {c['border']};
                    border-radius: 8px;
                    padding: 10px;
                    color: {c['text']};
                    font-size: 13px;
                    line-height: 1.5;
                }}
                QTextEdit:focus {{
                    border-color: {c['accent']};
                }}
                QTextEdit:hover {{
                    border-color: {c['text_dim']};
                }}
            """)
            if is_edit and edit_data:
                self._greeting_input.setText(edit_data.get('greeting', ''))
            layout.addWidget(self._greeting_input)
            
            # 场景选项
            scenarios_label = QLabel("场景选项（每行一个）:")
            scenarios_label.setStyleSheet(f"color: {c['text']};")
            scenarios_label.setFont(QFont("Microsoft YaHei UI", 11))
            layout.addWidget(scenarios_label)
            
            self._scenarios_input = QTextEdit()
            self._scenarios_input.setPlaceholderText("每行一个场景选项...\n\n例如：\n今天想做什么呢？\n要不要一起玩游戏？\n给主人按摩放松一下～")
            self._scenarios_input.setMinimumHeight(100)
            self._scenarios_input.setMaximumHeight(120)
            self._scenarios_input.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {c['input_bg']};
                    border: 2px solid {c['border']};
                    border-radius: 8px;
                    padding: 10px;
                    color: {c['text']};
                    font-size: 13px;
                    line-height: 1.5;
                }}
                QTextEdit:focus {{
                    border-color: {c['accent']};
                }}
                QTextEdit:hover {{
                    border-color: {c['text_dim']};
                }}
            """)
            if is_edit and edit_data:
                scenarios = edit_data.get('scenarios', [])
                if scenarios:
                    self._scenarios_input.setText('\n'.join(scenarios))
            layout.addWidget(self._scenarios_input)
            
            # 启用推荐回复
            from PySide6.QtWidgets import QCheckBox
            self._enable_suggestions_checkbox = QCheckBox("启用智能推荐回复（AI 回复后自动生成推荐选项）")
            self._enable_suggestions_checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {c['text']};
                    font-size: 13px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 20px;
                    height: 20px;
                    border: 2px solid {c['border']};
                    border-radius: 4px;
                    background-color: {c['input_bg']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {c['accent']};
                    border-color: {c['accent']};
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEzLjMzMzMgNEw2IDExLjMzMzNMMi42NjY2NyA4IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
                }}
                QCheckBox::indicator:hover {{
                    border-color: {c['accent']};
                }}
            """)
            self._enable_suggestions_checkbox.setChecked(
                edit_data.get('enable_suggestions', True) if (is_edit and edit_data) else True
            )
            layout.addWidget(self._enable_suggestions_checkbox)
        
        # 背景图片管理
        bg_label = QLabel("聊天背景图片:")
        bg_label.setStyleSheet(f"color: {c['text']};")
        bg_label.setFont(QFont("Microsoft YaHei UI", 11))
        layout.addWidget(bg_label)
        
        bg_container = QWidget()
        bg_layout = QVBoxLayout(bg_container)
        bg_layout.setSpacing(10)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        
        # 背景图片列表
        self._persona_backgrounds = []
        if is_edit and edit_data:
            bg_str = edit_data.get('background_images', '')
            if bg_str:
                try:
                    import json
                    self._persona_backgrounds = json.loads(bg_str)
                except:
                    self._persona_backgrounds = []
        
        # 背景图片预览区域（横向滚动）
        bg_scroll = QScrollArea()
        bg_scroll.setWidgetResizable(True)
        bg_scroll.setFixedHeight(110)
        bg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        bg_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bg_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {c['border']};
                border-radius: 8px;
                background-color: {c['bg_tertiary']};
            }}
            QScrollBar:horizontal {{
                background-color: transparent;
                height: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {c['scrollbar']};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {c['scrollbar_hover']};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        
        self._bg_preview_widget = QWidget()
        self._bg_preview_layout = QHBoxLayout(self._bg_preview_widget)
        self._bg_preview_layout.setSpacing(10)
        self._bg_preview_layout.setContentsMargins(10, 10, 10, 10)
        self._bg_preview_layout.setAlignment(Qt.AlignLeft)
        
        bg_scroll.setWidget(self._bg_preview_widget)
        bg_layout.addWidget(bg_scroll)
        
        self._update_persona_bg_preview()
        
        # 按钮行
        bg_btn_row = QHBoxLayout()
        bg_btn_row.setSpacing(10)
        
        add_bg_btn = QPushButton("➕ 添加背景")
        add_bg_btn.setFixedHeight(34)
        add_bg_btn.setCursor(Qt.PointingHandCursor)
        add_bg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        add_bg_btn.clicked.connect(lambda: self._add_persona_background(dialog))
        bg_btn_row.addWidget(add_bg_btn)
        
        clear_bg_btn = QPushButton("清空全部")
        clear_bg_btn.setFixedHeight(34)
        clear_bg_btn.setCursor(Qt.PointingHandCursor)
        clear_bg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text_secondary']};
                border-radius: 8px;
                font-size: 12px;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {c['text']};
            }}
        """)
        clear_bg_btn.clicked.connect(self._clear_persona_backgrounds)
        bg_btn_row.addWidget(clear_bg_btn)
        
        bg_btn_row.addStretch()
        bg_layout.addLayout(bg_btn_row)
        
        layout.addWidget(bg_container)
        
        # 将滚动内容设置到滚动区域
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 按钮容器（固定在底部，不滚动）
        button_container = QWidget()
        button_container.setStyleSheet(f"background-color: {c['bg']}; border-top: 1px solid {c['border']};")
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(25, 15, 25, 15)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("保存" if is_edit else "添加")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        
        # 美化按钮样式
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        ok_btn.setFixedHeight(38)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 25px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        cancel_btn.setFixedHeight(38)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 8px;
                font-size: 13px;
                padding: 0 25px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        button_layout.addWidget(buttons)
        
        # 将按钮容器添加到主布局
        main_layout.addWidget(button_container)
        
        if dialog.exec() == QDialog.Accepted:
            name = name_input.text().strip()
            desc = desc_input.text().strip()
            prompt = prompt_input.toPlainText().strip()
            persona_type = self._current_persona_type  # 获取类型
            
            # 获取角色对话字段
            greeting = ""
            scenarios = []
            enable_suggestions = True
            
            if persona_type == 'roleplay':
                if self._greeting_input:
                    greeting = self._greeting_input.toPlainText().strip()
                if self._scenarios_input:
                    scenarios_text = self._scenarios_input.toPlainText().strip()
                    if scenarios_text:
                        scenarios = [s.strip() for s in scenarios_text.split('\n') if s.strip()]
                if self._enable_suggestions_checkbox:
                    enable_suggestions = self._enable_suggestions_checkbox.isChecked()
            
            if name and prompt:
                from core.media_manager import get_media_manager
                media_manager = get_media_manager()
                
                # 处理图标路径
                icon_path_to_save = ""
                # 优先使用裁剪后的 QPixmap（新上传的图标）
                if hasattr(self, '_selected_icon_pixmap') and self._selected_icon_pixmap:
                    if is_edit:
                        icon_path_to_save = media_manager.save_persona_icon(self._selected_icon_pixmap, edit_key)
                    else:
                        # 新建时使用临时 key，稍后会被替换
                        from datetime import datetime
                        temp_key = f"persona_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        icon_path_to_save = media_manager.save_persona_icon(self._selected_icon_pixmap, temp_key)
                # 兼容旧的文件路径方式
                elif self._selected_icon_path:
                    # 保留原有的自定义图标路径（编辑时未更改图标）
                    icon_path_to_save = self._selected_icon_path
                # 编辑模式下，如果原本有自定义图标但没有重新选择，保留原图标
                elif is_edit and edit_data and edit_data.get('icon_path'):
                    icon_path_to_save = edit_data.get('icon_path')
                
                if is_edit:
                    # 编辑模式
                    self.persona_edited.emit(
                        edit_key, name, persona_type,
                        self._selected_icon if not icon_path_to_save else "📷",
                        desc, prompt,
                        icon_path_to_save,
                        self._persona_backgrounds,  # 背景图片列表
                        greeting,  # 问候语
                        scenarios,  # 场景选项
                        enable_suggestions  # 启用推荐
                    )
                else:
                    # 添加模式 - 使用时间戳生成唯一标识
                    from datetime import datetime
                    key = f"persona_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.persona_added.emit(
                        key, name, persona_type,
                        self._selected_icon if not icon_path_to_save else "📷",
                        desc, prompt,
                        icon_path_to_save,
                        self._persona_backgrounds,  # 背景图片列表
                        greeting,  # 问候语
                        scenarios,  # 场景选项
                        enable_suggestions  # 启用推荐
                    )
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "提示", "请填写名称和提示词")

    def _on_icon_selected(self, emoji: str, btn):
        """选择预设图标"""
        self._selected_icon = emoji
        self._selected_icon_path = None
        if hasattr(self, '_selected_icon_pixmap'):
            self._selected_icon_pixmap = None
        self._custom_icon_preview.setPixmap(QPixmap())
        
        # 取消所有按钮的选中状态
        for icon_btn in self._icon_buttons:
            icon_btn.setChecked(False)
        
        # 选中当前按钮
        btn.setChecked(True)
        
        # 恢复自定义图标预览框的默认样式
        c = self.theme.colors
        self._custom_icon_preview.setStyleSheet(f"border: 1px solid {c['border']}; border-radius: 8px;")
        
        # 更新样式
        self._update_icon_button_styles(c)

    def _update_icon_button_styles(self, c):
        """更新图标按钮样式"""
        for btn in self._icon_buttons:
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['accent']};
                        border: 2px solid {c['accent']};
                        border-radius: 8px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['bg_tertiary']};
                        border: 1px solid {c['border']};
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        border-color: {c['accent']};
                    }}
                """)

    def _upload_persona_icon(self, dialog):
        """上传助手自定义图标"""
        from PySide6.QtWidgets import QFileDialog
        from .image_crop_dialog import ImageCropDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            dialog, "选择图标", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            # 打开裁剪对话框
            crop_dialog = ImageCropDialog(file_path, dialog, title="裁剪助手图标")
            if crop_dialog.exec() == QDialog.Accepted:
                cropped_image = crop_dialog.get_cropped_image()
                if cropped_image:
                    # 暂存裁剪后的图片，稍后在保存时使用 MediaManager 处理
                    self._selected_icon_pixmap = cropped_image
                    self._selected_icon_path = None  # 清除文件路径标记
                    
                    # 显示预览（缩放到 36x36）
                    preview_pixmap = cropped_image.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self._custom_icon_preview.setPixmap(preview_pixmap)
                    
                    # 取消所有预设图标的选中状态
                    for btn in self._icon_buttons:
                        btn.setChecked(False)
                    
                    # 高亮自定义图标预览框
                    c = self.theme.colors
                    self._custom_icon_preview.setStyleSheet(f"""
                        border: 2px solid {c['accent']};
                        border-radius: 8px;
                        background-color: {c['accent']}20;
                    """)
                    self._update_icon_button_styles(c)
    
    def _add_persona_background(self, dialog):
        """添加助手背景图片"""
        from PySide6.QtWidgets import QFileDialog
        from core.media_manager import get_media_manager
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            dialog, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_paths:
            # 使用 MediaManager 保存背景图片
            media_manager = get_media_manager()
            for path in file_paths:
                relative_path = media_manager.save_background(path)
                if relative_path and relative_path not in self._persona_backgrounds:
                    self._persona_backgrounds.append(relative_path)
            self._update_persona_bg_preview()
    
    def _clear_persona_backgrounds(self):
        """清空助手背景图片"""
        self._persona_backgrounds = []
        self._update_persona_bg_preview()
    
    def _update_persona_bg_preview(self):
        """更新助手背景图片预览"""
        from PySide6.QtGui import QPixmap
        from core.media_manager import get_media_manager
        
        # 清空现有预览
        while self._bg_preview_layout.count():
            item = self._bg_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        c = self.theme.colors
        media_manager = get_media_manager()
        
        if not self._persona_backgrounds:
            # 显示空状态
            empty_label = QLabel("未添加背景图片")
            empty_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self._bg_preview_layout.addWidget(empty_label)
        else:
            # 显示所有背景图片预览
            for i, relative_path in enumerate(self._persona_backgrounds):
                # 获取绝对路径
                absolute_path = media_manager.get_absolute_path(relative_path)
                
                frame = QFrame()
                frame.setFixedSize(80, 80)
                frame.setStyleSheet(f"""
                    QFrame {{
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                        background-color: {c['bg']};
                    }}
                """)
                
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(2, 2, 2, 2)
                frame_layout.setSpacing(2)
                
                # 图片预览
                preview = QLabel()
                preview.setFixedSize(72, 56)
                preview.setAlignment(Qt.AlignCenter)
                
                if os.path.exists(absolute_path):
                    pixmap = QPixmap(absolute_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(72, 56, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                        preview.setPixmap(pixmap)
                    else:
                        preview.setText("❌")
                        preview.setStyleSheet(f"color: {c['error']};")
                else:
                    preview.setText("❌")
                    preview.setStyleSheet(f"color: {c['error']};")
                frame_layout.addWidget(preview)
                
                # 删除按钮
                del_btn = QPushButton("✕")
                del_btn.setFixedSize(72, 18)
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['error']}80;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {c['error']};
                    }}
                """)
                del_btn.clicked.connect(lambda checked, idx=i: self._remove_persona_background(idx))
                frame_layout.addWidget(del_btn)
                
                self._bg_preview_layout.addWidget(frame)
    
    def _remove_persona_background(self, index):
        """移除背景图片"""
        if 0 <= index < len(self._persona_backgrounds):
            self._persona_backgrounds.pop(index)
            self._update_persona_bg_preview()

    def _select_user_avatar(self):
        """选择用户头像"""
        from PySide6.QtWidgets import QFileDialog
        from .image_crop_dialog import ImageCropDialog
        from core.media_manager import get_media_manager
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            # 打开裁剪对话框
            crop_dialog = ImageCropDialog(file_path, self)
            if crop_dialog.exec() == QDialog.Accepted:
                cropped_image = crop_dialog.get_cropped_image()
                if cropped_image:
                    # 使用 MediaManager 保存头像
                    media_manager = get_media_manager()
                    relative_path = media_manager.save_user_avatar(cropped_image, "user_avatar.png")
                    
                    if relative_path:
                        self.user_avatar_path = relative_path
                        self.user_avatar_color = None
                        self._update_user_avatar_preview()
                        self._save_personal_settings()
                        self._emit_personal_changed()

    def _clear_user_avatar(self):
        """清除用户头像"""
        self.user_avatar_path = None
        self.user_avatar_color = "#007AFF"
        self._update_user_avatar_preview()
        self._save_personal_settings()
        self._emit_personal_changed()

    def _on_user_name_changed(self, text: str):
        """用户名称变化"""
        self.user_name = text if text else "我"
        self._save_personal_settings()
        self._emit_personal_changed()

    def _emit_personal_changed(self):
        """触发个性化设置变化信号"""
        self.personal_changed.emit(
        self.user_name,
        self.user_avatar_path if self.user_avatar_path else "",
        self.user_avatar_color if self.user_avatar_color else "",
        self.chat_backgrounds,
        self.background_interval
    )

    def create_scrollable_content(self, parent_layout):
        """创建可滚动的单页内容"""
        # 主滚动区域
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_scroll.setFrameShape(QFrame.NoFrame)
        
        # 内容容器
        self.scroll_container = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_container)
        self.scroll_layout.setContentsMargins(40, 30, 40, 40)
        self.scroll_layout.setSpacing(40)
        
        # 创建所有设置区块
        self.section_widgets = []
        
        # 1. 模型引擎
        ollama_section = self.create_ollama_section()
        self.scroll_layout.addWidget(ollama_section)
        self.section_widgets.append(ollama_section)
        
        # 2. 系统信息
        system_section = self.create_system_section()
        self.scroll_layout.addWidget(system_section)
        self.section_widgets.append(system_section)
        
        # 3. 模型管理
        models_section = self.create_models_section()
        self.scroll_layout.addWidget(models_section)
        self.section_widgets.append(models_section)
        
        # 4. 主题设置
        theme_section = self.create_theme_section()
        self.scroll_layout.addWidget(theme_section)
        self.section_widgets.append(theme_section)
        
        # 5. 个性化
        personal_section = self.create_personal_section()
        self.scroll_layout.addWidget(personal_section)
        self.section_widgets.append(personal_section)
        
        # 6. 助手管理
        personas_section = self.create_personas_section()
        self.scroll_layout.addWidget(personas_section)
        self.section_widgets.append(personas_section)
        
        self.scroll_layout.addStretch()
        
        self.main_scroll.setWidget(self.scroll_container)
        
        # 连接滚动事件
        self.main_scroll.verticalScrollBar().valueChanged.connect(self.on_scroll_changed)
        
        parent_layout.addWidget(self.main_scroll, 1)
    
    def scroll_to_section(self, section_index: int):
        """滚动到指定区块，使其标题显示在页面顶部"""
        if 0 <= section_index < len(self.section_widgets):
            widget = self.section_widgets[section_index]
            # 直接滚动到widget的顶部位置
            self.main_scroll.verticalScrollBar().setValue(widget.y())
    
    def on_scroll_changed(self, value):
        """滚动时更新导航激活状态"""
        scroll_bar = self.main_scroll.verticalScrollBar()
        viewport_height = self.main_scroll.viewport().height()
        
        # 找到当前可见的主要区块
        active_section = 0
        for i, widget in enumerate(self.section_widgets):
            widget_top = widget.y()
            widget_bottom = widget_top + widget.height()
            
            # 如果区块的顶部在视口的上半部分，认为它是当前激活的
            if widget_top <= value + viewport_height // 3:
                active_section = i
        
        # 更新导航按钮状态
        nav_buttons = [
            self.nav_ollama, self.nav_system, self.nav_models,
            self.nav_theme, self.nav_personal, self.nav_personas
        ]
        
        for i, btn in enumerate(nav_buttons):
            btn.setChecked(i == active_section)

    def create_ollama_section(self):
        """创建模型引擎区块"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 标题
        c = self.theme.colors
        title = QLabel("🔧 模型引擎")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)
        
        # 卡片 - 添加边框
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setProperty("bordered", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 20, 25, 25)
        card_layout.setSpacing(20)
        
        status_title = QLabel("服务状态")
        status_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        status_title.setStyleSheet(f"color: {c['text']};")
        card_layout.addWidget(status_title)
        
        self.ollama_status = StatusIndicator()
        card_layout.addWidget(self.ollama_status)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.start_btn = QPushButton("启动服务")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setFixedWidth(140)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_ollama.emit)
        btn_layout.addWidget(self.start_btn)
        
        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.setFixedHeight(44)
        self.refresh_btn.setFixedWidth(140)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_status.emit)
        btn_layout.addWidget(self.refresh_btn)
        
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(card)
        
        return section
    
    def create_system_section(self):
        """创建系统信息区块"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 标题
        c = self.theme.colors
        title = QLabel("💻 系统信息")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)
        
        # 硬件信息卡片 - 添加边框
        self.hw_card = QFrame()
        self.hw_card.setObjectName("settingsCard")
        self.hw_card.setProperty("bordered", True)
        hw_card_layout = QVBoxLayout(self.hw_card)
        hw_card_layout.setContentsMargins(25, 20, 25, 25)
        hw_card_layout.setSpacing(15)

        hw_title = QLabel("硬件配置")
        hw_title.setFont(QFont("Microsoft YaHei UI", 15, QFont.Bold))
        hw_title.setStyleSheet(f"color: {c['text']};")
        hw_card_layout.addWidget(hw_title)
        
        self.hw_container = QWidget()
        self.hw_info_layout = QVBoxLayout(self.hw_container)
        self.hw_info_layout.setContentsMargins(0, 10, 0, 0)
        self.hw_info_layout.setSpacing(10)
        hw_card_layout.addWidget(self.hw_container)
        
        layout.addWidget(self.hw_card)
        
        # 显存/内存建议卡片 - 添加边框
        tips_card = QFrame()
        tips_card.setObjectName("settingsCard")
        tips_card.setProperty("bordered", True)
        tips_layout = QVBoxLayout(tips_card)
        tips_layout.setContentsMargins(25, 20, 25, 25)
        tips_layout.setSpacing(15)
        
        # 根据是否有 GPU 显示不同标题
        self.tips_title = QLabel("💡 显存与模型推荐")
        self.tips_title.setFont(QFont("Microsoft YaHei UI", 15, QFont.Bold))
        self.tips_title.setStyleSheet(f"color: {c['text']};")
        tips_layout.addWidget(self.tips_title)
        
        # 存储推荐容器，用于动态更新
        self.tips_container = QWidget()
        self.tips_container_layout = QVBoxLayout(self.tips_container)
        self.tips_container_layout.setContentsMargins(0, 0, 0, 0)
        self.tips_container_layout.setSpacing(0)
        tips_layout.addWidget(self.tips_container)
        
        # 添加提示说明
        note = QLabel("💡 提示：量化版本越低（Q4），文件越小但质量略降；量化版本越高（Q8），质量越好但占用更大。")
        note.setFont(QFont("Microsoft YaHei UI", 10))
        note.setStyleSheet(f"color: {c['text_dim']}; padding-top: 10px;")
        note.setWordWrap(True)
        tips_layout.addWidget(note)
        
        self.tips_card = tips_card
        layout.addWidget(tips_card)
        
        return section
    
    def create_models_section(self):
        """创建模型管理区块"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 标题
        c = self.theme.colors
        title = QLabel("📦 模型管理")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)
        
        desc = QLabel("下载并管理 AI 模型。根据您的硬件配置，仅显示可运行的模型。")
        desc.setStyleSheet(f"color: {c['text_secondary']};")
        desc.setFont(QFont("Microsoft YaHei UI", 12))
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        self.hw_hint_label = QLabel("")
        self.hw_hint_label.setFont(QFont("Microsoft YaHei UI", 11))
        layout.addWidget(self.hw_hint_label)
        
        self.model_tabs = QTabWidget()
        self.model_tabs.setFont(QFont("Microsoft YaHei UI", 12))
        self.model_tabs.setMinimumHeight(500)
        
        self.categories = {
            'text': ('💬 文本对话', '通用文本对话模型'),
            'coder': ('💻 代码编程', '代码生成与编程辅助'),
            'ocr': ('📝 文字识别', 'OCR 文字识别模型'),
            'image': ('🖼️ 图像处理', '图像生成与处理'),
            'audio': ('🎵 音频处理', '语音识别与合成'),
            'video': ('🎬 视频处理', '视频分析与生成')
        }
        
        for cat_key, (cat_name, cat_desc) in self.categories.items():
            tab = ModelCategoryTab(cat_key)
            tab.download_clicked.connect(self._on_tab_download)
            tab.load_clicked.connect(self.load_model.emit)
            tab.uninstall_clicked.connect(self.uninstall_model.emit)
            self.category_tabs[cat_key] = tab
            self.model_tabs.addTab(tab, cat_name)
        
        layout.addWidget(self.model_tabs)
        
        self.models_section_widget = section
        return section
    
    def create_theme_section(self):
        """创建主题设置区块"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 标题
        c = self.theme.colors
        title = QLabel("🎨 主题设置")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)
        
        # 卡片 - 添加边框
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setProperty("bordered", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 20, 25, 25)
        card_layout.setSpacing(20)
        
        theme_title = QLabel("选择主题")
        theme_title.setStyleSheet(f"color: {c['text']};")
        theme_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        card_layout.addWidget(theme_title)
        
        self.theme_buttons = {}
        themes_layout = QHBoxLayout()
        themes_layout.setSpacing(20)
        
        for theme_name, theme_data in THEMES.items():
            theme_btn = self.create_theme_option(theme_name, theme_data)
            themes_layout.addWidget(theme_btn)
            self.theme_buttons[theme_name] = theme_btn
        
        themes_layout.addStretch()
        card_layout.addLayout(themes_layout)
        
        self.theme_card = card
        layout.addWidget(card)
        
        # 初始化主题选中状态
        self.update_theme_selection()
        
        return section
    
    def create_personal_section(self):
        """创建个性化设置区块"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 标题
        c = self.theme.colors
        title = QLabel("👤 个性化")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)
        
        # 用户设置卡片 - 添加边框
        user_card = QFrame()
        user_card.setObjectName("settingsCard")
        user_card.setProperty("bordered", True)
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(25, 20, 25, 25)
        user_layout.setSpacing(15)
        
        user_title = QLabel("用户设置")
        user_title.setStyleSheet(f"color: {c['text']};")
        user_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        user_layout.addWidget(user_title)
        
        # 头像区域
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(15)
        
        self.user_avatar_preview = QLabel("👤")
        self.user_avatar_preview.setFixedSize(70, 70)
        self.user_avatar_preview.setAlignment(Qt.AlignCenter)
        self.user_avatar_preview.setFont(QFont("Segoe UI Emoji", 32))
        avatar_row.addWidget(self.user_avatar_preview)
        
        avatar_btn_layout = QVBoxLayout()
        avatar_btn_layout.setSpacing(8)
        
        c = self.theme.colors
        
        self.user_avatar_btn = QPushButton("📷 上传图片")
        self.user_avatar_btn.setFixedSize(130, 36)
        self.user_avatar_btn.setCursor(Qt.PointingHandCursor)
        self.user_avatar_btn.setProperty("styled", True)
        self.user_avatar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        self.user_avatar_btn.clicked.connect(self._select_user_avatar)
        avatar_btn_layout.addWidget(self.user_avatar_btn)
        
        self.user_avatar_clear_btn = QPushButton("↺ 恢复默认")
        self.user_avatar_clear_btn.setFixedSize(130, 36)
        self.user_avatar_clear_btn.setCursor(Qt.PointingHandCursor)
        self.user_avatar_clear_btn.setProperty("styled", True)
        self.user_avatar_clear_btn.setProperty("secondary", True)
        self.user_avatar_clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                border: 2px solid {c['border']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
        """)
        self.user_avatar_clear_btn.clicked.connect(self._clear_user_avatar)
        avatar_btn_layout.addWidget(self.user_avatar_clear_btn)
        
        avatar_row.addLayout(avatar_btn_layout)
        avatar_row.addStretch()
        user_layout.addLayout(avatar_row)
        
        # 用户名称
        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        name_label = QLabel("显示名称:")
        name_label.setStyleSheet(f"color: {c['text']};")
        name_label.setFont(QFont("Microsoft YaHei UI", 11))
        name_row.addWidget(name_label)
        
        from PySide6.QtWidgets import QLineEdit
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("我")
        self.user_name_input.setFixedWidth(200)
        self.user_name_input.setFixedHeight(36)
        self.user_name_input.setText(self.user_name)
        self.user_name_input.textChanged.connect(self._on_user_name_changed)
        name_row.addWidget(self.user_name_input)
        name_row.addStretch()
        user_layout.addLayout(name_row)
        
        layout.addWidget(user_card)
        
        # 聊天背景卡片 - 添加边框
        bg_card = QFrame()
        bg_card.setObjectName("settingsCard")
        bg_card.setProperty("bordered", True)
        bg_layout = QVBoxLayout(bg_card)
        bg_layout.setContentsMargins(25, 20, 25, 25)
        bg_layout.setSpacing(15)
        
        bg_title = QLabel("聊天背景")
        bg_title.setStyleSheet(f"color: {c['text']};")
        bg_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        bg_layout.addWidget(bg_title)
        
        bg_desc = QLabel("添加多张背景图片，聊天时自动轮播（推荐比例4:3）")
        bg_desc.setStyleSheet(f"color: {c['text_secondary']};")
        bg_desc.setFont(QFont("Microsoft YaHei UI", 11))
        bg_desc.setObjectName("descLabel")
        bg_layout.addWidget(bg_desc)
        
        # 背景图片预览区域
        self.bg_preview_container = QWidget()
        self.bg_preview_layout = QHBoxLayout(self.bg_preview_container)
        self.bg_preview_layout.setContentsMargins(0, 10, 0, 10)
        self.bg_preview_layout.setSpacing(10)
        self.bg_preview_layout.setAlignment(Qt.AlignLeft)
        bg_layout.addWidget(self.bg_preview_container)
        
        # 添加背景按钮
        bg_btn_row = QHBoxLayout()
        
        self.add_bg_btn = QPushButton("➕ 添加背景图片")
        self.add_bg_btn.setFixedSize(160, 38)
        self.add_bg_btn.setCursor(Qt.PointingHandCursor)
        self.add_bg_btn.setProperty("styled", True)
        self.add_bg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        self.add_bg_btn.clicked.connect(self._add_chat_background)
        bg_btn_row.addWidget(self.add_bg_btn)
        
        self.clear_bg_btn = QPushButton("🗑️ 清空全部")
        self.clear_bg_btn.setFixedSize(110, 38)
        self.clear_bg_btn.setCursor(Qt.PointingHandCursor)
        self.clear_bg_btn.setProperty("styled", True)
        self.clear_bg_btn.setProperty("secondary", True)
        self.clear_bg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                border: 2px solid {c['border']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
        """)
        self.clear_bg_btn.clicked.connect(self._clear_chat_backgrounds)
        bg_btn_row.addWidget(self.clear_bg_btn)
        
        bg_btn_row.addStretch()
        
        # 轮播间隔设置
        interval_label = QLabel("轮播间隔:")
        interval_label.setStyleSheet(f"color: {c['text']};")
        interval_label.setFont(QFont("Microsoft YaHei UI", 11))
        bg_btn_row.addWidget(interval_label)
        
        from PySide6.QtWidgets import QSpinBox
        self.bg_interval_spin = QSpinBox()
        self.bg_interval_spin.setRange(3, 60)
        self.bg_interval_spin.setValue(self.background_interval)  # 使用加载的值
        self.bg_interval_spin.setSuffix(" 秒")
        self.bg_interval_spin.setFixedWidth(110)
        self.bg_interval_spin.setFixedHeight(40)
        self.bg_interval_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {c['input_bg']};
                border: 2px solid {c['border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {c['text']};
                font-size: 13px;
            }}
            QSpinBox:focus {{
                border-color: {c['accent']};
            }}
            QSpinBox:hover {{
                border-color: {c['text_dim']};
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid {c['border']};
                border-top-right-radius: 6px;
                background-color: {c['bg_tertiary']};
            }}
            QSpinBox::up-button:hover {{
                background-color: {c['hover']};
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 22px;
                border-left: 1px solid {c['border']};
                border-bottom-right-radius: 6px;
                background-color: {c['bg_tertiary']};
            }}
            QSpinBox::down-button:hover {{
                background-color: {c['hover']};
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid {c['text']};
                width: 0px;
                height: 0px;
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {c['text']};
                width: 0px;
                height: 0px;
            }}
        """)
        self.bg_interval_spin.valueChanged.connect(self._on_bg_interval_changed)
        bg_btn_row.addWidget(self.bg_interval_spin)
        
        bg_layout.addLayout(bg_btn_row)
        
        layout.addWidget(bg_card)
        
        self.user_card = user_card
        self.bg_card = bg_card
        
        # 初始化UI显示（加载保存的设置）
        self._update_user_avatar_preview()
        self._update_bg_preview()
        
        return section
    
    def create_personas_section(self):
        """创建助手管理区块 - 分为协作助手和角色扮演"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 标题
        c = self.theme.colors
        title = QLabel("🎭 助手与角色")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)
        
        desc = QLabel("创建专业协作助手或有趣的角色扮演，让 AI 更懂你")
        desc.setStyleSheet(f"color: {c['text_secondary']};")
        desc.setFont(QFont("Microsoft YaHei UI", 12))
        layout.addWidget(desc)
        
        c = self.theme.colors
        
        # 创建标签页
        from PySide6.QtWidgets import QTabWidget
        self.personas_tabs = QTabWidget()
        self.personas_tabs.setFont(QFont("Microsoft YaHei UI", 12))
        
        # 协作助手标签页
        assistant_tab = QWidget()
        assistant_layout = QVBoxLayout(assistant_tab)
        assistant_layout.setContentsMargins(10, 15, 10, 10)
        assistant_layout.setSpacing(15)
        
        # 协作助手说明
        self.assistant_desc = QLabel("💼 专业工具型助手，帮助你完成各种任务")
        self.assistant_desc.setFont(QFont("Microsoft YaHei UI", 11))
        self.assistant_desc.setStyleSheet(f"color: {c['text_secondary']}; padding: 8px;")
        assistant_layout.addWidget(self.assistant_desc)
        
        # 添加协作助手按钮
        self.add_assistant_btn = QPushButton("➕ 添加协作助手")
        self.add_assistant_btn.setFixedSize(150, 40)
        self.add_assistant_btn.setCursor(Qt.PointingHandCursor)
        self.add_assistant_btn.clicked.connect(lambda: self._show_add_persona_dialog(persona_type="assistant"))
        self.add_assistant_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        assistant_layout.addWidget(self.add_assistant_btn)
        
        # 协作助手列表
        self.assistants_container = QWidget()
        self.assistants_layout = QVBoxLayout(self.assistants_container)
        self.assistants_layout.setContentsMargins(0, 10, 0, 10)
        self.assistants_layout.setSpacing(12)
        self.assistants_layout.addStretch()
        self.assistants_container.setStyleSheet("background-color: transparent;")
        assistant_layout.addWidget(self.assistants_container)
        
        # 角色扮演标签页
        roleplay_tab = QWidget()
        roleplay_layout = QVBoxLayout(roleplay_tab)
        roleplay_layout.setContentsMargins(10, 15, 10, 10)
        roleplay_layout.setSpacing(15)
        
        # 角色扮演说明
        self.roleplay_desc = QLabel("🎭 娱乐互动型角色，零距离沉浸式对话体验")
        self.roleplay_desc.setFont(QFont("Microsoft YaHei UI", 11))
        self.roleplay_desc.setStyleSheet(f"color: {c['text_secondary']}; padding: 8px;")
        roleplay_layout.addWidget(self.roleplay_desc)
        
        # 添加角色按钮
        self.add_roleplay_btn = QPushButton("➕ 添加角色扮演")
        self.add_roleplay_btn.setFixedSize(150, 40)
        self.add_roleplay_btn.setCursor(Qt.PointingHandCursor)
        self.add_roleplay_btn.clicked.connect(lambda: self._show_add_persona_dialog(persona_type="roleplay"))
        self.add_roleplay_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        roleplay_layout.addWidget(self.add_roleplay_btn)
        
        # 角色扮演列表
        self.roleplays_container = QWidget()
        self.roleplays_layout = QVBoxLayout(self.roleplays_container)
        self.roleplays_layout.setContentsMargins(0, 10, 0, 10)
        self.roleplays_layout.setSpacing(12)
        self.roleplays_layout.addStretch()
        self.roleplays_container.setStyleSheet("background-color: transparent;")
        roleplay_layout.addWidget(self.roleplays_container)
        
        # 添加标签页
        self.personas_tabs.addTab(assistant_tab, "💼 协作助手")
        self.personas_tabs.addTab(roleplay_tab, "🎭 角色扮演")
        
        # 标签页样式
        self.personas_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                border-radius: 10px;
                background-color: {c['card_bg']};
                margin-top: -1px;
            }}
            QTabBar::tab {{
                background-color: {c['bg_tertiary']};
                color: {c['text_secondary']};
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background-color: {c['card_bg']};
                color: {c['accent']};
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {c['hover']};
                color: {c['text']};
            }}
        """)
        
        layout.addWidget(self.personas_tabs)
        
        # 保留旧的容器引用以兼容现有代码
        self.personas_container = self.assistants_container
        self.personas_layout = self.assistants_layout

        return section

    def create_content(self, parent_layout):
        """保留旧方法以防兼容性问题"""
        self.create_scrollable_content(parent_layout)
    
    def on_nav_clicked(self, id: int):
        """保留旧方法以防兼容性"""
        self.scroll_to_section(id)
    
    def create_theme_option(self, name: str, theme: dict):
        btn = QFrame()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(180, 130)
        btn.setProperty("theme_name", name)
        
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        preview = QFrame()
        preview.setFixedHeight(55)
        preview.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['bg']};
                border-radius: 8px;
                border: 2px solid {theme['border']};
            }}
        """)
        
        preview_layout = QHBoxLayout(preview)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        
        sidebar_preview = QFrame()
        sidebar_preview.setFixedWidth(30)
        sidebar_preview.setStyleSheet(f"background-color: {theme['sidebar_bg']}; border-radius: 4px;")
        preview_layout.addWidget(sidebar_preview)
        
        content_preview = QFrame()
        content_preview.setStyleSheet(f"background-color: {theme['bg']}; border-radius: 4px;")
        preview_layout.addWidget(content_preview)
        
        layout.addWidget(preview)
        
        c = self.theme.colors
        label = QLabel(theme['display_name'])
        label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(label)
        
        btn.mousePressEvent = lambda e, n=name: self.on_theme_selected(n)
        
        return btn
    
    def on_theme_selected(self, theme_name: str):
        from core.logger import get_logger
        logger = get_logger('settings')
        
        logger.info(f"on_theme_selected 被调用，主题: {theme_name}")
        self.theme.set_theme(theme_name)
        self.theme_changed.emit(theme_name)
        logger.info(f"已发射 theme_changed 信号")
        self.update_theme_selection()
    
    def update_theme_selection(self):
        c = self.theme.colors
        # 获取当前主题名称（兼容新旧主题系统）
        current_theme = self.theme.current
        if isinstance(current_theme, dict) and 'name' in current_theme:
            current = current_theme['name']
        else:
            current = 'dark'  # 默认值
        
        for name, btn in self.theme_buttons.items():
            if name == current:
                btn.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c['card_bg']};
                        border: 3px solid {c['accent']};
                        border-radius: 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QFrame {{
                        background-color: {c['card_bg']};
                        border: 2px solid {c['border']};
                        border-radius: 14px;
                    }}
                    QFrame:hover {{
                        border-color: {c['text_dim']};
                    }}
                """)
    
    def apply_theme(self, theme=None):
        from core.logger import get_logger
        logger = get_logger('settings')
        
        logger.info(f"apply_theme 被调用，当前主题: {self.theme.current.get('name', 'unknown')}")
        
        c = self.theme.colors
        
        self.setStyleSheet(f"background-color: {c['bg']};")
        
        # 导航栏样式
        self.nav.setStyleSheet(f"""
            QWidget#settingsNav {{
                background-color: {c['settings_nav_bg']};
                border-right: 1px solid {c['border']};
            }}
            QWidget#settingsNav QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        # 返回按钮
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['accent']};
                text-align: left;
                padding: 10px 15px;
                border-radius: 8px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        
        # 主滚动区域 - 优化滚动条样式
        self.main_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {c['bg']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c['text_dim']}40;
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {c['text_dim']}60;
            }}
            QScrollBar::handle:vertical:pressed {{
                background-color: {c['text_dim']}80;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        # 滚动容器
        self.scroll_container.setStyleSheet(f"background-color: {c['bg']};")
        
        # 所有设置卡片统一样式
        card_style = f"""
            QFrame#settingsCard {{
                background-color: {c['card_bg']};
                border-radius: 16px;
            }}
            QFrame#settingsCard[bordered="true"] {{
                background-color: {c['card_bg']};
                border-radius: 16px;
                border: 2px solid {c['border']};
            }}
        """
        
        # 应用到所有卡片
        for widget in self.scroll_container.findChildren(QFrame):
            if widget.objectName() == "settingsCard":
                widget.setStyleSheet(card_style)
        
        # 按钮样式
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 10px;
                padding: 12px 25px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {c['text_dim']};
            }}
        """)
        
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 10px;
                padding: 12px 25px;
                font-size: 13px;
                border: 2px solid {c['border']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['accent']};
            }}
        """)
        
        # 个性化按钮样式
        for btn in self.scroll_container.findChildren(QPushButton):
            if btn.property("styled"):
                if btn.property("secondary"):
                    # 次要按钮样式
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {c['bg_tertiary']};
                            color: {c['text']};
                            border-radius: 10px;
                            padding: 8px 16px;
                            font-size: 13px;
                            font-weight: 500;
                            border: 2px solid {c['border']};
                        }}
                        QPushButton:hover {{
                            background-color: {c['hover']};
                            border-color: {c['accent']};
                            color: {c['accent']};
                        }}
                    """)
                else:
                    # 主要按钮样式
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {c['accent']};
                            color: white;
                            border-radius: 10px;
                            padding: 8px 16px;
                            font-size: 13px;
                            font-weight: 600;
                            border: none;
                        }}
                        QPushButton:hover {{
                            background-color: {c['accent_hover']};
                        }}
                    """)
        
        # 模型标签页样式
        if hasattr(self, 'model_tabs'):
            self.model_tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {c['border']};
                    border-radius: 10px;
                    background-color: {c['card_bg']};
                    margin-top: -1px;
                }}
                QTabBar::tab {{
                    background-color: {c['bg_tertiary']};
                    color: {c['text_secondary']};
                    padding: 10px 20px;
                    margin-right: 4px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-size: 13px;
                }}
                QTabBar::tab:selected {{
                    background-color: {c['card_bg']};
                    color: {c['accent']};
                    font-weight: bold;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: {c['hover']};
                    color: {c['text']};
                }}
                QScrollBar:vertical {{
                    background-color: transparent;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {c['text_dim']}40;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {c['text_dim']}60;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
            """)
        
        # 硬件提示标签
        if hasattr(self, 'hw_hint_label'):
            self.hw_hint_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['accent']};
                    background-color: {c['accent']}15;
                    padding: 10px 15px;
                    border-radius: 8px;
                }}
            """)
        
        # 个性化卡片样式
        self._apply_personal_card_style()
        
        # 助手容器样式
        if hasattr(self, 'personas_container'):
            self.personas_container.setStyleSheet("background-color: transparent;")
        
        # 更新助手管理标签页样式
        if hasattr(self, 'personas_tabs'):
            self.personas_tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {c['border']};
                    border-radius: 10px;
                    background-color: {c['card_bg']};
                    margin-top: -1px;
                }}
                QTabBar::tab {{
                    background-color: {c['bg_tertiary']};
                    color: {c['text_secondary']};
                    padding: 12px 24px;
                    margin-right: 4px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QTabBar::tab:selected {{
                    background-color: {c['card_bg']};
                    color: {c['accent']};
                    font-weight: bold;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: {c['hover']};
                    color: {c['text']};
                }}
            """)
        
        # 更新助手管理说明文字样式
        if hasattr(self, 'assistant_desc'):
            self.assistant_desc.setStyleSheet(f"color: {c['text_secondary']}; padding: 8px;")
        if hasattr(self, 'roleplay_desc'):
            self.roleplay_desc.setStyleSheet(f"color: {c['text_secondary']}; padding: 8px;")
        
        # 更新添加助手按钮样式
        if hasattr(self, 'add_assistant_btn'):
            self.add_assistant_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent']};
                    color: white;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {c['accent_hover']};
                }}
            """)
        if hasattr(self, 'add_roleplay_btn'):
            self.add_roleplay_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent']};
                    color: white;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {c['accent_hover']};
                }}
            """)
        
        # 更新主题选中状态
        if hasattr(self, 'theme_buttons'):
            self.update_theme_selection()
        
        # 更新所有标题和标签的颜色（遍历所有QLabel）
        for label in self.scroll_container.findChildren(QLabel):
            # 跳过已有特殊样式的标签
            if label.styleSheet() and ('background-color' in label.styleSheet() or 'border' in label.styleSheet()):
                continue
            
            # 根据字体大小判断是标题还是普通文本
            font = label.font()
            if font.pointSize() >= 20:  # 大标题 (22px)
                label.setStyleSheet(f"color: {c['text']};")
            elif font.pointSize() >= 14:  # 中标题 (14-15px)
                label.setStyleSheet(f"color: {c['text']};")
            elif font.pointSize() >= 11:  # 小标题/标签 (11-13px)
                # 检查是否是次要文本
                if 'secondary' in label.objectName() or 'desc' in label.objectName().lower():
                    label.setStyleSheet(f"color: {c['text_secondary']};")
                else:
                    label.setStyleSheet(f"color: {c['text']};")
        
        # 更新导航标题
        if hasattr(self, 'nav_title'):
            self.nav_title.setStyleSheet(f"color: {c['text']};")
        
        # 刷新助手卡片样式（不重新创建，只更新样式）
        logger.info("准备更新助手卡片样式...")
        logger.debug(f"assistants_container 存在: {hasattr(self, 'assistants_container')}")
        logger.debug(f"roleplays_container 存在: {hasattr(self, 'roleplays_container')}")
        
        if hasattr(self, 'assistants_container') or hasattr(self, 'roleplays_container'):
            self._update_persona_cards_style()
        else:
            logger.warning("助手容器不存在，跳过卡片样式更新")
        
        # 更新主题选择
        self.update_theme_selection()
        
        # 刷新硬件配置显示（如果已有数据）
        if self.hardware_info:
            logger.info("刷新硬件配置显示以适配新主题")
            self.update_hardware_info(self.hardware_info)
        
        logger.info("apply_theme 完成")
    
    def update_ollama_status(self, running: bool, installed: bool):
        if running:
            self.ollama_status.set_status("success", "服务运行中")
            self.start_btn.setEnabled(False)
            self.start_btn.setText("已启动")
        elif installed:
            self.ollama_status.set_status("warning", "已安装，未运行")
            self.start_btn.setEnabled(True)
            self.start_btn.setText("启动服务")
        else:
            self.ollama_status.set_status("error", "未安装")
            self.start_btn.setEnabled(False)
            self.start_btn.setText("未安装")
    
    def update_hardware_info(self, info: dict):
        self.hardware_info = info
        c = self.theme.colors
        
        while self.hw_info_layout.count():
            item = self.hw_info_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取显存和内存信息用于等级判断
        vram_gb = self._parse_vram()
        ram_gb = self._parse_ram()
        
        # 添加硬件等级标签
        level_info = self._get_hardware_level(vram_gb, ram_gb)
        level_row = QWidget()
        level_layout = QHBoxLayout(level_row)
        level_layout.setContentsMargins(5, 0, 5, 0)
        level_layout.setSpacing(15)
        
        level_key = QLabel("硬件等级")
        level_key.setFont(QFont("Microsoft YaHei UI", 11))
        level_key.setFixedWidth(90)
        level_key.setFixedHeight(28)
        level_key.setAlignment(Qt.AlignCenter)
        level_key.setStyleSheet(f"""
            QLabel {{
                color: {c['text_secondary']};
                background-color: {c['info_row_bg']};
                border-radius: 6px;
                padding: 0 8px;
            }}
        """)
        level_layout.addWidget(level_key)
        
        level_value = QLabel(f"{level_info['emoji']} {level_info['name']}")
        level_value.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        level_value.setFixedHeight(28)
        level_value.setAlignment(Qt.AlignCenter)
        level_value.setStyleSheet(f"""
            QLabel {{
                color: {level_info['color']};
                background-color: {level_info['color']}18;
                border-radius: 6px;
                padding: 0 12px;
            }}
        """)
        level_layout.addWidget(level_value)
        level_layout.addStretch()
        
        self.hw_info_layout.addWidget(level_row)
        
        # 显示原有的硬件信息
        for key, value in info.items():
            row = QWidget()
            row.setFixedHeight(40)
            
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 0, 5, 0)
            row_layout.setSpacing(15)
            
            key_label = QLabel(key)
            key_label.setFont(QFont("Microsoft YaHei UI", 11))
            key_label.setFixedWidth(90)
            key_label.setFixedHeight(28)
            key_label.setAlignment(Qt.AlignCenter)
            key_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['text_secondary']};
                    background-color: {c['info_row_bg']};
                    border-radius: 6px;
                    padding: 0 8px;
                }}
            """)
            row_layout.addWidget(key_label)
            
            color = c['text']
            display_value = str(value) if value else "未检测到"
            bg_color = c['info_row_bg']
            
            if key == "GPU可用":
                if value:
                    color = c['success']
                    display_value = "✓ 可用"
                    bg_color = f"{c['success']}18"
                else:
                    color = c['error']
                    display_value = "✗ 不可用"
                    bg_color = f"{c['error']}18"
            elif value is None:
                color = c['text_dim']
                display_value = "未检测到"
            
            value_label = QLabel(display_value)
            value_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
            value_label.setFixedHeight(28)
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    background-color: {bg_color};
                    border-radius: 6px;
                    padding: 0 12px;
                }}
            """)
            row_layout.addWidget(value_label)
            row_layout.addStretch()
            
            self.hw_info_layout.addWidget(row)
        
        self._update_hw_hint()
    
    def _get_hardware_level(self, vram_gb: float, ram_gb: float) -> dict:
        """根据显存和内存判断硬件等级"""
        c = self.theme.colors
        
        if vram_gb >= 40:
            return {
                'name': '专业级',
                'emoji': '🏆',
                'color': '#dc3545',
                'desc': '专业级显卡（H100/A100），可运行超大模型（70B+）'
            }
        elif vram_gb >= 24:
            return {
                'name': '旗舰级',
                'emoji': '👑',
                'color': '#e83e8c',
                'desc': '可运行大型模型（32B-70B）'
            }
        elif vram_gb >= 16:
            return {
                'name': '高端级',
                'emoji': '💎',
                'color': '#fd7e14',
                'desc': '可运行中大型模型（14B-32B）'
            }
        elif vram_gb >= 12:
            return {
                'name': '性能级',
                'emoji': '🚀',
                'color': '#6f42c1',
                'desc': '可运行中型模型（8B-14B）'
            }
        elif vram_gb >= 8:
            return {
                'name': '主流级',
                'emoji': '⚡',
                'color': '#007AFF',
                'desc': '可运行小型模型（3B-8B）'
            }
        elif vram_gb >= 6:
            return {
                'name': '进阶级',
                'emoji': '📱',
                'color': '#17a2b8',
                'desc': '可运行轻量模型（1.5B-7B）'
            }
        elif vram_gb >= 4:
            return {
                'name': '入门级',
                'emoji': '🌱',
                'color': '#28a745',  # 黄色
                'desc': '可运行超轻量模型（0.5B-3B）'
            }
        elif vram_gb > 0:
            return {
                'name': '基础级',
                'emoji': '💻',
                'color': c['text_dim'],
                'desc': '仅支持极小模型（<1B）'
            }
        else:
            # CPU 模式
            if ram_gb >= 64:
                return {
                    'name': '专业级',
                    'emoji': '🚀',
                    'color': '#6f42c1',
                    'desc': 'CPU模式，可运行中型模型（3B-14B）'
                }
            elif ram_gb >= 32:
                return {
                    'name': '高配级',
                    'emoji': '⚡',
                    'color': '#28a745',
                    'desc': 'CPU模式，可运行小型模型（1B-7B）'
                }
            elif ram_gb >= 24:
                return {
                    'name': '中配级',
                    'emoji': '🖥️',
                    'color': '#607d8b',
                    'desc': 'CPU模式，可运行轻量模型（0.5B-3B）'
                }
            elif ram_gb >= 16:
                return {
                    'name': '标配级',
                    'emoji': '💾',
                    'color': '#9e9e9e',
                    'desc': 'CPU模式，可运行超轻量模型（0.5B-1B）'
                }
            else:
                return {
                    'name': '基础级',
                    'emoji': '⚙️',
                    'color': c['text_dim'],
                    'desc': 'CPU模式，仅支持极小模型'
                }
    
    def _update_hw_hint(self):
        vram_gb = self._parse_vram()
        ram_gb = self._parse_ram()
        
        if vram_gb > 0:
            hint = f"💾 检测到 GPU 显存: {vram_gb:.0f}GB，内存: {ram_gb:.0f}GB — 已为您筛选适合的模型"
        else:
            hint = f"💾 未检测到 GPU，内存: {ram_gb:.0f}GB — 将使用 CPU 运行，已筛选轻量模型"
        
        self.hw_hint_label.setText(hint)
        
        # 更新推荐列表
        self._update_recommendations(vram_gb, ram_gb)
    
    def _update_recommendations(self, vram_gb: float, ram_gb: float):
        """根据硬件情况更新推荐列表"""
        c = self.theme.colors
        
        # 清空现有内容
        while self.tips_container_layout.count():
            item = self.tips_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 根据是否有 GPU 选择不同的推荐
        if vram_gb > 0:
            self.tips_title.setText("💡 显存与模型推荐")
            recommendations = [
                ("4GB", "入门级", "🌱", "#007AFF", "0.5B-3B", "Qwen3-0.6B, Llama-3.2-1B", "Q4/Q8"),
                ("6GB", "进阶级", "📱", "#17a2b8", "1.5B-7B", "Qwen3-4B, DeepSeek-R1-1.5B", "Q4"),
                ("8GB", "主流级", "⚡", "#28a745", "3B-8B", "Qwen3-8B, GLM-Edge-4B", "Q4/Q5"),
                ("12GB", "性能级", "🚀", "#6f42c1", "8B-14B", "Qwen3-14B, DeepSeek-R1-14B", "Q4/Q5"),
                ("16GB", "高端级", "💎", "#e83e8c", "14B-32B", "Qwen3-32B, DeepSeek-R1-32B", "Q4/Q5"),
                ("24GB", "旗舰级", "👑", "#dc3545", "32B-70B", "Llama-3-70B, Qwen3-70B", "Q4/Q5/Q8"),
                ("40GB+", "专业级", "🏆", "#fd7e14", "70B-405B", "Llama-3.1-405B, Qwen2.5-72B", "Q4/Q5/Q8"),
            ]
            size_label = "显存"
        else:
            self.tips_title.setText("💡 内存与模型推荐")
            recommendations = [
                ("8GB", "基础级", "⚙️", "#9e9e9e", "0.5B", "Qwen3-0.6B", "Q4"),
                ("16GB", "标配级", "💾", "#9e97e9e", "0.5B-1B", "Qwen3-0.6B, Llama-3.2-1B", "Q4/Q8"),
                ("24GB", "中配级", "🖥️", "#607d8b", "0.5B-3B", "Qwen3-0.6B, Llama-3.2-3B", "Q4/Q8"),
                ("32GB", "高配级", "⚡", "#28a745", "1B-7B", "Qwen3-4B, DeepSeek-R1-1.5B", "Q4"),
                ("64GB+", "专业级", "🚀", "#6f42c1", "3B-14B", "Qwen3-8B, Llama-3.1-8B", "Q4"),
            ]
            size_label = "内存"
        
        last_item = recommendations[-1][0]
        
        for mem, level, icon, color, params, models, quant in recommendations:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 8, 0, 8)
            row_layout.setSpacing(12)
            
            # 内存/显存标签
            mem_label = QLabel(mem)
            mem_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
            mem_label.setFixedWidth(70)
            mem_label.setAlignment(Qt.AlignCenter)
            mem_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['accent']};
                    background-color: {c['accent']}15;
                    border-radius: 8px;
                    padding: 6px 10px;
                    border: 2px solid {c['accent']}40;
                }}
            """)
            row_layout.addWidget(mem_label)
            
            # 等级标签
            level_widget = QWidget()
            level_widget.setFixedWidth(100)
            level_inner = QHBoxLayout(level_widget)
            level_inner.setContentsMargins(8, 4, 8, 4)
            level_inner.setSpacing(4)
            
            level_icon = QLabel(icon)
            level_icon.setFont(QFont("Segoe UI Emoji", 12))
            level_inner.addWidget(level_icon)
            
            level_text = QLabel(level)
            level_text.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            level_inner.addWidget(level_text)
            
            level_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {color}20;
                    border-radius: 8px;
                    border: 2px solid {color}40;
                }}
                QLabel {{
                    color: {color};
                    background: transparent;
                    border: none;
                }}
            """)
            row_layout.addWidget(level_widget)
            
            # 详细信息
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            params_label = QLabel(f"参数量: {params}")
            params_label.setFont(QFont("Microsoft YaHei UI", 10))
            params_label.setStyleSheet(f"color: {c['text']};")
            info_layout.addWidget(params_label)
            
            models_label = QLabel(f"推荐: {models}")
            models_label.setFont(QFont("Microsoft YaHei UI", 9))
            models_label.setStyleSheet(f"color: {c['text_secondary']};")
            models_label.setWordWrap(True)
            info_layout.addWidget(models_label)
            
            quant_label = QLabel(f"量化: {quant}")
            quant_label.setFont(QFont("Microsoft YaHei UI", 9))
            quant_label.setStyleSheet(f"color: {c['text_dim']};")
            info_layout.addWidget(quant_label)
            
            row_layout.addLayout(info_layout, 1)
            
            self.tips_container_layout.addWidget(row)
            
            # 添加分隔线（除了最后一项）
            if mem != last_item:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setStyleSheet(f"background-color: {c['border']}; max-height: 1px;")
                self.tips_container_layout.addWidget(separator)
    
    def _parse_vram(self) -> float:
        vram_str = self.hardware_info.get('GPU显存', '')
        if not vram_str or vram_str == '未知':
            return 0
        
        try:
            vram_str = vram_str.upper().strip()
            if 'MIB' in vram_str or 'MB' in vram_str:
                num = float(''.join(c for c in vram_str if c.isdigit() or c == '.'))
                return num / 1024
            elif 'GIB' in vram_str or 'GB' in vram_str:
                num = float(''.join(c for c in vram_str if c.isdigit() or c == '.'))
                return num
            else:
                num = float(''.join(c for c in vram_str if c.isdigit() or c == '.'))
                if num > 100:
                    return num / 1024
                return num
        except:
            return 0
    
    def _parse_ram(self) -> float:
        ram_str = self.hardware_info.get('内存', '')
        try:
            num = float(''.join(c for c in ram_str if c.isdigit() or c == '.'))
            return num
        except:
            return 16
    
    def update_models(self, recommended: dict, installed: list):
        """更新模型列表"""
        self._installed_models = installed
        
        logger.info(f"更新模型列表，已安装模型数: {len(installed)}")
        
        vram_gb = self._parse_vram()
        ram_gb = self._parse_ram()
        
        # 设置所有标签页的显存信息
        for tab in self.category_tabs.values():
            tab.set_available_vram(vram_gb)
        
        categorized_models = {cat: [] for cat in self.categories.keys()}
        
        for name, info in recommended.items():
            category = info.get('category', 'text')
            if category not in categorized_models:
                category = 'text'
            
            params_b = self._extract_params(info)
            quant_details = info.get('quant_details', {})
            
            # 新逻辑：检查是否有任何量化版本可以在当前显存下运行
            has_suitable_quant = False
            if quant_details and vram_gb > 0:
                for quant, detail in quant_details.items():
                    vram_needed = detail.get('vram_gb', 0)
                    # 允许显存需求在可用显存的 110% 以内（稍微宽松一点）
                    if vram_needed <= vram_gb * 1.1:
                        has_suitable_quant = True
                        break
            
            # 如果有合适的量化版本，或者没有显存限制（CPU模式），则显示该模型
            if has_suitable_quant or vram_gb == 0:
                categorized_models[category].append({
                    'name': name,
                    **info
                })
            # 兼容旧逻辑：如果没有 quant_details，使用参数量判断
            elif not quant_details:
                max_params = self._calculate_max_params(vram_gb, ram_gb)
                if params_b <= max_params:
                    categorized_models[category].append({
                        'name': name,
                        **info
                    })
        
        for cat_key, tab in self.category_tabs.items():
            models = categorized_models.get(cat_key, [])
            
            # 构建已安装模型的集合（用于快速查找）
            installed_set = set()
            for m in installed:
                ollama_name = m.get('ollama_name', '') or m.get('name', '')
                if ollama_name:
                    installed_set.add(ollama_name.lower())
                    # 也添加不带标签的版本
                    base_name = ollama_name.split(':')[0]
                    installed_set.add(base_name.lower())
            
            # 排序：已安装的模型优先，然后按参数量排序
            def sort_key(model):
                name = model.get('name', '')
                params = self._extract_params(model)
                
                # 检查是否已安装（简单匹配）
                is_installed = False
                quantizations = model.get('quantizations', [])
                for quant in quantizations:
                    # 尝试多种可能的命名格式
                    possible_names = [
                        f"{name}-{quant}".lower(),
                        f"{name}-{quant.lower()}".lower(),
                        f"{name}-{quant.upper()}".lower(),
                    ]
                    for possible_name in possible_names:
                        if possible_name in installed_set:
                            is_installed = True
                            break
                    if is_installed:
                        break
                
                # 返回元组：(是否已安装的反值, 参数量)
                # 已安装的模型排在前面
                return (not is_installed, params)
            
            models.sort(key=sort_key)
            tab.update_models(models, installed, self._downloading_models)  # 传入下载状态
    
    def _calculate_max_params(self, vram_gb: float, ram_gb: float) -> float:
        if vram_gb >= 24: return 70
        elif vram_gb >= 16: return 32
        elif vram_gb >= 12: return 14
        elif vram_gb >= 8: return 8
        elif vram_gb >= 6: return 7
        elif vram_gb >= 4: return 3
        elif vram_gb > 0: return 1.7
        elif ram_gb >= 32: return 8
        elif ram_gb >= 16: return 4
        elif ram_gb >= 8: return 1.7
        else: return 0.6
    
    def _extract_params(self, info: dict) -> float:
        if 'params_b' in info:
            return float(info['params_b'])
        
        params_str = info.get('params', '')
        if params_str:
            try:
                num = float(''.join(c for c in params_str if c.isdigit() or c == '.'))
                return num
            except:
                pass
        
        return 1.0
    
    def _on_tab_download(self, model_name: str, quantization: str):
        """处理标签页的下载请求"""
        # 记录下载状态
        self._downloading_models[model_name] = {"percent": 0, "text": "准备下载..."}
        
        for tab in self.category_tabs.values():
            if model_name in tab.model_cards:
                tab.start_download(model_name)
                break
        self.download_model.emit(model_name, quantization)
    
    @Slot(str, int, str)
    def update_download_progress(self, model_name: str, percent: int, text: str):
        """更新下载进度"""
        # 保存下载状态
        self._downloading_models[model_name] = {"percent": percent, "text": text}
        
        for tab in self.category_tabs.values():
            if model_name in tab.model_cards:
                tab.update_progress(model_name, percent, text)
                return
    
    @Slot(str, bool)
    def finish_download(self, model_name: str, success: bool):
        """完成下载"""
        # 移除下载状态
        if model_name in self._downloading_models:
            del self._downloading_models[model_name]
        
        for tab in self.category_tabs.values():
            if model_name in tab.model_cards:
                tab.finish_download(model_name, success)
                return



class SettingsNavItem(QPushButton):
    """设置导航项"""
    
    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"{icon}  {text}" if icon else text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.theme = get_theme_manager()
        self.apply_theme()
        self.theme.theme_changed.connect(self.apply_theme)
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['card_bg']};
                color: {c['text']};
                text-align: left;
                padding: 14px 20px;
                border: 1px solid {c['border']};
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['accent']};
            }}
            QPushButton:checked {{
                background-color: {c['settings_nav_active']};
                color: {c['accent']};
                border-color: {c['accent']};
            }}
        """)