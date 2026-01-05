"""聊天页面右侧设置面板 - 模型参数"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .themes import get_theme_manager


class CollapsiblePanel(QWidget):
    """可折叠的右侧面板"""
    
    expanded_changed = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._panel_width = 320
        self.theme = get_theme_manager()
        
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)
        
        # 初始状态：收起
        self.setFixedWidth(20)
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 展开/收起按钮容器（用于垂直居中）
        toggle_container = QWidget()
        toggle_container.setFixedWidth(20)
        toggle_layout = QVBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)
        
        toggle_layout.addStretch(1)
        
        # 三角形展开按钮
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedSize(20, 60)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setToolTip("模型参数设置")
        self.toggle_btn.clicked.connect(self.toggle_expand)
        toggle_layout.addWidget(self.toggle_btn)
        
        toggle_layout.addStretch(1)
        
        layout.addWidget(toggle_container)
        
        # 内容区域
        self.content_widget = QWidget()
        self.content_widget.setFixedWidth(self._panel_width - 20)
        self.content_widget.setVisible(False)
        
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(0)
        
        # 直接添加模型参数面板（不使用 Tab）
        self.params_tab = ModelParamsTab()
        content_layout.addWidget(self.params_tab)
        
        layout.addWidget(self.content_widget)
        
        self.apply_theme()
    
    def toggle_expand(self):
        self._expanded = not self._expanded
        
        if self._expanded:
            self.setFixedWidth(self._panel_width)
            self.content_widget.setVisible(True)
            self.toggle_btn.setText("▶")
            self.toggle_btn.setToolTip("收起面板")
        else:
            self.setFixedWidth(20)
            self.content_widget.setVisible(False)
            self.toggle_btn.setText("◀")
            self.toggle_btn.setToolTip("模型参数设置")
        
        self.expanded_changed.emit(self._expanded)
    
    def is_expanded(self) -> bool:
        return self._expanded
    
    def get_model_options(self) -> dict:
        """获取当前模型参数"""
        return self.params_tab.get_options()
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        
        self.setStyleSheet(f"""
            CollapsiblePanel {{
                background-color: {c['card_bg']};
                border-left: 1px solid {c['border']};
            }}
        """)
        
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['card_bg']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-right: none;
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                font-size: 12px;
                margin-right: 0px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {c['accent']};
            }}
        """)
        
        # 内容区域样式
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-right: none;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }}
        """)


class ModelParamsTab(QWidget):
    """模型参数设置 Tab"""
    
    params_changed = Signal(dict)
    
    # Ollama 支持的参数及其默认值/范围
    OLLAMA_PARAMS = {
        'temperature': {'default': 0.7, 'min': 0.0, 'max': 2.0, 'step': 0.1, 'desc': '控制输出随机性，越高越随机'},
        'top_p': {'default': 0.9, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'desc': '核采样概率阈值'},
        'top_k': {'default': 40, 'min': 1, 'max': 100, 'step': 1, 'desc': '采样候选数量'},
        'repeat_penalty': {'default': 1.1, 'min': 1.0, 'max': 2.0, 'step': 0.05, 'desc': '重复惩罚系数'},
        'num_ctx': {'default': 4096, 'min': 512, 'max': 32768, 'step': 512, 'desc': '上下文长度'},
        'num_predict': {'default': -1, 'min': -1, 'max': 4096, 'step': 64, 'desc': '最大生成长度 (-1=无限)'},
        'seed': {'default': -1, 'min': -1, 'max': 999999, 'step': 1, 'desc': '随机种子 (-1=随机)'},
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme_manager()
        self.param_widgets = {}
        self.setup_ui()
        self.theme.theme_changed.connect(self.apply_theme)
    
    def setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("模型参数")
        title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        layout.addWidget(title)
        
        # 参数控件
        for param_name, param_info in self.OLLAMA_PARAMS.items():
            widget = self._create_param_widget(param_name, param_info)
            layout.addWidget(widget)
            self.param_widgets[param_name] = widget
        
        # 重置按钮
        reset_btn = QPushButton("重置为默认值")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        self.apply_theme()
    
    def _create_param_widget(self, name: str, info: dict) -> QWidget:
        """创建单个参数控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 参数名和值（带边框）
        header_frame = QFrame()
        header_frame.setObjectName("paramHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(5)
        
        label = QLabel(name)
        label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        header_layout.addWidget(label)
        
        header_layout.addStretch()
        
        # 当前值显示
        value_label = QLabel(str(info['default']))
        value_label.setFont(QFont("Microsoft YaHei UI", 10))
        value_label.setAlignment(Qt.AlignRight)
        header_layout.addWidget(value_label)
        
        layout.addWidget(header_frame)
        
        # 描述（无边框）
        desc = QLabel(info['desc'])
        desc.setFont(QFont("Microsoft YaHei UI", 9))
        desc.setWordWrap(True)
        desc.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(desc)
        
        # 滑块或输入框
        if isinstance(info['default'], float):
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(int(info['min'] * 100))
            slider.setMaximum(int(info['max'] * 100))
            slider.setValue(int(info['default'] * 100))
            slider.setSingleStep(int(info['step'] * 100))
            
            def update_float_value(v, lbl=value_label):
                lbl.setText(f"{v / 100:.2f}")
                self.params_changed.emit(self.get_options())
            
            slider.valueChanged.connect(update_float_value)
            layout.addWidget(slider)
            widget.slider = slider
            widget.value_label = value_label
            widget.is_float = True
        else:
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(info['min'])
            slider.setMaximum(info['max'])
            slider.setValue(info['default'])
            slider.setSingleStep(info['step'])
            
            def update_int_value(v, lbl=value_label):
                lbl.setText(str(v))
                self.params_changed.emit(self.get_options())
            
            slider.valueChanged.connect(update_int_value)
            layout.addWidget(slider)
            widget.slider = slider
            widget.value_label = value_label
            widget.is_float = False
        
        widget.param_name = name
        widget.default_value = info['default']
        
        return widget
    
    def get_options(self) -> dict:
        """获取当前所有参数值"""
        options = {}
        for name, widget in self.param_widgets.items():
            if widget.is_float:
                options[name] = widget.slider.value() / 100.0
            else:
                options[name] = widget.slider.value()
        return options
    
    def reset_to_defaults(self):
        """重置所有参数为默认值"""
        for name, widget in self.param_widgets.items():
            default = self.OLLAMA_PARAMS[name]['default']
            if widget.is_float:
                widget.slider.setValue(int(default * 100))
            else:
                widget.slider.setValue(default)
    
    def apply_theme(self, theme=None):
        c = self.theme.colors
        
        self.setStyleSheet(f"""
            QLabel {{
                color: {c['text']};
                background: transparent;
                border: none;
            }}
            QFrame#paramHeader {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
            QFrame {{
                background: transparent;
                border: none;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {c['border']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {c['accent']};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {c['accent_hover']};
            }}
            QSlider::sub-page:horizontal {{
                background: {c['accent']};
                border-radius: 3px;
            }}
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
