"""数据库管理模块"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from .logger import get_logger

logger = get_logger('database')


class Database:
    """SQLite 数据库管理器"""
    
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.db_path = os.path.join(self.base_dir, 'data.db')
        self.conn = None
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（线程安全）"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # 返回字典格式
        return self.conn
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 对话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                persona TEXT DEFAULT 'default',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                model TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')
        
        # 下载记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_records (
                record_key TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                ollama_name TEXT NOT NULL,
                gguf_path TEXT NOT NULL,
                quantization TEXT,
                model_id TEXT,
                download_time TEXT NOT NULL,
                file_exists INTEGER DEFAULT 1
            )
        ''')
        
        # 人格配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personas (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '🤖',
                icon_path TEXT,
                description TEXT,
                system_prompt TEXT
            )
        ''')
        
        # 模型配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                name TEXT NOT NULL,
                params TEXT NOT NULL,
                params_b REAL NOT NULL,
                ctx INTEGER NOT NULL,
                lang TEXT NOT NULL,
                distilled INTEGER DEFAULT 0,
                quantizations TEXT NOT NULL,
                file_pattern TEXT NOT NULL
            )
        ''')
        
        # 个人设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_updated 
            ON conversations(updated_at DESC)
        ''')
        
        conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")
        
        # 执行数据库迁移
        self._migrate_add_persona_type()
        self._migrate_add_roleplay_fields()
    
    def _migrate_add_persona_type(self):
        """数据库迁移：为 personas 表添加 type 字段"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查 type 列是否存在
            cursor.execute("PRAGMA table_info(personas)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'type' not in columns:
                logger.info("开始迁移：添加 personas.type 字段")
                
                # 添加 type 列，默认值为 'assistant'
                cursor.execute('''
                    ALTER TABLE personas 
                    ADD COLUMN type TEXT DEFAULT 'assistant'
                ''')
                conn.commit()
                logger.info("✅ 已添加 personas.type 字段")
                
                # 智能分类现有数据
                cursor.execute('''
                    UPDATE personas 
                    SET type = 'roleplay'
                    WHERE icon IN ('🐱', '👸', '🧙', '🦸', '🎭', '🐶', '🦊', '🐰', '🐻', '🦄', '🧝', '👨‍🎤', '👩‍🎤', '🤴', '👑', '⚔️')
                       OR name LIKE '%猫娘%'
                       OR name LIKE '%总裁%'
                       OR name LIKE '%御姐%'
                       OR name LIKE '%公主%'
                       OR name LIKE '%王子%'
                ''')
                conn.commit()
                logger.info("✅ 已自动分类现有 personas")
            
            # 检查 background_images 列是否存在
            cursor.execute("PRAGMA table_info(personas)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'background_images' not in columns:
                logger.info("开始迁移：添加 personas.background_images 字段")
                cursor.execute('''
                    ALTER TABLE personas 
                    ADD COLUMN background_images TEXT DEFAULT ''
                ''')
                conn.commit()
                logger.info("✅ 已添加 personas.background_images 字段")
                
        except Exception as e:
            logger.error(f"迁移 personas 字段失败: {e}")
    
    def _migrate_add_roleplay_fields(self):
        """数据库迁移：为 personas 表添加角色对话相关字段"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查字段是否存在
            cursor.execute("PRAGMA table_info(personas)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # 添加 scene_designs 字段（场景设计，JSON 数组）
            if 'scene_designs' not in columns:
                logger.info("开始迁移：添加 personas.scene_designs 字段")
                cursor.execute('''
                    ALTER TABLE personas 
                    ADD COLUMN scene_designs TEXT DEFAULT '[]'
                ''')
                conn.commit()
                logger.info("✅ 已添加 personas.scene_designs 字段")
                
                # 迁移旧数据：将 greeting 和 scenarios 合并为 scene_designs
                if 'greeting' in columns or 'scenarios' in columns:
                    logger.info("开始迁移旧数据到 scene_designs")
                    cursor.execute("SELECT key, greeting, scenarios FROM personas")
                    rows = cursor.fetchall()
                    for row in rows:
                        key = row[0]
                        greeting = row[1] or ''
                        scenarios_str = row[2] or '[]'
                        try:
                            scenarios = json.loads(scenarios_str) if scenarios_str else []
                        except:
                            scenarios = []
                        
                        if greeting or scenarios:
                            scene_designs = [{'scene': greeting, 'suggestions': scenarios[:3]}]
                            cursor.execute(
                                "UPDATE personas SET scene_designs = ? WHERE key = ?",
                                (json.dumps(scene_designs), key)
                            )
                    conn.commit()
                    logger.info("✅ 已迁移旧数据到 scene_designs")
            
            # 添加 enable_suggestions 字段（是否启用推荐回复）
            if 'enable_suggestions' not in columns:
                logger.info("开始迁移：添加 personas.enable_suggestions 字段")
                cursor.execute('''
                    ALTER TABLE personas 
                    ADD COLUMN enable_suggestions INTEGER DEFAULT 1
                ''')
                conn.commit()
                logger.info("✅ 已添加 personas.enable_suggestions 字段")
            
            # 添加 gender 字段（性别）
            if 'gender' not in columns:
                logger.info("开始迁移：添加 personas.gender 字段")
                cursor.execute('''
                    ALTER TABLE personas 
                    ADD COLUMN gender TEXT DEFAULT ''
                ''')
                conn.commit()
                logger.info("✅ 已添加 personas.gender 字段")
            
            # 添加 user_identity 字段（用户身份设计）
            if 'user_identity' not in columns:
                logger.info("开始迁移：添加 personas.user_identity 字段")
                cursor.execute('''
                    ALTER TABLE personas 
                    ADD COLUMN user_identity TEXT DEFAULT ''
                ''')
                conn.commit()
                logger.info("✅ 已添加 personas.user_identity 字段")
                
        except Exception as e:
            logger.error(f"迁移角色对话字段失败: {e}")
    
    # ==================== 对话管理 ====================
    
    def create_conversation(self, conv_id: str, title: str = "", persona: str = "default") -> bool:
        """创建新对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO conversations (id, title, persona, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (conv_id, title, persona, now, now))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            return False
    
    def update_conversation(self, conv_id: str, title: str = None, persona: str = None) -> bool:
        """更新对话信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            if title is not None:
                cursor.execute('''
                    UPDATE conversations 
                    SET title = ?, updated_at = ?
                    WHERE id = ?
                ''', (title, now, conv_id))
            
            if persona is not None:
                cursor.execute('''
                    UPDATE conversations 
                    SET persona = ?, updated_at = ?
                    WHERE id = ?
                ''', (persona, now, conv_id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新对话失败: {e}")
            return False
    
    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """获取对话信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM conversations WHERE id = ?
            ''', (conv_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取对话失败: {e}")
            return None
    
    def list_conversations(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出所有对话（按更新时间倒序）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.*, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"列出对话失败: {e}")
            return []
    
    def delete_conversation(self, conv_id: str) -> bool:
        """删除对话（级联删除消息）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            return False
    
    # ==================== 消息管理 ====================
    
    def add_message(self, conv_id: str, model: str, role: str, 
                   content: str, timestamp: str = None, completed_at: str = None) -> Optional[int]:
        """添加消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO messages (conversation_id, model, role, content, timestamp, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conv_id, model, role, content, timestamp, completed_at))
            
            conn.commit()
            
            # 更新对话的 updated_at
            cursor.execute('''
                UPDATE conversations SET updated_at = ? WHERE id = ?
            ''', (timestamp, conv_id))
            conn.commit()
            
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return None
    
    def get_messages(self, conv_id: str, limit: int = None) -> List[Dict]:
        """获取对话的所有消息（按时间排序）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if limit:
                cursor.execute('''
                    SELECT * FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (conv_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY timestamp ASC
                ''', (conv_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    def get_messages_by_model(self, conv_id: str, model: str) -> List[Dict]:
        """获取指定模型的消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM messages 
                WHERE conversation_id = ? AND model = ?
                ORDER BY timestamp ASC
            ''', (conv_id, model))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取模型消息失败: {e}")
            return []
    
    def search_messages(self, keyword: str, limit: int = 50) -> List[Dict]:
        """搜索消息内容"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT m.*, c.title as conversation_title
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE m.content LIKE ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (f'%{keyword}%', limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"搜索消息失败: {e}")
            return []
    
    # ==================== 下载记录管理 ====================
    
    def add_download_record(self, record_key: str, model_name: str, ollama_name: str,
                           gguf_path: str, quantization: str = '', model_id: str = '') -> bool:
        """添加下载记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            file_exists = 1 if os.path.exists(gguf_path) else 0
            
            cursor.execute('''
                INSERT OR REPLACE INTO download_records 
                (record_key, model_name, ollama_name, gguf_path, quantization, model_id, download_time, file_exists)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (record_key, model_name, ollama_name, gguf_path, quantization, model_id, now, file_exists))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加下载记录失败: {e}")
            return False
    
    def get_download_record(self, record_key: str) -> Optional[Dict]:
        """获取下载记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM download_records WHERE record_key = ?
            ''', (record_key,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取下载记录失败: {e}")
            return None
    
    def find_download_record(self, name: str) -> Optional[Dict]:
        """模糊查找下载记录（支持多种匹配方式）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 精确匹配 record_key
            cursor.execute('''
                SELECT * FROM download_records WHERE record_key = ?
            ''', (name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # 模糊匹配 model_name 或 ollama_name
            name_lower = name.lower()
            cursor.execute('''
                SELECT * FROM download_records 
                WHERE LOWER(model_name) = ? OR LOWER(ollama_name) = ?
            ''', (name_lower, name_lower))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # 部分匹配
            cursor.execute('''
                SELECT * FROM download_records 
                WHERE LOWER(record_key) LIKE ? OR LOWER(model_name) LIKE ?
                LIMIT 1
            ''', (f'%{name_lower}%', f'%{name_lower}%'))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"查找下载记录失败: {e}")
            return None
    
    def list_download_records(self) -> List[Dict]:
        """列出所有下载记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM download_records ORDER BY download_time DESC
            ''')
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"列出下载记录失败: {e}")
            return []
    
    def delete_download_record(self, record_key: str) -> bool:
        """删除下载记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM download_records WHERE record_key = ?', (record_key,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除下载记录失败: {e}")
            return False
    
    # ==================== 人格管理 ====================
    
    def add_persona(self, key: str, name: str, icon: str = '🤖', 
                   icon_path: str = '', description: str = '', system_prompt: str = '',
                   persona_type: str = 'assistant', background_images: str = '',
                   scene_designs: list = None, enable_suggestions: bool = True,
                   gender: str = '', user_identity: str = '') -> bool:
        """添加人格"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 将 scene_designs 列表转换为 JSON 字符串
            scene_designs_str = json.dumps(scene_designs if scene_designs else [])
            
            cursor.execute('''
                INSERT OR REPLACE INTO personas 
                (key, name, icon, icon_path, description, system_prompt, type, background_images, 
                 scene_designs, enable_suggestions, gender, user_identity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (key, name, icon, icon_path, description, system_prompt, persona_type, background_images,
                  scene_designs_str, 1 if enable_suggestions else 0, gender, user_identity))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加人格失败: {e}")
            return False
    
    def get_persona(self, key: str) -> Optional[Dict]:
        """获取人格"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM personas WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                persona = dict(row)
                # 解析 scene_designs JSON 字符串
                if 'scene_designs' in persona and persona['scene_designs']:
                    try:
                        persona['scene_designs'] = json.loads(persona['scene_designs'])
                    except:
                        persona['scene_designs'] = []
                else:
                    persona['scene_designs'] = []
                
                # 转换 enable_suggestions 为布尔值
                if 'enable_suggestions' in persona:
                    persona['enable_suggestions'] = bool(persona['enable_suggestions'])
                
                return persona
            return None
        except Exception as e:
            logger.error(f"获取人格失败: {e}")
            return None
    
    def list_personas(self) -> Dict[str, Dict]:
        """列出所有人格（返回字典格式）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM personas')
            rows = cursor.fetchall()
            
            personas = {}
            for row in rows:
                row_dict = dict(row)
                key = row_dict.pop('key')
                
                # 解析 scene_designs JSON 字符串
                if 'scene_designs' in row_dict and row_dict['scene_designs']:
                    try:
                        row_dict['scene_designs'] = json.loads(row_dict['scene_designs'])
                    except:
                        row_dict['scene_designs'] = []
                else:
                    row_dict['scene_designs'] = []
                
                # 转换 enable_suggestions 为布尔值
                if 'enable_suggestions' in row_dict:
                    row_dict['enable_suggestions'] = bool(row_dict['enable_suggestions'])
                
                personas[key] = row_dict
            
            return personas
        except Exception as e:
            logger.error(f"列出人格失败: {e}")
            return {}
    
    def delete_persona(self, key: str) -> bool:
        """删除人格"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM personas WHERE key = ?', (key,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除人格失败: {e}")
            return False
    
    # ==================== 模型配置管理 ====================
    
    def add_model(self, model_id: str, category: str, subcategory: str, 
                  name: str, params: str, params_b: float, ctx: int,
                  lang: list, distilled: bool, quantizations: list, 
                  file_pattern: str) -> bool:
        """添加模型配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO models 
                (id, category, subcategory, name, params, params_b, ctx, lang, distilled, quantizations, file_pattern)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model_id, category, subcategory, name, params, params_b, ctx, 
                  json.dumps(lang), 1 if distilled else 0, json.dumps(quantizations), file_pattern))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加模型配置失败: {e}")
            return False
    
    def get_model(self, model_id: str) -> Optional[Dict]:
        """获取模型配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM models WHERE id = ?', (model_id,))
            row = cursor.fetchone()
            
            if row:
                model = dict(row)
                model['lang'] = json.loads(model['lang'])
                model['distilled'] = bool(model['distilled'])
                model['quantizations'] = json.loads(model['quantizations'])
                return model
            return None
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            return None
    
    def list_models(self) -> Dict:
        """列出所有模型配置（按分类组织）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM models ORDER BY category, subcategory, params_b')
            rows = cursor.fetchall()
            
            models = {}
            for row in rows:
                model = dict(row)
                model['lang'] = json.loads(model['lang'])
                model['distilled'] = bool(model['distilled'])
                model['quantizations'] = json.loads(model['quantizations'])
                
                category = model.pop('category')
                subcategory = model.pop('subcategory')
                
                if category not in models:
                    models[category] = {}
                if subcategory not in models[category]:
                    models[category][subcategory] = []
                
                models[category][subcategory].append(model)
            
            return models
        except Exception as e:
            logger.error(f"列出模型配置失败: {e}")
            return {}
    
    def delete_model(self, model_id: str) -> bool:
        """删除模型配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM models WHERE id = ?', (model_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除模型配置失败: {e}")
            return False
    
    # ==================== 个人设置管理 ====================
    
    def set_personal_setting(self, key: str, value: any) -> bool:
        """设置个人配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 将值转换为 JSON 字符串
            value_str = json.dumps(value) if not isinstance(value, str) else value
            
            cursor.execute('''
                INSERT OR REPLACE INTO personal_settings (key, value)
                VALUES (?, ?)
            ''', (key, value_str))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"设置个人配置失败: {e}")
            return False
    
    def get_personal_setting(self, key: str, default=None) -> any:
        """获取个人配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM personal_settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                try:
                    return json.loads(row['value'])
                except:
                    return row['value']
            return default
        except Exception as e:
            logger.error(f"获取个人配置失败: {e}")
            return default
    
    def get_all_personal_settings(self) -> Dict:
        """获取所有个人配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT key, value FROM personal_settings')
            rows = cursor.fetchall()
            
            settings = {}
            for row in rows:
                try:
                    settings[row['key']] = json.loads(row['value'])
                except:
                    settings[row['key']] = row['value']
            
            return settings
        except Exception as e:
            logger.error(f"获取所有个人配置失败: {e}")
            return {}
    
    def delete_personal_setting(self, key: str) -> bool:
        """删除个人配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM personal_settings WHERE key = ?', (key,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除个人配置失败: {e}")
            return False
    
    # ==================== 数据导出 ====================
    
    def export_conversation_to_json(self, conv_id: str) -> Optional[Dict]:
        """导出对话为 JSON 格式（兼容旧格式）"""
        try:
            conv = self.get_conversation(conv_id)
            if not conv:
                return None
            
            messages = self.get_messages(conv_id)
            
            # 按模型分组消息（兼容旧的 sessions 格式）
            sessions = {}
            for msg in messages:
                model = msg['model']
                if model not in sessions:
                    sessions[model] = {
                        'model': model,
                        'started_at': msg['timestamp'],
                        'messages': []
                    }
                
                sessions[model]['messages'].append({
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'],
                    'completed_at': msg.get('completed_at', '')
                })
            
            return {
                'id': conv['id'],
                'title': conv['title'],
                'persona': conv.get('persona', 'default'),
                'created_at': conv['created_at'],
                'updated_at': conv['updated_at'],
                'sessions': list(sessions.values())
            }
        except Exception as e:
            logger.error(f"导出对话失败: {e}")
            return None
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None


# 全局数据库实例
_db_instance = None

def get_database() -> Database:
    """获取数据库单例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
