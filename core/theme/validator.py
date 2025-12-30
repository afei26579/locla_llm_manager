"""主题验证器

验证主题配置的完整性和正确性
"""

import re
from typing import Dict, Any, List, Tuple


class ThemeValidator:
    """主题验证器"""
    
    # 必需的颜色字段
    REQUIRED_COLOR_FIELDS = [
        'background.primary',
        'background.secondary',
        'surface.card',
        'surface.input',
        'border.default',
        'accent.primary',
        'text.primary',
        'text.secondary',
    ]
    
    # 颜色格式正则
    COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$|^#[0-9A-Fa-f]{8}$|^rgba?\([^)]+\)$|^transparent$')
    
    @classmethod
    def validate(cls, theme_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证主题配置
        
        Args:
            theme_data: 主题数据字典
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证元数据
        if 'meta' not in theme_data:
            errors.append("缺少 'meta' 字段")
        else:
            meta = theme_data['meta']
            if 'name' not in meta:
                errors.append("缺少 'meta.name' 字段")
            if 'display_name' not in meta:
                errors.append("缺少 'meta.display_name' 字段")
        
        # 验证颜色配置
        if 'colors' not in theme_data:
            errors.append("缺少 'colors' 字段")
        else:
            colors = theme_data['colors']
            for field in cls.REQUIRED_COLOR_FIELDS:
                if not cls._get_nested_value(colors, field):
                    errors.append(f"缺少必需的颜色字段: colors.{field}")
            
            # 验证颜色格式
            cls._validate_colors_recursive(colors, 'colors', errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def _get_nested_value(cls, data: Dict, path: str) -> Any:
        """获取嵌套字典的值"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    @classmethod
    def _validate_colors_recursive(cls, data: Any, path: str, errors: List[str]):
        """递归验证颜色格式"""
        if isinstance(data, dict):
            for key, value in data.items():
                cls._validate_colors_recursive(value, f"{path}.{key}", errors)
        elif isinstance(data, str):
            if not cls.COLOR_PATTERN.match(data):
                errors.append(f"无效的颜色格式: {path} = '{data}'")
    
    @classmethod
    def fill_defaults(cls, theme_data: Dict[str, Any], base_theme: Dict[str, Any]) -> Dict[str, Any]:
        """用基础主题填充缺失的字段
        
        Args:
            theme_data: 待填充的主题数据
            base_theme: 基础主题数据
            
        Returns:
            填充后的主题数据
        """
        result = cls._deep_merge(base_theme.copy(), theme_data)
        return result
    
    @classmethod
    def _deep_merge(cls, base: Dict, override: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
