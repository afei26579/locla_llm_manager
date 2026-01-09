"""可复用 UI 组件"""
import os
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from .themes import get_theme_manager


def parse_roleplay_content(text: str, theme_colors: dict = None) -> str:
    """解析角色扮演内容，转换为富文本HTML
    
    格式规则：
    - (动作/神情/心理) → 斜体灰色
    - "对话内容" → 主题适配的高亮色
    - 其他文本 → 普通样式
    
    支持中英文括号和引号
    
    Args:
        text: 要解析的文本
        theme_colors: 主题颜色字典，如果不传则自动获取
    """
    if not text:
        return ""
    
    # 获取主题颜色
    if theme_colors is None:
        theme = get_theme_manager()
        theme_colors = theme.colors
    
    # 根据主题选择对话颜色
    # 深色主题用浅色，浅色主题用深色
    dialogue_color = theme_colors.get('text', '#2c3e50')
    action_color = theme_colors.get('text_dim', '#888888')
    
    # 用占位符保护要替换的内容，避免HTML转义问题
    placeholders = []
    placeholder_idx = 0
    
    def save_placeholder(match, style_type):
        nonlocal placeholder_idx
        content = match.group(1)
        # 转义内容中的HTML特殊字符
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if style_type == 'action':
            html = f'<span style="color:{action_color};font-style:italic;">({content})</span>'
        else:
            # 对话内容使用主题文本色
            html = f'"<span style="color:{dialogue_color};font-weight:500;">{content}</span>"'
        placeholders.append(html)
        placeholder_idx += 1
        return f'\x00{placeholder_idx - 1}\x00'
    
    # 先用占位符替换括号内容
    text = re.sub(r'[（\(]([^）\)]*)[）\)]', lambda m: save_placeholder(m, 'action'), text)
    
    # 再用占位符替换引号内容
    text = re.sub(r'[""「]([^""」]*)[""」]', lambda m: save_placeholder(m, 'dialogue'), text)
    
    # 转义剩余文本中的HTML特殊字符
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # 还原占位符
    for i, html in enumerate(placeholders):
        text = text.replace(f'\x00{i}\x00', html)
    
    # 处理换行
    text = text.replace('\n', '<br>')
    
    return text


def extract_think_content(text: str) -> tuple:
    """提取思考内容和正文内容
    
    支持多种标签格式和不完整标签
    
    Returns:
        (think_content, main_content) - 思考内容和正文内容
    """
    think_parts = []
    
    # 完整标签匹配
    tag_patterns = [
        r'<think>(.*?)</think>',
        r'<thinking>(.*?)</thinking>',
        r'<reasoning>(.*?)</reasoning>',
    ]
    
    for pattern in tag_patterns:
        matches = re.findall(pattern, text, flags=re.DOTALL)
        think_parts.extend(matches)
    
    # 处理模板残留后跟思考内容
    template_patterns = [
        r'<\|im_end\|?>+(.*?)</think>',
        r'<\|im_end\|?>+(.*?)</thinking>',
        r'<\|im_end\|?>+(.*?)</reasoning>',
    ]
    for pattern in template_patterns:
        matches = re.findall(pattern, text, flags=re.DOTALL)
        think_parts.extend(matches)
    
    # 处理 > 后跟思考内容到 </think> 的情况
    incomplete_patterns = [
        r'>([^<]*)</think>',
        r'>([^<]*)</thinking>',
        r'>([^<]*)</reasoning>',
    ]
    for pattern in incomplete_patterns:
        matches = re.findall(pattern, text, flags=re.DOTALL)
        think_parts.extend(matches)
    
    # 处理文本开头的不完整结束标签
    start_incomplete = [
        r'^([^<]*)</think>',
        r'^([^<]*)</thinking>',
        r'^([^<]*)</reasoning>',
    ]
    for pattern in start_incomplete:
        match = re.match(pattern, text, flags=re.DOTALL)
        if match:
            think_parts.append(match.group(1))
    
    # 处理只有开始标签（流式输出中）
    incomplete_start_patterns = [
        r'<think>([^<]*)$',
        r'<thinking>([^<]*)$',
        r'<reasoning>([^<]*)$',
    ]
    for pattern in incomplete_start_patterns:
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            think_parts.append(match.group(1))
    
    think_content = '\n'.join([p.strip() for p in think_parts if p.strip()])
    
    # 移除所有思考标签得到正文
    main_content = text
    
    # 完整标签
    for pattern in tag_patterns:
        main_content = re.sub(pattern, '', main_content, flags=re.DOTALL)
    
    # 模板残留 + 思考内容
    template_remove = [
        r'<\|im_end\|?>+.*?</think>',
        r'<\|im_end\|?>+.*?</thinking>',
        r'<\|im_end\|?>+.*?</reasoning>',
    ]
    for pattern in template_remove:
        main_content = re.sub(pattern, '', main_content, flags=re.DOTALL)
    
    # > 后的思考内容
    for pattern in incomplete_patterns:
        main_content = re.sub(r'>' + pattern[1:], '>', main_content, flags=re.DOTALL)
    
    # 文本开头的不完整标签
    for pattern in start_incomplete:
        main_content = re.sub(pattern, '', main_content, flags=re.DOTALL)
    
    # 只有开始标签
    incomplete_start_remove = [
        r'<think>[^<]*$',
        r'<thinking>[^<]*$',
        r'<reasoning>[^<]*$',
    ]
    for pattern in incomplete_start_remove:
        main_content = re.sub(pattern, '', main_content, flags=re.DOTALL)
    
    # 清理模板残留
    main_content = re.sub(r'<\|im_end\|?>+', '', main_content)
    main_content = re.sub(r'<\|im_start\|?>+', '', main_content)
    
    # 清理多余空行
    main_content = re.sub(r'\n{3,}', '\n\n', main_content).strip()
    
    return think_content, main_content


class ChatBubble(QFrame):
    """聊天气泡"""
    
    def __init__(self, text: str, is_user: bool = False, 
                 name: str = None, avatar_path: str = None, 
                 icon: str = None, timestamp: str = None, 
                 is_roleplay: bool = False, is_streaming: bool = False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.text = text
        self.name = name
        self.avatar_path = avatar_path
        self.icon = icon  # 助手的 emoji 图标
        self.timestamp = timestamp
        self.is_roleplay = is_roleplay  # 是否是角色扮演模式
        self.theme = get_theme_manager()
        
        # 加载动画相关 - 只有流式响应且文本为空时才启动
        self._loading_timer = None
        self._loading_dots = 0
        self._is_loading = is_streaming and not text  # 只有流式模式且初始文本为空才显示加载动画
        
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)
        
        # 如果是流式模式且空文本，启动加载动画
        if self._is_loading and not is_user:
            self._start_loading_animation()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)
        
        if self.is_user:
            layout.addStretch()
        
        bubble_widget = QWidget()
        bubble_layout = QHBoxLayout(bubble_widget)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.setSpacing(12)
        
        # AI 头像在左边
        if not self.is_user:
            default_emoji = self.icon if self.icon else "🤖"
            self.avatar = self._create_avatar(default_emoji)
            bubble_layout.addWidget(self.avatar, 0, Qt.AlignTop)
        
        # 消息内容区域
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(4)
        
        # 名字 - 用户靠右，AI 靠左
        display_name = self.name if self.name else ("我" if self.is_user else "AI")
        self.name_label = QLabel(display_name)
        self.name_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        if self.is_user:
            self.name_label.setAlignment(Qt.AlignRight)
        else:
            self.name_label.setAlignment(Qt.AlignLeft)
        self.content_layout.addWidget(self.name_label)
        
        # 解析思考内容和正文
        think_content, main_content = '', self.text
        if not self.is_user:
            think_content, main_content = extract_think_content(self.text)
            # 角色扮演模式下不显示思考内容
            if self.is_roleplay:
                think_content = ''
        
        # 思考内容气泡（仅助手模式且有思考内容时显示）
        self.think_bubble = None
        self.think_label = None
        if think_content and not self.is_user and not self.is_roleplay:
            self.think_bubble = QFrame()
            self.think_bubble.setMaximumWidth(550)
            
            think_inner = QVBoxLayout(self.think_bubble)
            think_inner.setContentsMargins(16, 12, 16, 12)
            think_inner.setSpacing(6)
            
            # 思考标题
            think_title = QLabel("💭 思考过程")
            think_title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            think_inner.addWidget(think_title)
            
            # 思考内容
            self.think_label = QLabel(think_content)
            self.think_label.setWordWrap(True)
            self.think_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.think_label.setFont(QFont("Microsoft YaHei UI", 10))
            think_inner.addWidget(self.think_label)
            
            self.content_layout.addWidget(self.think_bubble)
        
        # 主消息气泡
        self.bubble = QFrame()
        self.bubble.setMaximumWidth(550)
        
        bubble_inner = QVBoxLayout(self.bubble)
        bubble_inner.setContentsMargins(16, 12, 16, 12)
        
        # 角色扮演模式使用富文本渲染
        display_text = main_content if not self.is_user else self.text
        if self.is_roleplay and not self.is_user:
            display_text = parse_roleplay_content(main_content, self.theme.colors)
        
        self.message_label = QLabel(display_text)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.message_label.setFont(QFont("Microsoft YaHei UI", 11))
        
        # 角色扮演模式启用富文本
        if self.is_roleplay and not self.is_user:
            self.message_label.setTextFormat(Qt.RichText)
        
        bubble_inner.addWidget(self.message_label)
        
        self.content_layout.addWidget(self.bubble)
        
        # 时间显示
        if self.timestamp:
            time_str = self._format_timestamp(self.timestamp)
            self.time_label = QLabel(time_str)
            self.time_label.setFont(QFont("Microsoft YaHei UI", 9))
            if self.is_user:
                self.time_label.setAlignment(Qt.AlignRight)
            else:
                self.time_label.setAlignment(Qt.AlignLeft)
            self.content_layout.addWidget(self.time_label)
        
        bubble_layout.addWidget(content_widget)
        
        # 用户头像在右边
        if self.is_user:
            self.avatar = self._create_avatar("👤")
            bubble_layout.addWidget(self.avatar, 0, Qt.AlignTop)
        
        layout.addWidget(bubble_widget)
        
        if not self.is_user:
            layout.addStretch()
        
        self.apply_theme()

    def _create_avatar(self, default_emoji: str):
        """创建头像"""
        avatar = QLabel()
        avatar.setFixedSize(80, 80)
        avatar.setAlignment(Qt.AlignCenter)
        
        if self.avatar_path:
            # 使用 MediaManager 获取绝对路径
            from core.media_manager import get_media_manager
            from PySide6.QtGui import QPixmap
            
            media_manager = get_media_manager()
            absolute_path = media_manager.get_absolute_path(self.avatar_path)
            
            if os.path.exists(absolute_path):
                # 使用自定义头像
                pixmap = QPixmap(absolute_path)
                
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    avatar.setPixmap(pixmap)
                    avatar.setStyleSheet("""
                        QLabel {
                            border-radius: 40px;
                            background-color: transparent;
                        }
                    """)
                    return avatar
        
        # 使用默认 emoji
        avatar.setText(default_emoji)
        avatar.setFont(QFont("Segoe UI Emoji", 40))
        
        return avatar
    
    def _format_timestamp(self, timestamp: str) -> str:
        """格式化时间戳，精确到分钟"""
        try:
            from datetime import datetime
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            return timestamp[:16] if len(timestamp) >= 16 else timestamp
        except:
            return ""
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        
        if self.is_user:
            self.bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {c['user_bubble']};
                    border-radius: 18px;
                }}
            """)
            self.message_label.setStyleSheet("color: #ffffff;")
            self.name_label.setStyleSheet(f"color: {c['text_secondary']};")
        else:
            self.bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {c['ai_bubble']};
                    border-radius: 18px;
                }}
            """)
            self.message_label.setStyleSheet(f"color: {c['text']};")
            self.name_label.setStyleSheet(f"color: {c['text_secondary']};")
            
            # 角色扮演模式：主题切换时重新渲染富文本以更新颜色
            if self.is_roleplay and self.text and not self._is_loading:
                _, main_content = extract_think_content(self.text)
                if main_content:
                    rich_text = parse_roleplay_content(main_content, c)
                    self.message_label.setTextFormat(Qt.RichText)
                    self.message_label.setText(rich_text)
            
            # 思考气泡样式（使用不同的背景色）
            if self.think_bubble:
                # 根据主题选择思考气泡的背景色
                think_bg = c.get('think_bubble', c['bg_tertiary'])
                self.think_bubble.setStyleSheet(f"""
                    QFrame {{
                        background-color: {think_bg};
                        border-radius: 14px;
                        border: 1px dashed {c['border']};
                    }}
                """)
                if self.think_label:
                    self.think_label.setStyleSheet(f"color: {c['text_secondary']};")
                # 思考标题样式
                for child in self.think_bubble.findChildren(QLabel):
                    if child != self.think_label:
                        child.setStyleSheet(f"color: {c['text_dim']};")
        
        if hasattr(self, 'time_label'):
            self.time_label.setStyleSheet(f"color: {c['text_dim']};")
    
    def _start_loading_animation(self):
        """启动加载动画"""
        self._loading_timer = QTimer(self)
        self._loading_timer.timeout.connect(self._update_loading_dots)
        self._loading_timer.start(400)
        self._update_loading_dots()
    
    def _stop_loading_animation(self):
        """停止加载动画"""
        if self._loading_timer:
            try:
                self._loading_timer.stop()
            except RuntimeError:
                pass
            self._loading_timer = None
        self._is_loading = False
    
    def _update_loading_dots(self):
        """更新加载动画的点"""
        dots = ["⬤ ○ ○", "○ ⬤ ○", "○ ○ ⬤"]
        self._loading_dots = (self._loading_dots + 1) % 3
        self.message_label.setText(dots[self._loading_dots])
    
    def update_text(self, text: str):
        """更新消息文本（支持流式更新）"""
        # 过滤思考内容后检查是否有实际可见内容
        if not self.is_user:
            think_content, main_content = extract_think_content(text)
            display_text = main_content if self.is_roleplay else main_content
            
            # 只有有实际可见内容时才停止加载动画
            if not display_text or not display_text.strip():
                # 没有可见内容，保持加载动画
                return
            
            # 收到实际内容后停止加载动画
            if self._is_loading:
                self._stop_loading_animation()
            
            self.text = text
            
            # 角色扮演模式：流式输出时用纯文本，避免频繁解析阻塞UI
            if self.is_roleplay:
                # 流式过程中暂时用纯文本显示
                self.message_label.setTextFormat(Qt.PlainText)
                self.message_label.setText(main_content)
            else:
                # 助手模式：分开显示思考和正文
                if think_content and not self.think_bubble:
                    # 需要创建思考气泡
                    self._create_think_bubble(think_content)
                elif think_content and self.think_bubble:
                    # 更新思考内容
                    if self.think_label:
                        self.think_label.setText(think_content)
                
                self.message_label.setText(main_content)
        else:
            if not text or not text.strip():
                return
            if self._is_loading:
                self._stop_loading_animation()
            self.text = text
            self.message_label.setText(text)
    
    def finalize_roleplay_text(self):
        """流式完成后，将角色扮演文本渲染为富文本"""
        if not self.is_roleplay or self.is_user:
            return
        
        _, main_content = extract_think_content(self.text)
        if main_content:
            rich_text = parse_roleplay_content(main_content, self.theme.colors)
            self.message_label.setTextFormat(Qt.RichText)
            self.message_label.setText(rich_text)
    
    def _create_think_bubble(self, think_content: str):
        """动态创建思考气泡"""
        c = self.theme.colors
        
        self.think_bubble = QFrame()
        self.think_bubble.setMaximumWidth(550)
        
        think_inner = QVBoxLayout(self.think_bubble)
        think_inner.setContentsMargins(16, 12, 16, 12)
        think_inner.setSpacing(6)
        
        # 思考标题
        think_title = QLabel("💭 思考过程")
        think_title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        think_title.setStyleSheet(f"color: {c['text_dim']};")
        think_inner.addWidget(think_title)
        
        # 思考内容
        self.think_label = QLabel(think_content)
        self.think_label.setWordWrap(True)
        self.think_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.think_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.think_label.setStyleSheet(f"color: {c['text_secondary']};")
        think_inner.addWidget(self.think_label)
        
        # 设置思考气泡样式
        think_bg = c.get('think_bubble', c['bg_tertiary'])
        self.think_bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {think_bg};
                border-radius: 14px;
                border: 1px dashed {c['border']};
            }}
        """)
        
        # 插入到主气泡之前
        bubble_index = self.content_layout.indexOf(self.bubble)
        self.content_layout.insertWidget(bubble_index, self.think_bubble)
    
    def set_name(self, name: str):
        self.name = name
        self.name_label.setText(name)
    
    def set_avatar(self, avatar_path: str):
        """设置头像"""
        self.avatar_path = avatar_path
        if avatar_path:
            from core.media_manager import get_media_manager
            from PySide6.QtGui import QPixmap
            
            media_manager = get_media_manager()
            absolute_path = media_manager.get_absolute_path(avatar_path)
            
            if os.path.exists(absolute_path):
                pixmap = QPixmap(absolute_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self.avatar.setPixmap(pixmap)
                    self.avatar.setText("")
                    self.avatar.setStyleSheet("""
                        QLabel {
                            border-radius: 40px;
                            background-color: transparent;
                        }
                    """)
                    return
        
        # 恢复默认头像
        self.avatar.setPixmap(QPixmap())
        self.avatar.setText("🤖" if not self.is_user else "👤")
        self.avatar.setStyleSheet("")

class HistoryItem(QPushButton):
    """历史记录项"""
    
    clicked_with_data = Signal(dict)
    delete_requested = Signal(str)
    
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_active = False
        self.theme = get_theme_manager()
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)
    
    def setup_ui(self):
        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QSizePolicy
        from PySide6.QtGui import QPixmap
        from core.media_manager import get_media_manager
        from core.database import get_database
        
        # 设置按钮的最小高度和大小策略
        self.setMinimumHeight(65)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 创建布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(12)
        
        # 获取助手信息
        persona_key = self.data.get('persona', 'default')
        db = get_database()
        persona = db.get_persona(persona_key)
        
        # 头像
        avatar_label = QLabel()
        avatar_label.setFixedSize(45, 45)
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setStyleSheet("border: none; background: transparent;")
        
        if persona:
            icon_path = persona.get('icon_path', '')
            if icon_path:
                media_manager = get_media_manager()
                abs_path = media_manager.get_absolute_path(icon_path)
                if os.path.exists(abs_path):
                    pixmap = QPixmap(abs_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(45, 45, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                        avatar_label.setPixmap(scaled_pixmap)
                        avatar_label.setStyleSheet("border: none; border-radius: 22px; background: transparent;")
                    else:
                        avatar_label.setText(persona.get('icon', '🤖'))
                        avatar_label.setFont(QFont("Segoe UI Emoji", 22))
                        avatar_label.setStyleSheet("border: none; background: transparent;")
                else:
                    avatar_label.setText(persona.get('icon', '🤖'))
                    avatar_label.setFont(QFont("Segoe UI Emoji", 22))
                    avatar_label.setStyleSheet("border: none; background: transparent;")
            else:
                avatar_label.setText(persona.get('icon', '🤖'))
                avatar_label.setFont(QFont("Segoe UI Emoji", 22))
                avatar_label.setStyleSheet("border: none; background: transparent;")
        else:
            avatar_label.setText('🤖')
            avatar_label.setFont(QFont("Segoe UI Emoji", 22))
            avatar_label.setStyleSheet("border: none; background: transparent;")
        
        main_layout.addWidget(avatar_label, 0, Qt.AlignVCenter)
        
        # 文本信息
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题和助手名称
        title = self.data.get('title', '未命名对话')
        if len(title) > 15:
            title = title[:15] + "..."
        
        persona_name = persona.get('name', '默认助手') if persona else '默认助手'
        if len(persona_name) > 10:
            persona_name = persona_name[:10] + "..."
        title_text = f"{title} -- {persona_name}"
        
        self.title_label = QLabel(title_text)
        self.title_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))
        self.title_label.setWordWrap(False)
        self.title_label.setStyleSheet("border: none; background: transparent;")
        text_layout.addWidget(self.title_label)
        
        # 时间和消息数
        timestamp = self.data.get('timestamp', '')[:10]
        msg_count = self.data.get('messages_count', 0)
        
        self.info_label = QLabel(f"{timestamp} · {msg_count}条消息")
        self.info_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.info_label.setStyleSheet("border: none; background: transparent;")
        text_layout.addWidget(self.info_label)
        
        main_layout.addLayout(text_layout, 1)
        
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: self.clicked_with_data.emit(self.data))
        self.apply_theme()
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        
        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['active']};
                    border: 1px solid {c['accent']};
                    border-radius: 10px;
                }}
                QPushButton QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
            if hasattr(self, 'title_label'):
                self.title_label.setStyleSheet(f"color: {c['text']}; border: none; background: transparent;")
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet(f"color: {c['text_secondary']}; border: none; background: transparent;")
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['card_bg']};
                    border: 1px solid {c['border']};
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {c['hover']};
                    border-color: {c['accent']};
                }}
                QPushButton QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
            if hasattr(self, 'title_label'):
                self.title_label.setStyleSheet(f"color: {c['text']}; border: none; background: transparent;")
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet(f"color: {c['text_secondary']}; border: none; background: transparent;")
    
    def set_active(self, active: bool):
        self.is_active = active
        self.apply_theme()
    
    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        c = self.theme.colors
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {c['hover']};
            }}
        """)
        
        delete_action = menu.addAction("🗑️ 删除对话")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.data.get('filename', ''))
        )
        
        menu.exec(event.globalPos())


class ModelCard(QFrame):
    """模型卡片"""
    
    download_clicked = Signal(str, str)  # model_name, quantization
    load_clicked = Signal(str)
    uninstall_clicked = Signal(str)
    
    def __init__(self, name: str, info: dict, is_installed: bool = False, available_vram_gb: float = 0, parent=None):
        super().__init__(parent)
        self.model_name = name
        self.info = info
        self.is_installed = is_installed
        self.available_vram_gb = available_vram_gb  # 可用显存
        self.theme = get_theme_manager()
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)
    
    def setup_ui(self):
        self.setMinimumHeight(115)
        self.setMaximumHeight(125)
        self.setContentsMargins(0, 0, 0, 0)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)
        
        # 左侧：模型信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # 第一行：名称 + 参数量 + 状态
        name_layout = QHBoxLayout()
        name_layout.setSpacing(8)
        name_layout.setAlignment(Qt.AlignVCenter)
        
        self.name_label = QLabel(self.model_name)
        self.name_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        name_layout.addWidget(self.name_label)
        
        params = self.info.get('params', '')
        if params:
            self.params_label = QLabel(params)
            self.params_label.setFont(QFont("Microsoft YaHei UI", 9))
            self.params_label.setFixedHeight(18)
            name_layout.addWidget(self.params_label)
        
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.status_label.setFixedHeight(20)
        self.status_label.setAlignment(Qt.AlignCenter)
        name_layout.addWidget(self.status_label)
        name_layout.addStretch()
        
        info_layout.addLayout(name_layout)
        
        desc = self.info.get('description', '')
        self.desc_label = QLabel(desc)
        self.desc_label.setFont(QFont("Microsoft YaHei UI", 10))
        info_layout.addWidget(self.desc_label)
        
        size = self.info.get('size', '')
        vram = self.info.get('vram', '')
        lang = self.info.get('lang', [])
        lang_str = '中英' if ('zh' in lang and 'en' in lang) else ('中文' if 'zh' in lang else '英文')
        self.spec_label = QLabel(f"📦 {size}  💾 {vram}  🌐 {lang_str}")
        self.spec_label.setFont(QFont("Microsoft YaHei UI", 9))
        info_layout.addWidget(self.spec_label)
        
        layout.addLayout(info_layout, 1)
        
        # 右侧：操作区域
        self._create_action_widget()
        layout.addWidget(self.action_widget)
        
        # 进度条区域
        self._create_progress_widget()
        layout.addWidget(self.progress_widget)
        
        self.apply_theme()
        self.update_status()
    
    def _create_action_widget(self):
        """创建操作按钮区域"""
        self.action_widget = QWidget()
        self.action_widget.setFixedWidth(200)
        action_layout = QVBoxLayout(self.action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)
        action_layout.setAlignment(Qt.AlignCenter)
        
        if self.is_installed:
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(8)
            btn_layout.setAlignment(Qt.AlignCenter)
            
            self.load_btn = QPushButton("加载")
            self.load_btn.setFixedSize(68, 32)
            self.load_btn.setCursor(Qt.PointingHandCursor)
            self.load_btn.clicked.connect(lambda: self.load_clicked.emit(self.model_name))
            btn_layout.addWidget(self.load_btn)
            
            self.uninstall_btn = QPushButton("卸载")
            self.uninstall_btn.setFixedSize(68, 32)
            self.uninstall_btn.setCursor(Qt.PointingHandCursor)
            self.uninstall_btn.clicked.connect(lambda: self.uninstall_clicked.emit(self.model_name))
            btn_layout.addWidget(self.uninstall_btn)
            
            action_layout.addLayout(btn_layout)
        else:
            quantizations = self.info.get('quantizations', [])
            quant_details = self.info.get('quant_details', {})
            
            if quantizations:
                quant_layout = QHBoxLayout()
                quant_layout.setSpacing(6)
                quant_layout.setAlignment(Qt.AlignCenter)
                
                quant_label = QLabel("量化:")
                quant_label.setFont(QFont("Microsoft YaHei UI", 9))
                quant_layout.addWidget(quant_label)
                
                self.quant_combo = QComboBox()
                self.quant_combo.setFixedSize(120, 26)
                self.quant_combo.setFont(QFont("Microsoft YaHei UI", 9))
                
                # 根据显存选择默认的"安全"量化版本
                default_quant = self._get_safe_quantization(quantizations, quant_details)
                
                # 添加量化版本，并显示大小信息
                for q in quantizations:
                    if q in quant_details:
                        detail = quant_details[q]
                        vram_gb = detail.get('vram_gb', 0)
                        # 显示格式：q4_k_m (6.9GB)
                        display_text = f"{q} ({vram_gb}GB)"
                        self.quant_combo.addItem(display_text, q)  # 使用 userData 存储原始量化名
                    else:
                        self.quant_combo.addItem(q, q)
                
                # 设置默认选项
                for i in range(self.quant_combo.count()):
                    if self.quant_combo.itemData(i) == default_quant:
                        self.quant_combo.setCurrentIndex(i)
                        break
                
                # 连接信号，显示详细信息
                self.quant_combo.currentIndexChanged.connect(self._on_quant_changed)
                
                quant_layout.addWidget(self.quant_combo)
                action_layout.addLayout(quant_layout)
                
                # 显示当前选择的推荐等级
                self.quant_info_label = QLabel()
                self.quant_info_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
                self.quant_info_label.setAlignment(Qt.AlignCenter)
                self.quant_info_label.setWordWrap(True)
                self.quant_info_label.setFixedHeight(20)
                action_layout.addWidget(self.quant_info_label)
                self._update_quant_info()
            
            self.download_btn = QPushButton("下载")
            self.download_btn.setFixedSize(90, 32)
            self.download_btn.setCursor(Qt.PointingHandCursor)
            self.download_btn.clicked.connect(self._on_download_clicked)
            action_layout.addWidget(self.download_btn, 0, Qt.AlignCenter)
    
    def _get_safe_quantization(self, quantizations: list, quant_details: dict) -> str:
        """根据可用显存选择"安全"的量化版本
        
        选择策略：
        1. 如果没有显存信息，返回第一个量化版本
        2. 找到所有"安全"的量化版本（显存占用 <= 可用显存 * 0.85）
        3. 在安全版本中选择质量最高的（比特数最大）
        4. 如果没有安全版本，选择最小的量化版本
        
        Args:
            quantizations: 所有可用的量化版本列表
            quant_details: 量化版本的详细信息
        
        Returns:
            推荐的量化版本
        """
        if not quantizations:
            return 'Q4_K_M'
        
        # 如果没有显存信息，返回第一个
        if self.available_vram_gb <= 0:
            return quantizations[0]
        
        # 找到所有"安全"的量化版本（显存占用 <= 85% 可用显存）
        safe_threshold = self.available_vram_gb * 0.85
        safe_quants = []
        
        for quant in quantizations:
            if quant in quant_details:
                detail = quant_details[quant]
                vram_needed = detail.get('vram_gb', 0)
                bits = detail.get('bits', 0)
                
                if vram_needed <= safe_threshold:
                    safe_quants.append({
                        'quant': quant,
                        'vram': vram_needed,
                        'bits': bits
                    })
        
        # 如果有安全版本，选择质量最高的（比特数最大）
        if safe_quants:
            safe_quants.sort(key=lambda x: x['bits'], reverse=True)
            return safe_quants[0]['quant']
        
        # 如果没有安全版本，选择最小的量化版本
        min_quant = quantizations[0]
        min_vram = float('inf')
        
        for quant in quantizations:
            if quant in quant_details:
                vram_needed = quant_details[quant].get('vram_gb', 0)
                if vram_needed < min_vram:
                    min_vram = vram_needed
                    min_quant = quant
        
        return min_quant
    
    def _on_quant_changed(self):
        """量化版本改变时更新信息"""
        self._update_quant_info()
    
    def _get_recommendation_level(self, vram_needed: float) -> tuple:
        """获取推荐等级
        
        Returns:
            (level_text, level_color, level_emoji)
        """
        if self.available_vram_gb <= 0:
            return ("未知", "#888888", "❓")
        
        ratio = vram_needed / self.available_vram_gb
        
        if ratio <= 0.6:
            return ("流畅", "#28a745", "🚀")  # 绿色
        elif ratio <= 0.75:
            return ("安全", "#17a2b8", "✅")  # 青色
        elif ratio <= 0.9:
            return ("推荐", "#ffc107", "👍")  # 黄色
        elif ratio <= 1.05:
            return ("勉强", "#fd7e14", "⚠️")  # 橙色
        else:
            return ("不足", "#dc3545", "❌")  # 红色
    
    def _update_quant_info(self):
        """更新量化版本详细信息"""
        if not hasattr(self, 'quant_info_label') or not hasattr(self, 'quant_combo'):
            return
        
        current_quant = self.quant_combo.currentData()
        quant_details = self.info.get('quant_details', {})
        
        if current_quant and current_quant in quant_details:
            detail = quant_details[current_quant]
            vram_gb = detail.get('vram_gb', 0)
            
            # 获取推荐等级
            level_text, level_color, level_emoji = self._get_recommendation_level(vram_gb)
            
            # 显示推荐等级
            self.quant_info_label.setText(f"{level_emoji} {level_text}")
            self.quant_info_label.setStyleSheet(f"""
                QLabel {{
                    color: {level_color};
                    background-color: {level_color}20;
                    padding: 2px 10px;
                    border-radius: 10px;
                    font-weight: 600;
                    border: none;
                }}
            """)
        else:
            self.quant_info_label.setText("")
            self.quant_info_label.setStyleSheet("")
    
    def _create_progress_widget(self):
        """创建进度条区域"""
        self.progress_widget = QWidget()
        self.progress_widget.setFixedWidth(200)
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)
        progress_layout.setAlignment(Qt.AlignVCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("准备下载...")
        self.progress_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setWordWrap(True)
        self.progress_label.setFixedHeight(32)
        progress_layout.addWidget(self.progress_label)
        
        self.progress_widget.hide()
    
    def _on_download_clicked(self):
        """处理下载按钮点击"""
        quant = ''
        if hasattr(self, 'quant_combo'):
            # 获取 userData 中存储的原始量化名
            quant = self.quant_combo.currentData()
            if not quant:
                quant = self.quant_combo.currentText().split(' ')[0]  # 兼容旧格式
        self.download_clicked.emit(self.model_name, quant)
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        
        self.setStyleSheet(f"""
            ModelCard {{
                background-color: {c['card_bg']};
                border-radius: 12px;
                border: 1px solid {c['border']};
                margin: 0px 8px;
            }}
        """)
        
        self.name_label.setStyleSheet(f"color: {c['text']}; background: transparent; border: none;")
        self.desc_label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent; border: none;")
        self.spec_label.setStyleSheet(f"color: {c['text_dim']}; background: transparent; border: none;")
        self.progress_label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent; border: none;")
        
        # 进度条样式
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['progress_bg']};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {c['accent']};
                border-radius: 4px;
            }}
        """)
        
        if hasattr(self, 'params_label'):
            self.params_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['accent']};
                    background-color: {c['accent']}20;
                    padding: 2px 8px;
                    border-radius: 9px;
                    font-weight: 500;
                    border: none;
                }}
            """)
        
        if hasattr(self, 'quant_combo'):
            self.quant_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {c['input_bg']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: 5px;
                    padding: 3px 6px;
                }}
                QComboBox:hover {{
                    border-color: {c['accent']};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 18px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid {c['text_secondary']};
                }}
                QComboBox QAbstractItemView {{
                    background-color: {c['card_bg']};
                    color: {c['text']};
                    selection-background-color: {c['accent']};
                    border: 1px solid {c['border']};
                    border-radius: 5px;
                }}
            """)
        
        if self.is_installed:
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['success']};
                    background-color: {c['success']}22;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-weight: 500;
                    border: none;
                }}
            """)
            
            if hasattr(self, 'load_btn'):
                self.load_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['success']};
                        color: white;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: #28a745;
                    }}
                """)
            
            if hasattr(self, 'uninstall_btn'):
                self.uninstall_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['error']};
                        color: white;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: #c82333;
                    }}
                """)
        else:
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {c['text_dim']};
                    background-color: {c['bg_tertiary']};
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-weight: 500;
                    border: none;
                }}
            """)
            
            if hasattr(self, 'download_btn'):
                self.download_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['accent']};
                        color: white;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {c['accent_hover']};
                    }}
                """)
    
    def update_status(self):
        if self.is_installed:
            self.status_label.setText("✓ 已安装")
        else:
            self.status_label.setText("未安装")
    
    def start_download(self):
        """开始下载，显示进度条"""
        self.action_widget.hide()
        self.progress_widget.show()
        self.progress_bar.setValue(0)
        self.progress_label.setText("准备下载...")
    
    def update_progress(self, percent: int, text: str):
        """更新下载进度"""
        self.progress_bar.setValue(percent)
        # 截断过长的文本
        if len(text) > 35:
            text = text[:32] + "..."
        self.progress_label.setText(text)
    
    def finish_download(self, success: bool):
        """完成下载"""
        self.progress_widget.hide()
        
        if success:
            self.is_installed = True
            
            # 删除旧的操作区域
            old_widget = self.action_widget
            self.layout().removeWidget(old_widget)
            old_widget.deleteLater()
            
            # 创建新的操作区域（已安装状态）
            self._create_action_widget()
            self.layout().insertWidget(1, self.action_widget)
            
            self.apply_theme()
            self.update_status()
        else:
            self.action_widget.show()
    
    def get_selected_quantization(self):
        """获取当前选择的量化版本"""
        if hasattr(self, 'quant_combo'):
            # 优先从 userData 获取
            quant = self.quant_combo.currentData()
            if quant:
                return quant
            # 兼容旧格式
            return self.quant_combo.currentText().split(' ')[0]
        return ''

class StatusIndicator(QWidget):
    """状态指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme_manager()
        self._status = "checking"
        self._text = "检测中..."
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.dot = QLabel("●")
        self.dot.setFont(QFont("Microsoft YaHei UI", 10))
        layout.addWidget(self.dot)
        
        self.label = QLabel("检测中...")
        self.label.setFont(QFont("Microsoft YaHei UI", 12))
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        self.set_status("checking", "检测中...")
        self.theme.theme_changed.connect(lambda: self.set_status(self._status, self._text))
    
    def set_status(self, status: str, text: str):
        self._status = status
        self._text = text
        
        c = self.theme.colors
        colors = {
            'success': c['success'],
            'warning': c['warning'],
            'error': c['error'],
            'checking': c['text_dim']
        }
        color = colors.get(status, c['text_dim'])
        
        self.dot.setStyleSheet(f"color: {color};")
        self.label.setStyleSheet(f"color: {color};")
        self.label.setText(text)