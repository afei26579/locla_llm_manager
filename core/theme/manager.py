"""主题管理器

管理主题的加载、切换和保存
"""

import json
import os
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from .loader import ThemeLoader
from .stylesheet import StylesheetGenerator


class ThemeManager(QObject):
    """主题管理器（单例）"""
    
    theme_changed = Signal(dict)  # 主题变更信号
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        super().__init__()
        self._initialized = True
        
        self.loader = ThemeLoader()
        self.stylesheet_generator = StylesheetGenerator()
        
        self._current_theme = None
        self._themes = {}  # 已注册的主题
        
        # 加载内置主题
        self._load_builtin_themes()
        
        # 从配置加载当前主题
        self._load_current_theme_from_config()
    
    def _load_builtin_themes(self):
        """加载内置主题"""
        builtin_themes = ['dark', 'light']
        for theme_name in builtin_themes:
            theme_data = self.loader.load(theme_name)
            if theme_data:
                self._themes[theme_name] = theme_data
    
    def _load_current_theme_from_config(self):
        """从配置文件加载当前主题"""
        config_path = self._get_config_path()
        theme_name = 'dark'  # 默认主题
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    theme_name = config.get('theme', 'dark')
            except:
                pass
        
        # 设置当前主题
        if theme_name in self._themes:
            self._current_theme = self._themes[theme_name]
        else:
            # 如果配置的主题不存在，使用默认主题
            self._current_theme = self._themes.get('dark')
    
    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        import sys
        if getattr(sys, 'frozen', False):
            # 配置文件应该在 exe 同级目录，不在 _MEIPASS
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, 'config.json')
    
    def _save_config(self):
        """保存配置（只更新 theme 字段）"""
        config_path = self._get_config_path()
        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except:
                    pass
            
            # 更新 theme 字段
            existing_config['theme'] = self._current_theme['meta']['name']
            
            # 写回文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存主题配置失败: {e}")
    
    @property
    def current(self) -> Dict[str, Any]:
        """获取当前主题完整数据（兼容旧代码）"""
        if not self._current_theme:
            return {}
        
        # 返回兼容旧代码的扁平结构
        meta = self._current_theme.get('meta', {})
        colors = self._current_theme.get('colors', {})
        
        # 创建兼容的主题字典
        compat_theme = {
            'name': meta.get('name', 'dark'),
            'display_name': meta.get('display_name', '深色'),
        }
        
        # 添加扁平化的颜色
        compat_theme.update(self._flatten_colors(colors))
        
        return compat_theme
    
    @property
    def colors(self) -> Dict[str, Any]:
        """获取当前主题颜色配置（兼容旧代码）"""
        if not self._current_theme:
            return {}
        
        # 扁平化颜色配置，兼容旧的访问方式
        colors = self._current_theme.get('colors', {})
        flat_colors = self._flatten_colors(colors)
        return flat_colors
    
    def _flatten_colors(self, colors: Dict[str, Any], prefix: str = '') -> Dict[str, str]:
        """扁平化颜色配置
        
        将嵌套的颜色配置转换为扁平结构，例如：
        {'background': {'primary': '#000'}} -> {'bg': '#000'}
        """
        flat = {}
        
        # 映射规则（新键名 -> 旧键名）
        mapping = {
            'background.primary': 'bg',
            'background.secondary': 'bg_secondary',
            'background.tertiary': 'bg_tertiary',
            'surface.card': 'card_bg',
            'surface.input': 'input_bg',
            'surface.hover': 'hover',
            'surface.active': 'active',
            'border.default': 'border',
            'border.focus': 'border_focus',
            'accent.primary': 'accent',
            'accent.hover': 'accent_hover',
            'accent.light': 'accent_light',
            'text.primary': 'text',
            'text.secondary': 'text_secondary',
            'text.dim': 'text_dim',
            'semantic.success': 'success',
            'semantic.warning': 'warning',
            'semantic.error': 'error',
            'semantic.info': 'info',
            'chat.user_bubble': 'user_bubble',
            'chat.ai_bubble': 'ai_bubble',
            'scrollbar.track': 'scrollbar_track',
            'scrollbar.thumb': 'scrollbar',
            'scrollbar.thumb_hover': 'scrollbar_hover',
            'sidebar.background': 'sidebar_bg',
            'notification.background': 'notification_bg',
            'settings.nav_bg': 'settings_nav_bg',
            'settings.nav_active': 'settings_nav_active',
            'progress.background': 'progress_bg',
            'progress.fill': 'progress_fill',
            'info_row.background': 'info_row_bg',
        }
        
        def get_nested(d: Dict, path: str) -> Optional[str]:
            """获取嵌套字典的值"""
            keys = path.split('.')
            value = d
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        
        # 应用映射
        for new_key, old_key in mapping.items():
            value = get_nested(colors, new_key)
            if value:
                flat[old_key] = value
        
        # 添加一些额外的兼容字段
        if 'sidebar' in colors and 'background' in colors['sidebar']:
            flat['sidebar_bg'] = colors['sidebar']['background']
        if 'notification' in colors and 'background' in colors['notification']:
            flat['notification_bg'] = colors['notification']['background']
        if 'settings' in colors:
            if 'nav_bg' in colors['settings']:
                flat['settings_nav_bg'] = colors['settings']['nav_bg']
            if 'nav_active' in colors['settings']:
                flat['settings_nav_active'] = colors['settings']['nav_active']
        if 'progress' in colors:
            if 'background' in colors['progress']:
                flat['progress_bg'] = colors['progress']['background']
            if 'fill' in colors['progress']:
                flat['progress_fill'] = colors['progress']['fill']
        if 'info_row' in colors and 'background' in colors['info_row']:
            flat['info_row_bg'] = colors['info_row']['background']
        
        return flat
    
    def set_theme(self, theme_name: str) -> bool:
        """设置主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            是否设置成功
        """
        from core.logger import get_logger
        logger = get_logger('theme')
        
        logger.info(f"set_theme 被调用，主题名称: {theme_name}")
        
        # 如果主题已注册，直接使用
        if theme_name in self._themes:
            self._current_theme = self._themes[theme_name]
            self._save_config()
            logger.info(f"发射 theme_changed 信号，主题: {theme_name}")
            self.theme_changed.emit(self._current_theme)
            logger.info("theme_changed 信号已发射")
            return True
        
        # 尝试加载主题
        theme_data = self.loader.load(theme_name)
        if theme_data:
            self._themes[theme_name] = theme_data
            self._current_theme = theme_data
            self._save_config()
            logger.info(f"发射 theme_changed 信号，主题: {theme_name}")
            self.theme_changed.emit(self._current_theme)
            logger.info("theme_changed 信号已发射")
            return True
        
        logger.warning(f"主题 {theme_name} 不存在")
        return False
    
    def register_theme(self, theme_data: Dict[str, Any]) -> bool:
        """注册自定义主题
        
        Args:
            theme_data: 主题数据
            
        Returns:
            是否注册成功
        """
        if 'meta' not in theme_data or 'name' not in theme_data['meta']:
            print("主题数据缺少 meta.name 字段")
            return False
        
        theme_name = theme_data['meta']['name']
        self._themes[theme_name] = theme_data
        return True
    
    def get_stylesheet(self) -> str:
        """获取当前主题的样式表
        
        Returns:
            Qt 样式表字符串
        """
        if not self._current_theme:
            return ""
        
        return self.stylesheet_generator.generate(self._current_theme)
    
    def get_available_themes(self) -> list:
        """获取可用主题列表
        
        Returns:
            [(theme_name, display_name), ...]
        """
        themes = []
        for name, data in self._themes.items():
            display_name = data.get('meta', {}).get('display_name', name)
            themes.append((name, display_name))
        return themes
    
    def reload_themes(self):
        """重新加载所有主题"""
        self.loader.clear_cache()
        self.stylesheet_generator.clear_cache()
        self._themes.clear()
        self._load_builtin_themes()
        self._load_current_theme_from_config()
    
    def toggle_theme(self):
        """切换主题（深色/浅色）"""
        current_name = self._current_theme.get('meta', {}).get('name', 'dark')
        if current_name == 'dark':
            self.set_theme('light')
        else:
            self.set_theme('dark')


def get_theme_manager() -> ThemeManager:
    """获取主题管理器实例（单例）"""
    return ThemeManager()
