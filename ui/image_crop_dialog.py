"""图片裁剪对话框"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPixmap, QPen, QColor, QBrush, QPainter, QTransform

from .themes import get_theme_manager


class ImageCropDialog(QDialog):
    """图片裁剪对话框 - 固定裁剪框，缩放图片"""
    
    def __init__(self, image_path: str, parent=None, title: str = "裁剪头像"):
        super().__init__(parent)
        self.image_path = image_path
        self.theme = get_theme_manager()
        self.cropped_image = None
        self.dialog_title = title
        
        # 固定裁剪框尺寸
        self.crop_size = 500  # 裁剪框固定为 500x500
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(900, 850)
        
        self.setup_ui()
        self.load_image()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel(f"调整{self.dialog_title.replace('裁剪', '')}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("拖动图片调整位置，使用滑块缩放图片大小，方框内的区域将被裁剪")
        desc.setStyleSheet("color: #888;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 图片查看器
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.NoDrag)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setFixedSize(700, 600)
        
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        
        # 居中显示
        view_container = QHBoxLayout()
        view_container.addStretch()
        view_container.addWidget(self.view)
        view_container.addStretch()
        layout.addLayout(view_container)
        
        # 缩放控制
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(10)
        
        zoom_label = QLabel("缩放图片:")
        zoom_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(50)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider, 1)
        
        self.zoom_value_label = QLabel("100%")
        self.zoom_value_label.setFixedWidth(50)
        zoom_layout.addWidget(self.zoom_value_label)
        
        layout.addLayout(zoom_layout)
        
        # 提示信息
        hint = QLabel(f"裁剪框尺寸: {self.crop_size} x {self.crop_size} (固定)")
        hint.setStyleSheet("color: #666; font-size: 12px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setFixedSize(100, 36)
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_image)
        btn_layout.addWidget(self.reset_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(100, 36)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setFixedSize(100, 36)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept_crop)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def load_image(self):
        """加载图片"""
        self.original_pixmap = QPixmap(self.image_path)
        if self.original_pixmap.isNull():
            return
        
        # 添加图片到场景（可拖动）
        self.pixmap_item = QGraphicsPixmapItem(self.original_pixmap)
        self.pixmap_item.setFlag(QGraphicsPixmapItem.ItemIsMovable)
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.addItem(self.pixmap_item)
        
        # 设置场景大小为视图大小
        self.scene.setSceneRect(0, 0, 700, 600)
        
        # 创建固定的裁剪框（居中显示）
        crop_x = (700 - self.crop_size) / 2
        crop_y = (600 - self.crop_size) / 2
        
        self.crop_rect = QGraphicsRectItem(crop_x, crop_y, self.crop_size, self.crop_size)
        pen = QPen(QColor("#007AFF"), 3, Qt.SolidLine)
        self.crop_rect.setPen(pen)
        self.crop_rect.setBrush(QBrush(Qt.transparent))
        self.crop_rect.setZValue(100)  # 确保在最上层
        self.scene.addItem(self.crop_rect)
        
        # 添加半透明遮罩（裁剪框外的区域）
        self.create_mask()
        
        # 初始化图片位置（居中）
        self.center_image()
    
    def create_mask(self):
        """创建裁剪框外的半透明遮罩"""
        # 上方遮罩
        crop_rect = self.crop_rect.rect()
        top_mask = QGraphicsRectItem(0, 0, 700, crop_rect.top())
        top_mask.setBrush(QBrush(QColor(0, 0, 0, 120)))
        top_mask.setPen(QPen(Qt.transparent))
        top_mask.setZValue(99)
        self.scene.addItem(top_mask)
        
        # 下方遮罩
        bottom_mask = QGraphicsRectItem(0, crop_rect.bottom(), 700, 600 - crop_rect.bottom())
        bottom_mask.setBrush(QBrush(QColor(0, 0, 0, 120)))
        bottom_mask.setPen(QPen(Qt.transparent))
        bottom_mask.setZValue(99)
        self.scene.addItem(bottom_mask)
        
        # 左侧遮罩
        left_mask = QGraphicsRectItem(0, crop_rect.top(), crop_rect.left(), self.crop_size)
        left_mask.setBrush(QBrush(QColor(0, 0, 0, 120)))
        left_mask.setPen(QPen(Qt.transparent))
        left_mask.setZValue(99)
        self.scene.addItem(left_mask)
        
        # 右侧遮罩
        right_mask = QGraphicsRectItem(crop_rect.right(), crop_rect.top(), 700 - crop_rect.right(), self.crop_size)
        right_mask.setBrush(QBrush(QColor(0, 0, 0, 120)))
        right_mask.setPen(QPen(Qt.transparent))
        right_mask.setZValue(99)
        self.scene.addItem(right_mask)
    
    def center_image(self):
        """将图片居中到裁剪框"""
        if not hasattr(self, 'pixmap_item'):
            return
        
        # 获取当前缩放后的图片尺寸
        transform = self.pixmap_item.transform()
        scaled_width = self.original_pixmap.width() * transform.m11()
        scaled_height = self.original_pixmap.height() * transform.m22()
        
        # 计算居中位置
        crop_rect = self.crop_rect.rect()
        center_x = crop_rect.center().x()
        center_y = crop_rect.center().y()
        
        # 设置图片位置（使图片中心对齐裁剪框中心）
        self.pixmap_item.setPos(
            center_x - scaled_width / 2,
            center_y - scaled_height / 2
        )
    
    def on_zoom_changed(self, value):
        """缩放变化"""
        if not hasattr(self, 'pixmap_item'):
            return
        
        scale = value / 100.0
        
        # 获取当前图片中心点（场景坐标）
        current_rect = self.pixmap_item.sceneBoundingRect()
        center_x = current_rect.center().x()
        center_y = current_rect.center().y()
        
        # 重置变换并应用新的缩放
        self.pixmap_item.setTransform(QTransform())
        self.pixmap_item.setScale(scale)
        
        # 重新计算位置，保持中心点不变
        new_rect = self.pixmap_item.sceneBoundingRect()
        offset_x = center_x - new_rect.center().x()
        offset_y = center_y - new_rect.center().y()
        
        self.pixmap_item.moveBy(offset_x, offset_y)
        
        # 更新标签
        self.zoom_value_label.setText(f"{value}%")
    
    def reset_image(self):
        """重置图片位置和缩放"""
        if not hasattr(self, 'pixmap_item'):
            return
        
        # 重置缩放
        self.zoom_slider.setValue(100)
        self.pixmap_item.setTransform(QTransform())
        self.pixmap_item.setScale(1.0)
        
        # 居中图片
        self.center_image()
    
    def accept_crop(self):
        """确认裁剪"""
        if not hasattr(self, 'pixmap_item'):
            self.reject()
            return
        
        # 获取裁剪框在场景中的位置
        crop_rect = self.crop_rect.rect()
        
        # 创建一个新的 QPixmap 用于渲染裁剪区域
        result_pixmap = QPixmap(int(self.crop_size), int(self.crop_size))
        result_pixmap.fill(Qt.transparent)
        
        # 创建 QPainter 在结果 pixmap 上绘制
        painter = QPainter(result_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 渲染场景中裁剪框区域的内容
        self.scene.render(
            painter,
            QRectF(0, 0, self.crop_size, self.crop_size),
            crop_rect
        )
        painter.end()
        
        # 缩放到标准头像尺寸（200x200）
        self.cropped_image = result_pixmap.scaled(
            200, 200,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.accept()
    
    def get_cropped_image(self):
        """获取裁剪后的图片"""
        return self.cropped_image
    
    def apply_theme(self):
        """应用主题"""
        c = self.theme.colors
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
                color: {c['text']};
            }}
            QLabel {{
                color: {c['text']};
            }}
            QGraphicsView {{
                background-color: {c['bg_secondary']};
                border: 2px solid {c['border']};
                border-radius: 8px;
            }}
        """)
        
        self.ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text']};
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        
        self.zoom_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {c['bg_tertiary']};
                height: 6px;
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
        """)
