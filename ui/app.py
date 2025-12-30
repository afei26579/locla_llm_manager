"""主应用程序"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QStackedWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont

import sys
import os
import json
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from core.hardware import detect_hardware
from core.ollama_manager import OllamaManager
from core.model_manager import ModelManager
from core.chat_db import ChatManager

from .themes import get_theme_manager, get_stylesheet
from .components import HistoryItem, StatusIndicator
from .chat_page import ChatPage
from .settings_page import SettingsPage


class WorkerThread(QThread):
    """工作线程"""
    finished = Signal(object)
    progress = Signal(str, int, str)  # model_name, percent, text
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(e)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.theme = get_theme_manager()
        self.ollama = OllamaManager()
        self.model_manager = ModelManager()
        self.chat_manager = ChatManager()
        
        self.current_chat_id = None
        self.current_history_item = None
        self.worker = None
        self.current_download_model = None
        
        self.setup_ui()
        self.connect_signals()
        self.load_personal_settings()  # 加载个性化设置
        self.startup_check()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("AI 助手")
        
        # 设置初始尺寸和最小尺寸
        initial_width = 1280
        initial_height = 960
        
        self.setMinimumSize(800, 600)  # 设置合理的最小尺寸
        self.resize(initial_width, initial_height)
        self.setStyleSheet(get_stylesheet())
        
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 主内容区使用 StackedWidget
        self.main_stack = QStackedWidget()
        
        # 聊天页面容器（包含侧边栏）
        self.chat_container = QWidget()
        chat_container_layout = QHBoxLayout(self.chat_container)
        chat_container_layout.setContentsMargins(0, 0, 0, 0)
        chat_container_layout.setSpacing(0)
        
        self.create_sidebar(chat_container_layout)
        
        self.chat_page = ChatPage()
        chat_container_layout.addWidget(self.chat_page, 1)
        
        self.main_stack.addWidget(self.chat_container)
        
        # 设置页面（完整覆盖）
        self.settings_page = SettingsPage()
        self.main_stack.addWidget(self.settings_page)
        
        main_layout.addWidget(self.main_stack, 1)
        
        # 底部通知栏
        self.create_notification_bar(main_layout)
        
        # 安装事件过滤器以捕获双击
        self.installEventFilter(self)
        self._last_click_time = 0
        
        self.theme.theme_changed.connect(self.on_theme_changed)
        self.apply_theme()
    
    def create_sidebar(self, parent_layout):
        """创建侧边栏"""
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(280)
        
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(12)
        
        # 新建对话按钮
        self.new_chat_btn = QPushButton("＋ 新建对话")
        self.new_chat_btn.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self.new_chat_btn.setFixedHeight(48)
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.new_chat)
        layout.addWidget(self.new_chat_btn)
        
        # 角色对话按钮（默认隐藏）
        self.role_chat_btn = QPushButton("🎭 角色对话")
        self.role_chat_btn.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self.role_chat_btn.setFixedHeight(48)
        self.role_chat_btn.setCursor(Qt.PointingHandCursor)
        self.role_chat_btn.clicked.connect(self.new_role_chat)
        self.role_chat_btn.setVisible(False)  # 默认隐藏
        layout.addWidget(self.role_chat_btn)
        
        # 分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # 历史记录标题
        self.history_title = QLabel("对话历史")
        self.history_title.setFont(QFont("Microsoft YaHei UI", 11))
        layout.addWidget(self.history_title)
        
        # 历史记录滚动区域
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_scroll.setObjectName("historyScroll")
        
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(6)
        self.history_layout.addStretch()
        
        self.history_scroll.setWidget(self.history_container)
        layout.addWidget(self.history_scroll, 1)
        
        # 底部状态
        self.create_sidebar_footer(layout)
        
        # Ollama 状态快捷按钮区域
        self.ollama_quick_widget = QWidget()
        self.ollama_quick_layout = QVBoxLayout(self.ollama_quick_widget)
        self.ollama_quick_layout.setContentsMargins(0, 10, 0, 0)
        self.ollama_quick_layout.setSpacing(8)
        
        # 状态标签
        self.ollama_status_label = QLabel("")
        self.ollama_status_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.ollama_status_label.setAlignment(Qt.AlignCenter)
        self.ollama_quick_layout.addWidget(self.ollama_status_label)
        
        # 快捷按钮
        self.ollama_quick_btn = QPushButton("")
        self.ollama_quick_btn.setFixedHeight(36)
        self.ollama_quick_btn.setCursor(Qt.PointingHandCursor)
        self.ollama_quick_btn.setVisible(False)
        self.ollama_quick_layout.addWidget(self.ollama_quick_btn)
        
        # 跟踪按钮连接状态
        self._ollama_btn_connected = False
        
        layout.addWidget(self.ollama_quick_widget)

        parent_layout.addWidget(self.sidebar)
        
        self.apply_sidebar_theme()
    
    def update_ollama_quick_status(self, installed: bool, running: bool):
        """更新侧边栏 Ollama 快捷状态"""
        c = self.theme.colors
        
        if running:
            # 已运行，隐藏按钮
            self.ollama_status_label.setText("✅ Ollama 运行中")
            self.ollama_status_label.setStyleSheet(f"color: {c['success']};")
            self.ollama_quick_btn.setVisible(False)
        elif installed:
            # 已安装未运行
            self.ollama_status_label.setText("⚠️ Ollama 未启动")
            self.ollama_status_label.setStyleSheet(f"color: {c['warning']};")
            self.ollama_quick_btn.setText("🚀 一键启动")
            self.ollama_quick_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent']};
                    color: white;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c['accent_hover']};
                }}
            """)
            self.ollama_quick_btn.setVisible(True)
            # 断开之前的连接，重新连接
            if self._ollama_btn_connected:
                try:
                    self.ollama_quick_btn.clicked.disconnect()
                except (TypeError, RuntimeError, AttributeError):
                    pass
            self.ollama_quick_btn.clicked.connect(self._quick_start_ollama)
            self._ollama_btn_connected = True
        else:
            # 未安装
            self.ollama_status_label.setText("❌ Ollama 未安装")
            self.ollama_status_label.setStyleSheet(f"color: {c['error']};")
            self.ollama_quick_btn.setText("📥 点击去下载")
            self.ollama_quick_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['error']};
                    color: white;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #c82333;
                }}
            """)
            self.ollama_quick_btn.setVisible(True)
            # 断开之前的连接，重新连接
            if self._ollama_btn_connected:
                try:
                    self.ollama_quick_btn.clicked.disconnect()
                except (TypeError, RuntimeError, AttributeError):
                    pass
            self.ollama_quick_btn.clicked.connect(self._open_ollama_download)

    def _quick_start_ollama(self):
        """快捷启动 Ollama"""
        self.ollama_quick_btn.setEnabled(False)
        self.ollama_quick_btn.setText("启动中...")
        self.set_notification("正在启动 Ollama 服务...")
        
        def do_start():
            return self.ollama.start_service()
        
        def on_started(result):
            success, msg = result
            if success:
                self.set_notification("✅ Ollama 启动成功", "success")
                self.update_ollama_quick_status(True, True)
                self.refresh_status()
            else:
                self.set_notification(f"❌ 启动失败: {msg}", "error")
                self.ollama_quick_btn.setEnabled(True)
                self.ollama_quick_btn.setText("🚀 一键启动")
            
            self.settings_page.update_ollama_status(
                self.ollama.is_running(),
                self.ollama.is_installed()
            )
        
        self.worker = WorkerThread(do_start)
        self.worker.finished.connect(on_started)
        self.worker.start()

    def _open_ollama_download(self):
        """打开 Ollama 下载页面"""
        import webbrowser
        # TODO: 替换为实际下载链接
        webbrowser.open("https://ollama.com/download")

    def create_sidebar_footer(self, parent_layout):
        """创建侧边栏底部（移除模型状态显示）"""
        footer = QWidget()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 10, 0, 0)
        footer_layout.setSpacing(10)
        
        separator = QFrame()
        separator.setFixedHeight(1)
        footer_layout.addWidget(separator)
        
        # 只保留 Ollama 服务状态
        self.status_indicator = StatusIndicator()
        footer_layout.addWidget(self.status_indicator)
        
        parent_layout.addWidget(footer)
    
    def create_notification_bar(self, parent_layout):
        """通知栏"""
        self.notification = QWidget()
        self.notification.setFixedHeight(42)
        
        layout = QHBoxLayout(self.notification)
        layout.setContentsMargins(25, 0, 25, 0)
        
        self.notification_label = QLabel("就绪")
        self.notification_label.setFont(QFont("Microsoft YaHei UI", 11))
        layout.addWidget(self.notification_label)
        
        layout.addStretch()
        
        version = QLabel("v1.0.0")
        version.setFont(QFont("Microsoft YaHei UI", 10))
        layout.addWidget(version)
        
        parent_layout.addWidget(self.notification)
        
        self.apply_notification_theme()
    
    def apply_sidebar_theme(self):
        """应用侧边栏主题"""
        c = self.theme.colors
        
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {c['sidebar_bg']};
                border-right: 1px solid {c['border']};
            }}
        """)
        
        self.new_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        
        # 历史记录滚动条样式
        if hasattr(self, 'history_scroll'):
            self.history_scroll.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
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
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical,
                QScrollBar::sub-page:vertical {{
                    background: none;
                }}
            """)
    
    def apply_notification_theme(self):
        """应用通知栏主题"""
        c = self.theme.colors
        
        self.notification.setStyleSheet(f"""
            background-color: {c['notification_bg']};
            border-top: 1px solid {c['border']};
        """)
        
        self.notification_label.setStyleSheet(f"color: {c['text_secondary']};")
    
    def on_theme_changed(self, theme):
        """主题更改"""
        self.setStyleSheet(get_stylesheet(theme))
        self.apply_sidebar_theme()
        self.apply_notification_theme()
    
    @Slot(str, str, str, list, int)
    def on_personal_changed(self, user_name: str, avatar_path: str, avatar_color: str, 
                            backgrounds: list, interval: int):
        """个性化设置变化"""
        self.chat_page.set_user_name(user_name)
        self.chat_page.set_user_avatar(avatar_path if avatar_path else None, avatar_color)
        self.chat_page.set_chat_backgrounds(backgrounds, interval)
    
    def load_personal_settings(self):
        """加载个性化设置并应用到对话页面"""
        from core.database import get_database
        from core.media_manager import get_media_manager
        
        # 从数据库加载个性化设置
        db = get_database()
        user_name = db.get_personal_setting('user_name', '我')
        avatar_path = db.get_personal_setting('user_avatar_path')
        avatar_color = db.get_personal_setting('user_avatar_color', '#007AFF')
        backgrounds = db.get_personal_setting('chat_backgrounds', [])
        interval = db.get_personal_setting('background_interval', 5)
        
        print(f"[DEBUG] 从数据库加载个性化设置:")
        print(f"[DEBUG]   user_name: {user_name}")
        print(f"[DEBUG]   avatar_path: {avatar_path}")
        print(f"[DEBUG]   avatar_color: {avatar_color}")
        print(f"[DEBUG]   backgrounds: {backgrounds}")
        print(f"[DEBUG]   interval: {interval}")
        
        # 转换背景图片为绝对路径
        media_manager = get_media_manager()
        
        absolute_backgrounds = []
        for bg in backgrounds:
            abs_path = media_manager.get_absolute_path(bg)
            if os.path.exists(abs_path):
                absolute_backgrounds.append(abs_path)
        
        # 应用到对话页面（头像路径保持相对路径，由 ChatBubble 处理）
        self.chat_page.set_user_name(user_name)
        self.chat_page.set_user_avatar(avatar_path, avatar_color)
        self.chat_page.set_chat_backgrounds(absolute_backgrounds, interval)
    
    def load_personal_backgrounds(self):
        """仅加载个性化背景设置"""
        import json
        import sys
        from core.media_manager import get_media_manager
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_path = os.path.join(base_dir, 'personal_settings.json')
        
        backgrounds = []
        interval = 5
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                backgrounds = data.get('chat_backgrounds', [])
                interval = data.get('background_interval', 5)
            except Exception as e:
                print(f"加载背景设置失败: {e}")
        
        # 转换为绝对路径
        media_manager = get_media_manager()
        absolute_backgrounds = []
        for bg in backgrounds:
            abs_path = media_manager.get_absolute_path(bg)
            if os.path.exists(abs_path):
                absolute_backgrounds.append(abs_path)
        
        self.chat_page.set_chat_backgrounds(absolute_backgrounds, interval)

    def connect_signals(self):
        """连接信号"""
        self.chat_page.settings_clicked.connect(self.show_settings)
        self.chat_page.send_message.connect(self.send_message)
        self.chat_page.model_changed.connect(self.on_model_changed)
        
        self.settings_page.back_clicked.connect(self.show_chat)
        self.settings_page.start_ollama.connect(self.start_ollama)
        self.settings_page.refresh_status.connect(self.refresh_status)
        self.settings_page.download_model.connect(self.download_model)  # 现在接收两个参数
        self.settings_page.load_model.connect(self.load_model)
        self.settings_page.uninstall_model.connect(self.uninstall_model)
        self.settings_page.theme_changed.connect(self.on_theme_setting_changed)

        self.settings_page.personal_changed.connect(self.on_personal_changed)
        self.theme.theme_changed.connect(self.apply_theme)
        # 人格相关
        self.chat_page.new_chat_with_persona.connect(self.new_chat_with_persona)
        self.settings_page.persona_added.connect(self.add_persona)
        self.settings_page.persona_deleted.connect(self.delete_persona)
        self.settings_page.persona_edited.connect(self.edit_persona)

    def show_chat(self):
        """显示聊天页面"""
        self.main_stack.setCurrentWidget(self.chat_container)
    
    def show_settings(self):
        """显示设置页面"""
        self.refresh_settings_data()
        self.main_stack.setCurrentWidget(self.settings_page)
    
    def refresh_settings_data(self):
        """刷新设置页面数据（保留下载状态）"""
        running = self.ollama.is_running()
        installed = self.ollama.is_installed()
        self.settings_page.update_ollama_status(running, installed)
        
        hw_info = detect_hardware()
        self.settings_page.update_hardware_info(hw_info)
        
        # 优先从 Ollama 获取已安装模型，如果服务未运行则从数据库获取
        if running:
            installed_models_raw = self.ollama.list_models()
            # 为每个模型添加精简名称
            installed_models = []
            for model in installed_models_raw:
                ollama_name = model.get('name', '')
                # 从下载记录中查找对应的精简名称
                record = self.model_manager.get_download_record(ollama_name)
                if record:
                    display_name = record.get('model_name', ollama_name)
                else:
                    # 如果找不到记录，尝试从 ollama 名称提取
                    display_name = ollama_name.split(':')[0].replace('_', ' ').title()
                
                installed_models.append({
                    "name": display_name,  # 精简名称用于显示
                    "ollama_name": ollama_name,  # 完整名称用于操作
                    "size": model.get('size', ''),
                    "modified": model.get('modified', '')
                })
        else:
            # 从数据库下载记录中获取已安装的模型
            download_records = self.model_manager.list_download_records()
            installed_models = []
            for record in download_records:
                # 检查文件是否存在
                gguf_path = record.get('gguf_path', '')
                if gguf_path and os.path.exists(gguf_path):
                    size_bytes = os.path.getsize(gguf_path)
                    size_gb = size_bytes / (1024**3)
                    installed_models.append({
                        "name": record.get('model_name', ''),  # 精简名称
                        "ollama_name": record.get('ollama_name', ''),  # 完整名称
                        "size": f"{size_gb:.2f} GB",
                        "modified": record.get('download_time', '')
                    })
        
        # update_models 会自动恢复下载状态
        self.settings_page.update_models(
            self.model_manager.RECOMMENDED_MODELS,
            installed_models
        )
        
        # 更新助手列表
        personas = self.chat_manager.get_personas()
        self.settings_page.update_personas(personas)

    @Slot(str)
    def new_chat_with_persona(self, persona_key: str):
        """使用指定人格创建新对话"""
        from core.media_manager import get_media_manager
        
        self.save_current_chat()
        chat_id = self.chat_manager.new_chat(persona_key)
        self.current_chat_id = chat_id
        
        # 获取人格信息
        persona = self.chat_manager.get_current_persona()
        
        # 更新 UI
        self.chat_page.clear_messages()
        self.chat_page.clear_welcome()
        self.chat_page.set_title(f"新对话 - {persona.get('name', '默认')}")
        
        # 设置 AI 名称和头像
        ai_name = persona.get('name', '默认助手')
        ai_icon_path = persona.get('icon_path', '')
        
        # 转换为绝对路径
        media_manager = get_media_manager()
        if ai_icon_path:
            ai_icon_path = media_manager.get_absolute_path(ai_icon_path)
            if not os.path.exists(ai_icon_path):
                ai_icon_path = None
        
        self.chat_page.set_ai_name(ai_name)
        self.chat_page.set_ai_avatar(ai_icon_path)
        
        # 设置背景图片（优先使用角色的背景，如果没有则使用个性化设置）
        background_images_str = persona.get('background_images', '')
        if background_images_str:
            try:
                background_images = json.loads(background_images_str)
                if background_images:
                    # 转换为绝对路径
                    absolute_backgrounds = []
                    for bg in background_images:
                        abs_path = media_manager.get_absolute_path(bg)
                        if os.path.exists(abs_path):
                            absolute_backgrounds.append(abs_path)
                    
                    if absolute_backgrounds:
                        self.chat_page.set_chat_backgrounds(absolute_backgrounds, 5)
                    elif persona_key == 'default':
                        self.load_personal_backgrounds()
                    else:
                        self.chat_page.set_chat_backgrounds([], 5)
                else:
                    if persona_key == 'default':
                        self.load_personal_backgrounds()
                    else:
                        self.chat_page.set_chat_backgrounds([], 5)
            except:
                if persona_key == 'default':
                    self.load_personal_backgrounds()
                else:
                    self.chat_page.set_chat_backgrounds([], 5)
        else:
            if persona_key == 'default':
                self.load_personal_backgrounds()
            else:
                self.chat_page.set_chat_backgrounds([], 5)
        
        # 取消历史选中
        if self.current_history_item:
            try:
                self.current_history_item.set_active(False)
            except RuntimeError:
                pass
            self.current_history_item = None

    @Slot(str, str, str, str, str, str, str, list)
    def add_persona(self, key: str, name: str, persona_type: str, icon: str, desc: str, prompt: str, icon_path: str = "", backgrounds: list = None):
        """添加助手/角色"""
        self.chat_manager.add_persona(key, name, icon, desc, prompt, icon_path, persona_type, backgrounds)
        self.refresh_personas()
        type_name = "角色" if persona_type == "roleplay" else "助手"
        self.set_notification(f"✅ 已添加{type_name}: {name}", "success")

    @Slot(str)
    def delete_persona(self, key: str):
        """删除助手/角色"""
        # 创建自定义对话框
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除")
        dialog.setFixedWidth(400)
        dialog.setModal(True)
        
        c = self.theme.colors
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 25)
        layout.setSpacing(20)
        
        # 图标和标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)
        
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Segoe UI Emoji", 32))
        title_layout.addWidget(icon_label)
        
        title_text = QLabel("确认删除助手")
        title_text.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title_text.setStyleSheet(f"color: {c['text']};")
        title_layout.addWidget(title_text, 1)
        
        layout.addLayout(title_layout)
        
        # 提示信息
        message = QLabel("确定要删除这个助手/角色吗？\n删除后将无法恢复。")
        message.setFont(QFont("Microsoft YaHei UI", 12))
        message.setStyleSheet(f"color: {c['text_secondary']}; line-height: 1.6;")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(QFont("Microsoft YaHei UI", 12))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border: 2px solid {c['border']};
                border-radius: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['text_dim']};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setFixedSize(100, 40)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['error']};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #c82333;
            }}
        """)
        delete_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            if self.chat_manager.delete_persona(key):
                self.refresh_personas()
                self.set_notification("✅ 已删除", "success")
    
    @Slot(str, str, str, str, str, str, str, list)
    def edit_persona(self, key: str, name: str, persona_type: str, icon: str, desc: str, prompt: str, icon_path: str, backgrounds: list = None):
        """编辑助手/角色"""
        # update_persona expects: key, name, icon, description, system_prompt, icon_path, persona_type, background_images
        self.chat_manager.update_persona(key, name, icon, desc, prompt, icon_path, persona_type, backgrounds)
        self.refresh_personas()
        type_name = "角色" if persona_type == "roleplay" else "助手"
        self.set_notification(f"✅ 已更新{type_name}: {name}", "success")

    def refresh_personas(self):
        """刷新人格列表"""
        personas = self.chat_manager.get_personas()
        self.chat_page.set_personas(personas)
        self.settings_page.update_personas(personas)

    def startup_check(self):
        """启动检查"""
        self.set_notification("正在检测系统状态...")
        
        def check():
            hw_info = detect_hardware()
            running = self.ollama.is_running()
            installed = self.ollama.is_installed()
            auto_started = False
            start_error = None
            
            # 如果已安装但未运行，自动尝试启动
            if installed and not running:
                success, msg = self.ollama.start_service()
                if success:
                    running = True
                    auto_started = True
                else:
                    start_error = msg
            
            models = self.ollama.list_models() if running else []
            return {
                'hw_info': hw_info,
                'running': running, 
                'installed': installed, 
                'models': models,
                'auto_started': auto_started,
                'start_error': start_error
            }
        
        self.worker = WorkerThread(check)
        self.worker.finished.connect(self.on_startup_check_done)
        self.worker.start()
    
    @Slot(object)
    def on_startup_check_done(self, result):
        """启动检查完成"""
        if isinstance(result, Exception):
            self.set_notification(f"检测失败: {result}", "error")
            self.status_indicator.set_status("error", "检测失败")
            return
        
        hw_info = result.get('hw_info')
        running = result.get('running')
        installed = result.get('installed')
        models = result.get('models', [])
        auto_started = result.get('auto_started', False)
        start_error = result.get('start_error')
        
        # 更新硬件信息和状态
        if hw_info:
            self.settings_page.update_hardware_info(hw_info)
        self.settings_page.update_ollama_status(running, installed)
        self.update_ollama_quick_status(installed, running)
        
        if running:
            self.status_indicator.set_status("success", "运行中")
            
            # 如果是自动启动的，显示提示
            if auto_started:
                self.set_notification("✅ Ollama 已自动启动", "success")
            else:
                self.set_notification("✅ 系统就绪", "success")
            
            # 更新模型列表
            self.chat_page.update_models(models)
            
            # 自动选择第一个模型
            if models:
                model_name = models[0]['name']
                self.chat_manager.set_model(model_name)
        elif installed:
            self.status_indicator.set_status("warning", "未运行")
            if start_error:
                self.set_notification(f"⚠️ Ollama 自动启动失败: {start_error}", "warning")
            else:
                self.set_notification("Ollama 已安装但未运行，点击左下角启动")
        else:
            self.status_indicator.set_status("error", "未安装")
            self.set_notification("Ollama 未找到", "error")
        
        # 初始化人格
        self.refresh_personas()
        self.refresh_history()
    
    def refresh_history(self):
        """刷新历史记录"""
         # 刷新前重置引用
        self.current_history_item = None
        # 清空
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        histories = self.chat_manager.list_history()
        
        for h in histories[:30]:
            item = HistoryItem(h)
            item.clicked_with_data.connect(self.load_history)
            item.delete_requested.connect(self.delete_history)
            self.history_layout.insertWidget(self.history_layout.count() - 1, item)
    
    def save_current_chat(self):
        """保存当前对话"""
        if self.current_chat_id:
            try:
                self.chat_manager.save_history(self.current_chat_id)
            except Exception as e:
                print(f"保存对话失败: {e}")

    def new_chat(self):
        """新建对话 - 只显示助手选择"""
        self.save_current_chat()
        self.current_chat_id = None
        
        # 取消历史选中
        if self.current_history_item:
            try:
                self.current_history_item.set_active(False)
            except RuntimeError:
                pass
            self.current_history_item = None
            
        
        # 显示欢迎界面（只显示助手）
        self.chat_page.clear_messages()
        self.chat_page.set_title("新对话")
        self.chat_page.show_welcome_assistants_only()
    
    def new_role_chat(self):
        """新建角色对话 - 只显示角色选择"""
        self.save_current_chat()
        self.current_chat_id = None
        
        # 取消历史选中
        if self.current_history_item:
            try:
                self.current_history_item.set_active(False)
            except RuntimeError:
                pass
            self.current_history_item = None
        
        # 显示欢迎界面（只显示角色）
        self.chat_page.clear_messages()
        self.chat_page.set_title("角色对话")
        self.chat_page.show_welcome_roles_only()

    @Slot(dict)
    def load_history(self, data):
        """加载历史对话"""
        from core.media_manager import get_media_manager
        
        try:
            # 重置当前历史项引用
            if self.current_history_item:
                try:
                    # 检查对象是否仍然有效
                    self.current_history_item.set_active(False)
                except RuntimeError:
                    # 对象已被删除，忽略
                    pass
                self.current_history_item = None
            
            filename = data.get('filename', '')
            chat_id = filename.replace('.json', '')
            
            # 加载对话数据
            loaded = self.chat_manager.load_history(chat_id)
            
            if not loaded:
                self.set_notification("加载失败：对话不存在", "error")
                return
            
            if self.current_history_item:
                self.current_history_item.set_active(False)
            
            sender = self.sender()
            if isinstance(sender, HistoryItem):
                sender.set_active(True)
                self.current_history_item = sender
            
            # 设置标题
            title = loaded.get('title', '对话')
            self.chat_page.set_title(title)
            
            # 获取人格信息
            persona_key = loaded.get('persona', 'default')
            persona = self.chat_manager.get_current_persona()
            
            # 设置 AI 名称和头像
            ai_name = persona.get('name', '默认助手')
            ai_icon_path = persona.get('icon_path', '')
            
            # 转换为绝对路径
            media_manager = get_media_manager()
            if ai_icon_path:
                ai_icon_path = media_manager.get_absolute_path(ai_icon_path)
                if not os.path.exists(ai_icon_path):
                    ai_icon_path = None
            
            self.chat_page.set_ai_name(ai_name)
            self.chat_page.set_ai_avatar(ai_icon_path)
            
            # 设置背景图片（优先使用角色的背景）
            background_images_str = persona.get('background_images', '')
            if background_images_str:
                try:
                    background_images = json.loads(background_images_str)
                    if background_images:
                        # 转换为绝对路径
                        absolute_backgrounds = []
                        for bg in background_images:
                            abs_path = media_manager.get_absolute_path(bg)
                            if os.path.exists(abs_path):
                                absolute_backgrounds.append(abs_path)
                        
                        if absolute_backgrounds:
                            self.chat_page.set_chat_backgrounds(absolute_backgrounds, 5)
                        elif persona_key == 'default':
                            self.load_personal_backgrounds()
                        else:
                            self.chat_page.set_chat_backgrounds([], 5)
                    else:
                        if persona_key == 'default':
                            self.load_personal_backgrounds()
                        else:
                            self.chat_page.set_chat_backgrounds([], 5)
                except:
                    if persona_key == 'default':
                        self.load_personal_backgrounds()
                    else:
                        self.chat_page.set_chat_backgrounds([], 5)
            else:
                if persona_key == 'default':
                    self.load_personal_backgrounds()
                else:
                    self.chat_page.set_chat_backgrounds([], 5)
            
            # 获取所有消息（按时间排序）
            all_messages = self.chat_manager.get_all_messages_sorted()
            
            # 加载消息到 UI
            self.chat_page.load_messages(all_messages)
            
            # 获取最后使用的模型
            last_model = None
            if all_messages:
                # 从最后一条消息获取模型
                last_model = all_messages[-1].get('model')
            
            if last_model:
                self.chat_manager.set_model(last_model)
                self.chat_page.set_model(last_model)  # 自动选择下拉框中的模型
            
            self.current_chat_id = loaded.get('id', chat_id)
            self.show_chat()
            self.set_notification(f"已加载对话：{title}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.set_notification(f"加载失败: {e}", "error")

    @Slot(str)
    def delete_history(self, filename):
        """删除历史记录"""
        # 创建自定义对话框
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除")
        dialog.setFixedWidth(400)
        dialog.setModal(True)
        
        c = self.theme.colors
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 25)
        layout.setSpacing(20)
        
        # 图标和标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)
        
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Segoe UI Emoji", 32))
        title_layout.addWidget(icon_label)
        
        title_text = QLabel("确认删除对话")
        title_text.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title_text.setStyleSheet(f"color: {c['text']};")
        title_layout.addWidget(title_text, 1)
        
        layout.addLayout(title_layout)
        
        # 提示信息
        message = QLabel("确定要删除这条对话记录吗？\n删除后将无法恢复。")
        message.setFont(QFont("Microsoft YaHei UI", 12))
        message.setStyleSheet(f"color: {c['text_secondary']}; line-height: 1.6;")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(QFont("Microsoft YaHei UI", 12))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border: 2px solid {c['border']};
                border-radius: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['text_dim']};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setFixedSize(100, 40)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['error']};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #c82333;
            }}
        """)
        delete_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            if self.chat_manager.delete_history(filename):
                self.refresh_history()
                self.set_notification("已删除对话", "success")
            else:
                self.set_notification("删除失败", "error")
    
    @Slot(str)
    def on_model_changed(self, model_name):
        """模型切换"""
        if model_name:
            # 获取完整的 ollama 名称
            ollama_name = self.chat_page.get_current_ollama_name()
            self.chat_manager.set_model(ollama_name)
            # 显示精简名称给用户
            self.set_notification(f"已切换模型: {model_name}")
    
    @Slot(str)
    def send_message(self, text):
        """发送消息"""
        if not self.chat_manager.current_model:
            QMessageBox.warning(self, "提示", "请先选择模型")
            return
        
        if self.chat_manager.is_generating:
            return
        
        # 如果是新对话，先创建
        if not self.current_chat_id:
            self.current_chat_id = self.chat_manager.new_chat()
        
        self.chat_page.add_user_message(text)
        self.chat_page.set_send_enabled(False)
        self.chat_page.start_ai_response()
        self.set_notification("正在生成回复...")
        
        self.ai_response_text = ""
        
        def stream_callback(chunk):
            self.ai_response_text += chunk
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self.chat_page,
                "update_ai_response",
                Qt.QueuedConnection,
                Q_ARG(str, self.ai_response_text)
            )
        
        def do_chat():
            return self.chat_manager.chat(text, stream_callback=stream_callback)
        
        self.worker = WorkerThread(do_chat)
        self.worker.finished.connect(self.on_chat_done)
        self.worker.start()

    @Slot(object)
    def on_chat_done(self, result):
        """聊天完成回调"""
        self.chat_page.finish_ai_response()
        self.chat_page.set_send_enabled(True)
        
        if isinstance(result, Exception):
            self.set_notification(f"生成失败: {result}", "error")
        else:
            self.set_notification("生成完成", "success")
            
            # 更新标题
            title = self.chat_manager.get_title()
            self.chat_page.set_title(title)
            
            # 保存对话
            if self.current_chat_id:
                self.chat_manager.save_history(self.current_chat_id)
                self.refresh_history()
    
    def start_ollama(self):
        """启动 Ollama"""
        self.set_notification("正在启动 Ollama 服务...")
        
        def start():
            return self.ollama.start_service()

        def on_started(result):
            success, msg = result
            if success:
                self.set_notification("✅ Ollama 启动成功", "success")
                # ===== 添加这行 =====
                self.update_ollama_quick_status(True, True)
                # ===== 添加结束 =====
                self.refresh_models()
            else:
                self.set_notification(f"❌ 启动失败: {msg}", "error")
            
            self.settings_page.update_ollama_status(
                self.ollama.is_running(),
                self.ollama.is_installed()
            )

        self.worker = WorkerThread(start)
        self.worker.finished.connect(self.on_ollama_started)
        self.worker.start()
    
    @Slot(object)
    def on_ollama_started(self, result):
        """Ollama 启动完成"""
        if isinstance(result, tuple):
            success, msg = result
            if success:
                self.status_indicator.set_status("success", "运行中")
                self.settings_page.update_ollama_status(True, True)
                self.set_notification("Ollama 服务已启动", "success")
                
                # 刷新模型列表
                models = self.ollama.list_models()
                self.chat_page.update_models(models)
                self.refresh_settings_data()
            else:
                self.set_notification(f"启动失败: {msg}", "error")
        else:
            self.set_notification("启动失败", "error")
    
    def refresh_status(self):
        """刷新状态"""
        self.refresh_settings_data()
        
        running = self.ollama.is_running()
        if running:
            self.status_indicator.set_status("success", "运行中")
            models = self.ollama.list_models()
            self.chat_page.update_models(models)
        else:
            self.status_indicator.set_status("warning", "未运行")
        
        self.set_notification("已刷新状态")
    
    @Slot(str, str)
    def download_model(self, model_name: str, quantization: str = ''):
        """下载模型"""
        if not self.ollama.is_running():
            QMessageBox.warning(self, "提示", "请先启动 Ollama 服务")
            self.settings_page.finish_download(model_name, False)
            return
        
        self.current_download_model = model_name
        self.current_download_quant = quantization
        
        quant_info = f" ({quantization})" if quantization else ""
        self.set_notification(f"正在下载 {model_name}{quant_info}...")
        
        self.download_start_time = datetime.now()
        
        def update_ui_progress(percent, msg):
            """更新 UI 进度（线程安全）"""
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            
            # 计算剩余时间
            elapsed = (datetime.now() - self.download_start_time).total_seconds()
            if percent > 10 and elapsed > 0:
                remaining = (elapsed / percent) * (100 - percent)
                if remaining > 60:
                    time_str = f" - 剩余约 {int(remaining / 60)} 分钟"
                else:
                    time_str = f" - 剩余约 {int(remaining)} 秒"
                display_msg = f"{msg}{time_str}"
            else:
                display_msg = msg
            
            QMetaObject.invokeMethod(
                self.settings_page,
                "update_download_progress",
                Qt.QueuedConnection,
                Q_ARG(str, self.current_download_model),
                Q_ARG(int, percent),
                Q_ARG(str, display_msg)
            )
            QMetaObject.invokeMethod(
                self,
                "set_notification",
                Qt.QueuedConnection,
                Q_ARG(str, display_msg)
            )
        
        def do_download():
            # 下载模型（progress_callback 现在接收 percent 和 msg）
            gguf_path, ollama_name, error = self.model_manager.download_model(
                model_name, 
                progress_callback=update_ui_progress,
                quantization=quantization if quantization else None
            )
            
            if error:
                return False, error, None
            
            update_ui_progress(95, "正在导入到 Ollama...")
            
            # 导入到 Ollama
            def ollama_progress(msg):
                update_ui_progress(97, msg)
            
            success = self.ollama.create_model_from_gguf(ollama_name, gguf_path, ollama_progress)
            
            if success:
                update_ui_progress(100, "安装完成!")
                return True, model_name, ollama_name
            else:
                return False, "导入 Ollama 失败", None
        
        self.worker = WorkerThread(do_download)
        self.worker.finished.connect(self.on_download_done)
        self.worker.start()

    @Slot(object)
    def on_download_done(self, result):
        """下载完成回调"""
        model_name = self.current_download_model
        
        success = False
        ollama_name = None
        
        if isinstance(result, tuple):
            if len(result) == 3:
                success, msg, ollama_name = result
            elif len(result) == 2:
                success, msg = result
            
            if success:
                self.set_notification(f"✅ {msg} 安装成功!", "success")
                
                # 重要：先刷新模型列表
                models = self.ollama.list_models()
                self.chat_page.update_models(models)
                
                # 刷新设置页面（这会重新渲染模型卡片）
                self.refresh_settings_data()
                
                # 通知设置页面下载完成
                self.settings_page.finish_download(model_name, True)
                
                # 自动选择该模型
                if ollama_name:
                    self.chat_manager.set_model(ollama_name)
                    self.chat_page.set_model(ollama_name)
                    #self.current_model_label.setText(ollama_name)
            else:
                self.set_notification(f"❌ 失败: {msg}", "error")
                self.settings_page.finish_download(model_name, False)
        else:
            self.set_notification("❌ 下载失败", "error")
            self.settings_page.finish_download(model_name, False)
        
        self.current_download_model = None
        self.current_download_quant = None

    @Slot(str)
    def load_model(self, model_name):
        """加载模型"""
        # 查找实际的 Ollama 模型名
        models = self.ollama.list_models()
        actual_name = None
        
        simple_name = model_name.lower().replace('-', '').replace('.', '')
        for m in models:
            m_simple = m['name'].split(':')[0].lower().replace('-', '').replace('.', '')
            if simple_name in m_simple or m_simple in simple_name:
                actual_name = m['name']
                break
        
        if actual_name:
            self.chat_manager.set_model(actual_name)
            self.chat_page.set_model(actual_name)
            #self.current_model_label.setText(actual_name)
            self.set_notification(f"已加载模型: {actual_name}")
            self.show_chat()
        else:
            self.set_notification(f"未找到模型: {model_name}", "error")
    
    @Slot(str)
    def uninstall_model(self, model_name: str):
        """卸载模型（包括删除 GGUF 文件）"""
        # 创建自定义对话框
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        dialog = QDialog(self)
        dialog.setWindowTitle("确认卸载")
        dialog.setFixedWidth(450)
        dialog.setModal(True)
        
        c = self.theme.colors
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 25)
        layout.setSpacing(20)
        
        # 图标和标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)
        
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Segoe UI Emoji", 32))
        title_layout.addWidget(icon_label)
        
        title_text = QLabel("确认卸载模型")
        title_text.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title_text.setStyleSheet(f"color: {c['text']};")
        title_layout.addWidget(title_text, 1)
        
        layout.addLayout(title_layout)
        
        # 模型名称
        model_label = QLabel(f"模型：{model_name}")
        model_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        model_label.setStyleSheet(f"color: {c['accent']}; padding: 10px; background-color: {c['bg_tertiary']}; border-radius: 8px;")
        layout.addWidget(model_label)
        
        # 提示信息
        message = QLabel("这将同时删除：\n• Ollama 中的模型\n• 对应的 GGUF 文件\n\n卸载后需要重新下载才能使用。")
        message.setFont(QFont("Microsoft YaHei UI", 11))
        message.setStyleSheet(f"color: {c['text_secondary']}; line-height: 1.8;")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(QFont("Microsoft YaHei UI", 12))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border: 2px solid {c['border']};
                border-radius: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-color: {c['text_dim']};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        uninstall_btn = QPushButton("卸载")
        uninstall_btn.setFixedSize(100, 40)
        uninstall_btn.setCursor(Qt.PointingHandCursor)
        uninstall_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        uninstall_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['error']};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #c82333;
            }}
        """)
        uninstall_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(uninstall_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            self.set_notification(f"正在卸载 {model_name}...")
            
            # 1. 从下载记录中获取完整的 ollama 名称
            record = self.model_manager.get_download_record(model_name)
            
            if not record:
                self.set_notification("❌ 未找到模型记录", "error")
                return
            
            ollama_name = record.get('ollama_name', '')
            gguf_path = record.get('gguf_path', '')
            quantization = record.get('quantization', '')
            
            print(f"[卸载] 精简名称: {model_name}")
            print(f"[卸载] 记录中的Ollama名称: {ollama_name}")
            print(f"[卸载] GGUF路径: {gguf_path}")
            print(f"[卸载] 量化版本: {quantization}")
            
            # 2. 从 Ollama 中删除模型
            ollama_deleted = False
            
            # 获取 Ollama 中所有模型，找到匹配的
            if self.ollama.is_running():
                ollama_models = self.ollama.list_models()
                print(f"[卸载] Ollama中的模型列表: {[m.get('name', '') for m in ollama_models]}")
                
                # 尝试多种匹配方式
                possible_names = []
                
                # 1. 使用记录中的名称
                if ollama_name:
                    possible_names.append(ollama_name)
                    if ':' not in ollama_name:
                        possible_names.append(f"{ollama_name}:latest")
                
                # 2. 使用标准格式：模型名-量化版本
                if quantization:
                    standard_name = f"{model_name}-{quantization}"
                    possible_names.append(standard_name)
                    possible_names.append(f"{standard_name}:latest")
                    # 尝试小写
                    possible_names.append(standard_name.lower())
                    possible_names.append(f"{standard_name.lower()}:latest")
                
                # 3. 在 Ollama 模型列表中查找匹配
                for ollama_model in ollama_models:
                    ollama_model_name = ollama_model.get('name', '')
                    # 检查是否匹配（不区分大小写）
                    if any(pn.lower() == ollama_model_name.lower() for pn in possible_names):
                        print(f"[卸载] 找到匹配的模型: {ollama_model_name}")
                        if self.ollama.delete_model(ollama_model_name):
                            ollama_deleted = True
                            print(f"[卸载] ✅ 成功删除 Ollama 模型: {ollama_model_name}")
                            break
                    # 也检查模型名称是否包含精简名称和量化版本
                    elif model_name.lower() in ollama_model_name.lower() and quantization.lower() in ollama_model_name.lower():
                        print(f"[卸载] 通过模糊匹配找到模型: {ollama_model_name}")
                        if self.ollama.delete_model(ollama_model_name):
                            ollama_deleted = True
                            print(f"[卸载] ✅ 成功删除 Ollama 模型: {ollama_model_name}")
                            break
                
                if not ollama_deleted:
                    print(f"[卸载] ⚠️ 未找到匹配的 Ollama 模型")
            else:
                print(f"[卸载] ⚠️ Ollama 服务未运行，跳过模型删除")
            
            # 3. 删除 GGUF 文件
            gguf_deleted = False
            if gguf_path and os.path.exists(gguf_path):
                try:
                    os.remove(gguf_path)
                    gguf_deleted = True
                    print(f"[卸载] ✅ 成功删除 GGUF 文件: {gguf_path}")
                except Exception as e:
                    print(f"[卸载] ⚠️ 删除 GGUF 文件失败: {e}")
            
            # 4. 删除下载记录
            record_key = record.get('record_key', '')
            if record_key:
                self.model_manager.remove_download_record(record_key)
                print(f"[卸载] ✅ 已删除下载记录: {record_key}")
            
            # 汇总结果
            if ollama_deleted or gguf_deleted:
                msg_parts = []
                if ollama_deleted:
                    msg_parts.append("Ollama 模型")
                if gguf_deleted:
                    msg_parts.append("GGUF 文件")
                
                self.set_notification(f"✅ 已卸载: {', '.join(msg_parts)}", "success")
                
                # 刷新界面
                self.refresh_settings_data()
            else:
                self.set_notification("❌ 卸载失败，未找到相关文件", "error")

    @Slot(str)
    def on_theme_setting_changed(self, theme_name):
        """主题设置更改"""
        self.set_notification(f"已切换到{self.theme.current['display_name']}主题")
    
    def apply_theme(self, theme=None):
        """应用主题样式"""
        c = self.theme.colors
        
        # 主窗口背景
        self.setStyleSheet(f"background-color: {c['bg']};")
        
        # 侧边栏样式
        if hasattr(self, 'sidebar'):
            self.sidebar.setStyleSheet(f"""
                background-color: {c['sidebar_bg']};
                border-right: 1px solid {c['border']};
            """)
        
        # 新建对话按钮
        if hasattr(self, 'new_chat_btn'):
            self.new_chat_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent']};
                    color: white;
                    border-radius: 10px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {c['accent_hover']};
                }}
            """)
        
        # 角色对话按钮
        if hasattr(self, 'role_chat_btn'):
            self.role_chat_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['card_bg']};
                    color: {c['text']};
                    border: 2px solid {c['accent']};
                    border-radius: 10px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {c['accent']};
                    color: white;
                }}
            """)
        
        # 历史记录标题
        if hasattr(self, 'history_title'):
            self.history_title.setStyleSheet(f"color: {c['text_secondary']};")
        
        # 通知栏
        if hasattr(self, 'notification'):
            self.notification.setStyleSheet(f"""
                background-color: {c['notification_bg']};
                border-top: 1px solid {c['border']};
            """)
        
        if hasattr(self, 'notification_label'):
            self.notification_label.setStyleSheet(f"color: {c['text']};")
        
        # 更新 Ollama 快捷按钮样式
        if hasattr(self, 'ollama_status_label'):
            self.update_ollama_quick_status(
                self.ollama.is_installed(),
                self.ollama.is_running()
            )
    
    def resizeEvent(self, event):
        """窗口大小改变事件 - 更新背景图片"""
        super().resizeEvent(event)
        
        # 窗口大小改变时，更新聊天背景
        if hasattr(self, 'chat_page'):
            self.chat_page.update_background_on_resize()
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 捕获双击空白处"""
        from PySide6.QtCore import QEvent, QTime
        from PySide6.QtWidgets import QPushButton, QLabel, QScrollArea
        
        if event.type() == QEvent.MouseButtonDblClick:
            # 获取点击的控件
            widget = self.childAt(event.pos())
            
            # 如果点击的是空白区域（背景或容器）
            if widget is None or isinstance(widget, (QWidget, QFrame)) and not isinstance(widget, (QPushButton, QLabel, QScrollArea)):
                # 切换角色对话按钮的可见性
                self.role_chat_btn.setVisible(not self.role_chat_btn.isVisible())
                return True
        
        return super().eventFilter(obj, event)

    @Slot(str, str)
    def set_notification(self, text: str, level: str = "info"):
        """设置通知"""
        c = self.theme.colors
        colors = {
            "info": c['text_secondary'],
            "success": c['success'],
            "warning": c['warning'],
            "error": c['error']
        }
        color = colors.get(level, c['text_secondary'])
        
        # 添加图标
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icons.get(level, "")
        
        # 如果消息本身已经包含图标，就不添加
        if any(emoji in text for emoji in ["✅", "❌", "⚠️", "ℹ️", "🚀", "📥", "📊"]):
            display_text = text
        else:
            display_text = f"{icon} {text}" if icon else text
        
        self.notification_label.setStyleSheet(f"color: {color}; font-weight: 500;")
        self.notification_label.setText(display_text)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.ollama.stop_service()
        event.accept()


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("AI 助手")
    app.setOrganizationName("LocalLLM")
    
    # 设置图标
    icon_path = os.path.join(BASE_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()