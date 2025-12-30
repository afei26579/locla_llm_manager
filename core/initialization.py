"""应用初始化模块

负责首次启动时的资源初始化：
1. 创建必要的目录结构
2. 从 JSON 文件导入数据到数据库（如果存在）
3. media/ 目录由用户手动放置资源（类似 runtime/ollama/）
"""

import os
import sys
import json
from typing import Tuple

from .database import get_database
from .logger import get_logger

logger = get_logger('initialization')


class AppInitializer:
    """应用初始化器"""
    
    def __init__(self):
        # 确定基础目录（exe 所在目录）
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
            # 打包后的数据文件在 _MEIPASS 临时目录
            self.data_dir = getattr(sys, '_MEIPASS', self.base_dir)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = self.base_dir
        
        self.db = get_database()
        
        # 配置文件路径（从 _MEIPASS 读取）
        self.models_json = os.path.join(self.data_dir, 'models.json')
        self.personas_json = os.path.join(self.data_dir, 'personas.json')
        
        # 用户数据路径（exe 同级目录）
        self.media_dir = os.path.join(self.base_dir, 'media')
        self.models_dir = os.path.join(self.base_dir, 'models')
        self.ollama_models_dir = os.path.join(self.base_dir, 'ollama_models')
        
        # 初始化标记文件（exe 同级目录）
        self.init_flag_file = os.path.join(self.base_dir, '.initialized')
    
    def is_first_run(self) -> bool:
        """检查是否首次运行"""
        return not os.path.exists(self.init_flag_file)
    
    def initialize_all(self) -> Tuple[bool, str]:
        """执行完整初始化"""
        try:
            logger.info("开始应用初始化...")
            
            # 1. 创建目录结构
            self.create_directories()
            logger.info("✓ 目录结构创建完成")
            
            # 2. 导入模型配置（如果 models.json 存在）
            model_count = self.import_models()
            if model_count > 0:
                logger.info(f"✓ 导入模型配置: {model_count} 个")
            else:
                logger.info("⚠ 未找到 models.json，跳过模型导入")
            
            # 3. 导入人格配置（如果 personas.json 存在）
            persona_count = self.import_personas()
            if persona_count > 0:
                logger.info(f"✓ 导入人格配置: {persona_count} 个")
            else:
                logger.info("✓ 使用默认人格配置")
            
            # 4. 检测 media 目录资源
            media_exists = os.path.exists(self.media_dir) and os.listdir(self.media_dir)
            if media_exists:
                logger.info("✓ 检测到 media/ 目录资源")
            else:
                logger.info("⚠ media/ 目录为空，可手动添加背景图片等资源")
            
            # 5. 创建初始化标记
            self.mark_initialized()
            
            summary = (
                f"初始化完成！\n"
                f"• 模型配置: {model_count} 个\n"
                f"• 人格配置: {persona_count} 个\n"
                f"• 资源目录: {'已就绪' if media_exists else '可选'}"
            )
            
            logger.info(summary)
            return True, summary
        
        except Exception as e:
            error_msg = f"初始化失败: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def create_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.media_dir,
            os.path.join(self.media_dir, 'backgrounds'),
            os.path.join(self.media_dir, 'avatars'),
            os.path.join(self.media_dir, 'persona_icons'),
            self.models_dir,
            self.ollama_models_dir,
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"创建目录: {directory}")
    
    def import_models(self) -> int:
        """从 models.json 导入模型配置到数据库"""
        logger.debug(f"查找 models.json: {self.models_json}")
        logger.debug(f"文件存在: {os.path.exists(self.models_json)}")
        
        if not os.path.exists(self.models_json):
            logger.warning(f"模型配置文件不存在: {self.models_json}")
            logger.debug(f"当前目录: {os.getcwd()}")
            logger.debug(f"base_dir: {self.base_dir}")
            logger.debug(f"data_dir: {self.data_dir}")
            if hasattr(sys, '_MEIPASS'):
                logger.debug(f"_MEIPASS: {sys._MEIPASS}")
                try:
                    meipass_files = os.listdir(sys._MEIPASS)
                    logger.debug(f"_MEIPASS 内容: {meipass_files[:20]}")  # 只显示前20个
                except Exception as e:
                    logger.debug(f"无法列出 _MEIPASS 内容: {e}")
            return 0
        
        try:
            with open(self.models_json, 'r', encoding='utf-8') as f:
                models_list = json.load(f)
            
            logger.info(f"成功读取 models.json，模型数: {len(models_list)}")
            
            count = 0
            for model in models_list:
                # 处理 JSON 字符串字段
                lang = model.get('lang', '[]')
                if isinstance(lang, str):
                    lang = json.loads(lang)
                
                quantizations = model.get('quantizations', '[]')
                if isinstance(quantizations, str):
                    quantizations = json.loads(quantizations)
                
                self.db.add_model(
                    model_id=model['id'],
                    category=model.get('category', 'text'),
                    subcategory=model.get('subcategory', 'general'),
                    name=model['name'],
                    params=model.get('params', ''),
                    params_b=model.get('params_b', 0),
                    ctx=model.get('ctx', 4096),
                    lang=lang,
                    distilled=bool(model.get('distilled', False)),
                    quantizations=quantizations,
                    file_pattern=model.get('file_pattern', '')
                )
                count += 1
            
            logger.info(f"成功导入 {count} 个模型配置")
            return count
        
        except Exception as e:
            logger.error(f"导入模型配置失败: {e}", exc_info=True)
            return 0
    
    def import_personas(self) -> int:
        """从 personas.json 导入人格配置到数据库"""
        logger.debug(f"查找 personas.json: {self.personas_json}")
        
        if not os.path.exists(self.personas_json):
            logger.warning(f"人格配置文件不存在: {self.personas_json}")
            # 创建默认人格
            return self._create_default_personas()
        
        try:
            with open(self.personas_json, 'r', encoding='utf-8') as f:
                personas_list = json.load(f)
            
            logger.info(f"成功读取 personas.json，人格数: {len(personas_list)}")
            
            count = 0
            for persona in personas_list:
                # 处理 JSON 字符串字段
                background_images = persona.get('background_images', '')
                if isinstance(background_images, str) and background_images.startswith('['):
                    try:
                        background_images = json.loads(background_images)
                        background_images = ','.join(background_images)  # 转换为逗号分隔的字符串
                    except Exception as e:
                        logger.warning(f"解析 background_images 失败: {e}")
                
                self.db.add_persona(
                    key=persona['key'],
                    name=persona['name'],
                    icon=persona.get('icon', '🤖'),
                    icon_path=persona.get('icon_path', ''),
                    description=persona.get('description', ''),
                    system_prompt=persona.get('system_prompt', ''),
                    persona_type=persona.get('type', 'assistant'),
                    background_images=background_images
                )
                count += 1
            
            logger.info(f"成功导入 {count} 个人格配置")
            return count
        
        except Exception as e:
            logger.error(f"导入人格配置失败: {e}", exc_info=True)
            return self._create_default_personas()
    
    def _create_default_personas(self) -> int:
        """创建默认人格"""
        default_personas = [
            {
                'key': 'default',
                'name': '默认助手',
                'icon': '🤖',
                'description': '通用 AI 助手，可以回答各种问题',
                'system_prompt': '',
                'type': 'assistant'
            },
            {
                'key': 'coder',
                'name': '编程助手',
                'icon': '💻',
                'description': '专业的编程助手，擅长代码编写和调试',
                'system_prompt': '你是一个专业的编程助手，擅长多种编程语言和框架。请用清晰、准确的方式回答编程相关问题。',
                'type': 'assistant'
            },
            {
                'key': 'translator',
                'name': '翻译助手',
                'icon': '🌐',
                'description': '专业的翻译助手，支持多语言互译',
                'system_prompt': '你是一个专业的翻译助手，能够准确地在中英文之间进行翻译。请保持原文的语气和风格。',
                'type': 'assistant'
            }
        ]
        
        count = 0
        for persona in default_personas:
            self.db.add_persona(
                key=persona['key'],
                name=persona['name'],
                icon=persona['icon'],
                description=persona['description'],
                system_prompt=persona['system_prompt'],
                persona_type=persona['type']
            )
            count += 1
        
        logger.info(f"创建了 {count} 个默认人格")
        return count
    
    def mark_initialized(self):
        """创建初始化标记文件"""
        from datetime import datetime
        
        with open(self.init_flag_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                'initialized_at': datetime.now().isoformat(),
                'version': '1.0'
            }, indent=2))
        
        logger.info(f"创建初始化标记: {self.init_flag_file}")
    
    def reset_initialization(self):
        """重置初始化状态（用于测试）"""
        if os.path.exists(self.init_flag_file):
            os.remove(self.init_flag_file)
            logger.info("已重置初始化状态")


def auto_initialize_on_startup():
    """启动时自动初始化（如果需要）"""
    initializer = AppInitializer()
    
    if initializer.is_first_run():
        logger.info("检测到首次运行，开始初始化...")
        success, message = initializer.initialize_all()
        
        if success:
            logger.info("✓ 初始化成功")
        else:
            logger.error(f"✗ 初始化失败: {message}")
        
        return success, message
    else:
        logger.info("应用已初始化，跳过初始化步骤")
        return True, "已初始化"


if __name__ == '__main__':
    # 测试初始化
    from .logger import setup_logger
    setup_logger('initialization', level=logging.DEBUG)
    auto_initialize_on_startup()
