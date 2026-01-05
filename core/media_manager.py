"""媒体文件管理模块"""

import os
import sys
import shutil
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class MediaManager:
    """媒体文件管理器 - 统一管理所有图片资源"""
    
    def __init__(self):
        # 获取基础目录
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 媒体目录结构
        self.media_dir = os.path.join(self.base_dir, 'media')
        self.avatars_dir = os.path.join(self.media_dir, 'avatars')
        self.persona_icons_dir = os.path.join(self.media_dir, 'persona_icons')
        self.backgrounds_dir = os.path.join(self.media_dir, 'backgrounds')
        
        # 确保目录存在
        self._ensure_directories()
        
        # 迁移旧的 avatars 目录
        self._migrate_old_avatars()
    
    def _ensure_directories(self):
        """确保所有媒体目录存在"""
        for directory in [self.media_dir, self.avatars_dir, self.persona_icons_dir, self.backgrounds_dir]:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"媒体目录已创建: {directory}")
    
    def _migrate_old_avatars(self):
        """迁移旧的 avatars 目录到 media/avatars"""
        old_avatars_dir = os.path.join(self.base_dir, 'avatars')
        if os.path.exists(old_avatars_dir) and old_avatars_dir != self.avatars_dir:
            try:
                # 迁移所有文件
                for filename in os.listdir(old_avatars_dir):
                    if filename == '.gitignore':
                        continue
                    old_path = os.path.join(old_avatars_dir, filename)
                    new_path = os.path.join(self.avatars_dir, filename)
                    if os.path.isfile(old_path) and not os.path.exists(new_path):
                        shutil.copy2(old_path, new_path)
                        logger.info(f"迁移头像: {filename}")
            except Exception as e:
                logger.error(f"迁移旧头像失败: {e}")
    
    def save_user_avatar(self, image, filename: str = "user_avatar.png") -> str:
        """
        保存用户头像
        
        Args:
            image: PIL Image 对象或文件路径
            filename: 文件名（默认 user_avatar.png）
        
        Returns:
            相对路径（如 media/avatars/user_avatar.png）
        """
        try:
            target_path = os.path.join(self.avatars_dir, filename)
            
            # 如果是 PIL Image 对象
            if hasattr(image, 'save'):
                image.save(target_path, "PNG")
            # 如果是文件路径
            elif isinstance(image, str) and os.path.exists(image):
                shutil.copy2(image, target_path)
            else:
                raise ValueError("Invalid image input")
            
            # 返回相对路径
            relative_path = os.path.relpath(target_path, self.base_dir)
            logger.info(f"用户头像已保存: {relative_path}")
            return relative_path
        except Exception as e:
            logger.error(f"保存用户头像失败: {e}")
            return ""
    
    def save_persona_icon(self, source, persona_key: str) -> str:
        """
        保存助手图标
        
        Args:
            source: QPixmap 对象或源文件路径
            persona_key: 助手唯一标识
        
        Returns:
            相对路径（如 media/persona_icons/persona_xxx_icon.png）
        """
        try:
            # 生成目标文件名
            filename = f"{persona_key}_icon.png"
            target_path = os.path.join(self.persona_icons_dir, filename)
            
            # 如果是 QPixmap 对象
            if hasattr(source, 'save'):
                source.save(target_path, "PNG")
            # 如果是文件路径
            elif isinstance(source, str) and os.path.exists(source):
                # 获取文件扩展名
                _, ext = os.path.splitext(source)
                if ext.lower() in ['.png', '.jpg', '.jpeg', '.bmp']:
                    filename = f"{persona_key}_icon{ext}"
                    target_path = os.path.join(self.persona_icons_dir, filename)
                # 复制文件
                shutil.copy2(source, target_path)
            else:
                logger.error(f"无效的图标源: {source}")
                return ""
            
            # 返回相对路径
            relative_path = os.path.relpath(target_path, self.base_dir)
            logger.info(f"助手图标已保存: {relative_path}")
            return relative_path
        except Exception as e:
            logger.error(f"保存助手图标失败: {e}")
            return ""
    
    def save_background(self, source_path: str) -> str:
        """
        保存聊天背景图片
        
        Args:
            source_path: 源文件路径
        
        Returns:
            相对路径（如 media/backgrounds/bg_20231225_123456.jpg）
        """
        try:
            if not os.path.exists(source_path):
                return ""
            
            # 获取文件扩展名
            _, ext = os.path.splitext(source_path)
            if not ext:
                ext = '.png'
            
            # 生成唯一文件名（使用时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"bg_{timestamp}{ext}"
            target_path = os.path.join(self.backgrounds_dir, filename)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 返回相对路径
            relative_path = os.path.relpath(target_path, self.base_dir)
            logger.info(f"背景图片已保存: {relative_path}")
            return relative_path
        except Exception as e:
            logger.error(f"保存背景图片失败: {e}")
            return ""
    
    def save_backgrounds(self, source_paths: List[str]) -> List[str]:
        """
        批量保存聊天背景图片
        
        Args:
            source_paths: 源文件路径列表
        
        Returns:
            相对路径列表
        """
        relative_paths = []
        for source_path in source_paths:
            relative_path = self.save_background(source_path)
            if relative_path:
                relative_paths.append(relative_path)
        return relative_paths
    
    def get_absolute_path(self, relative_path: str) -> str:
        """
        将相对路径转换为绝对路径
        
        Args:
            relative_path: 相对路径（如 media/avatars/user_avatar.png）
        
        Returns:
            绝对路径
        """
        if not relative_path:
            return ""
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(relative_path):
            return relative_path
        
        # 拼接为绝对路径
        absolute_path = os.path.join(self.base_dir, relative_path)
        return absolute_path
    
    def delete_file(self, relative_path: str) -> bool:
        """
        删除媒体文件
        
        Args:
            relative_path: 相对路径
        
        Returns:
            是否删除成功
        """
        try:
            absolute_path = self.get_absolute_path(relative_path)
            if os.path.exists(absolute_path):
                os.remove(absolute_path)
                logger.info(f"媒体文件已删除: {relative_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除媒体文件失败: {e}")
            return False
    
    def delete_persona_files(self, persona_key: str) -> bool:
        """
        删除助手相关的所有文件（图标）
        
        Args:
            persona_key: 助手唯一标识
        
        Returns:
            是否删除成功
        """
        try:
            # 删除图标文件
            pattern = f"{persona_key}_icon"
            deleted = False
            for filename in os.listdir(self.persona_icons_dir):
                if filename.startswith(pattern):
                    file_path = os.path.join(self.persona_icons_dir, filename)
                    os.remove(file_path)
                    logger.info(f"已删除助手图标: {filename}")
                    deleted = True
            return deleted
        except Exception as e:
            logger.error(f"删除助手文件失败: {e}")
            return False
    
    def file_exists(self, relative_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            relative_path: 相对路径
        
        Returns:
            文件是否存在
        """
        absolute_path = self.get_absolute_path(relative_path)
        return os.path.exists(absolute_path)


# 全局单例
_media_manager_instance = None

def get_media_manager() -> MediaManager:
    """获取媒体管理器单例"""
    global _media_manager_instance
    if _media_manager_instance is None:
        _media_manager_instance = MediaManager()
    return _media_manager_instance
