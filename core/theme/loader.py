"""主题加载器

从 JSON 文件加载主题配置
"""

import json
import os
from typing import Dict, Any, Optional
from .validator import ThemeValidator


class ThemeLoader:
    """主题加载器"""
    
    def __init__(self, themes_dir: str = None):
        """初始化加载器
        
        Args:
            themes_dir: 主题目录路径，默认为项目根目录下的 themes/
        """
        if themes_dir is None:
            import sys
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包后，数据文件在 _MEIPASS 临时目录
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            themes_dir = os.path.join(base_dir, 'themes')
        
        self.themes_dir = themes_dir
        self.validator = ThemeValidator()
        self._cache = {}
    
    def load(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """加载主题
        
        Args:
            theme_name: 主题名称（不含 .json 后缀）
            
        Returns:
            主题数据字典，加载失败返回 None
        """
        # 检查缓存
        if theme_name in self._cache:
            return self._cache[theme_name]
        
        # 尝试从标准主题目录加载
        theme_path = os.path.join(self.themes_dir, f"{theme_name}.json")
        if not os.path.exists(theme_path):
            # 尝试从自定义主题目录加载
            theme_path = os.path.join(self.themes_dir, 'custom', f"{theme_name}.json")
        
        if not os.path.exists(theme_path):
            print(f"主题文件不存在: {theme_path}")
            return None
        
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            # 处理主题继承
            if 'meta' in theme_data and theme_data['meta'].get('base'):
                base_name = theme_data['meta']['base']
                base_theme = self.load(base_name)
                if base_theme:
                    theme_data = self.validator.fill_defaults(theme_data, base_theme)
            
            # 验证主题
            valid, errors = self.validator.validate(theme_data)
            if not valid:
                print(f"主题验证失败: {theme_name}")
                for error in errors:
                    print(f"  - {error}")
                return None
            
            # 缓存主题
            self._cache[theme_name] = theme_data
            return theme_data
            
        except json.JSONDecodeError as e:
            print(f"主题 JSON 解析失败: {theme_name}, 错误: {e}")
            return None
        except Exception as e:
            print(f"加载主题失败: {theme_name}, 错误: {e}")
            return None
    
    def load_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """从指定文件加载主题
        
        Args:
            file_path: 主题文件完整路径
            
        Returns:
            主题数据字典，加载失败返回 None
        """
        if not os.path.exists(file_path):
            print(f"主题文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            # 验证主题
            valid, errors = self.validator.validate(theme_data)
            if not valid:
                print(f"主题验证失败: {file_path}")
                for error in errors:
                    print(f"  - {error}")
                return None
            
            return theme_data
            
        except Exception as e:
            print(f"加载主题失败: {file_path}, 错误: {e}")
            return None
    
    def list_themes(self) -> list:
        """列出所有可用主题
        
        Returns:
            主题名称列表
        """
        themes = []
        
        # 扫描标准主题目录
        if os.path.exists(self.themes_dir):
            for file in os.listdir(self.themes_dir):
                if file.endswith('.json'):
                    themes.append(file[:-5])
        
        # 扫描自定义主题目录
        custom_dir = os.path.join(self.themes_dir, 'custom')
        if os.path.exists(custom_dir):
            for file in os.listdir(custom_dir):
                if file.endswith('.json'):
                    theme_name = f"custom/{file[:-5]}"
                    themes.append(theme_name)
        
        return themes
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
