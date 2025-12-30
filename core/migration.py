"""数据迁移工具 - 从 JSON 迁移到 SQLite"""

import os
import sys
import json
import shutil
from datetime import datetime
from typing import Tuple

from .database import get_database
from .logger import get_logger

logger = get_logger('migration')


class DataMigration:
    """数据迁移管理器"""
    
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.db = get_database()
        self.history_dir = os.path.join(self.base_dir, 'history')
        self.backup_dir = os.path.join(self.base_dir, 'backup_json')
    
    def check_migration_needed(self) -> bool:
        """检查是否需要迁移"""
        # 检查是否存在旧的 JSON 文件
        if not os.path.exists(self.history_dir):
            return False
        
        json_files = [f for f in os.listdir(self.history_dir) if f.endswith('.json')]
        return len(json_files) > 0
    
    def migrate_all(self) -> Tuple[bool, str]:
        """执行完整迁移"""
        try:
            logger.info("开始数据迁移...")
            
            # 1. 迁移对话历史
            conv_count, msg_count = self.migrate_conversations()
            logger.info(f"迁移对话: {conv_count} 个，消息: {msg_count} 条")
            
            # 2. 迁移下载记录
            record_count = self.migrate_download_records()
            logger.info(f"迁移下载记录: {record_count} 条")
            
            # 3. 迁移人格配置
            persona_count = self.migrate_personas()
            logger.info(f"迁移人格配置: {persona_count} 个")
            
            # 4. 备份原始 JSON 文件
            self.backup_json_files()
            
            summary = (
                f"迁移完成！\n"
                f"• 对话: {conv_count} 个\n"
                f"• 消息: {msg_count} 条\n"
                f"• 下载记录: {record_count} 条\n"
                f"• 人格配置: {persona_count} 个\n"
                f"原始文件已备份到: {self.backup_dir}"
            )
            
            logger.info(summary)
            return True, summary
        
        except Exception as e:
            error_msg = f"迁移失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def migrate_conversations(self) -> Tuple[int, int]:
        """迁移对话历史"""
        if not os.path.exists(self.history_dir):
            return 0, 0
        
        conv_count = 0
        msg_count = 0
        
        for filename in os.listdir(self.history_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.history_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取对话信息
                conv_id = data.get('id', filename.replace('.json', ''))
                title = data.get('title', '未命名对话')
                persona = data.get('persona', 'default')
                created_at = data.get('created_at', data.get('timestamp', datetime.now().isoformat()))
                updated_at = data.get('updated_at', created_at)
                
                # 创建对话
                self.db.create_conversation(conv_id, title, persona)
                
                # 更新时间（因为 create 会设置当前时间）
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET created_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (created_at, updated_at, conv_id))
                conn.commit()
                
                conv_count += 1
                
                # 迁移消息
                if 'sessions' in data:
                    # 新格式（多模型会话）
                    for session in data['sessions']:
                        model = session.get('model', 'unknown')
                        for msg in session.get('messages', []):
                            self.db.add_message(
                                conv_id=conv_id,
                                model=model,
                                role=msg.get('role', 'user'),
                                content=msg.get('content', ''),
                                timestamp=msg.get('timestamp', ''),
                                completed_at=msg.get('completed_at')
                            )
                            msg_count += 1
                
                elif 'messages' in data:
                    # 旧格式（单模型）
                    model = data.get('model', 'unknown')
                    for msg in data['messages']:
                        self.db.add_message(
                            conv_id=conv_id,
                            model=model,
                            role=msg.get('role', 'user'),
                            content=msg.get('content', ''),
                            timestamp=data.get('timestamp', ''),
                            completed_at=None
                        )
                        msg_count += 1
                
                logger.info(f"迁移对话: {filename}")
            
            except Exception as e:
                logger.error(f"迁移对话失败 {filename}: {e}")
                continue
        
        return conv_count, msg_count
    
    def migrate_download_records(self) -> int:
        """迁移下载记录"""
        records_file = os.path.join(self.base_dir, 'download_records.json')
        
        if not os.path.exists(records_file):
            return 0
        
        try:
            with open(records_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            count = 0
            for record_key, record in records.items():
                self.db.add_download_record(
                    record_key=record.get('record_key', record_key),
                    model_name=record.get('model_name', ''),
                    ollama_name=record.get('ollama_name', ''),
                    gguf_path=record.get('gguf_path', ''),
                    quantization=record.get('quantization', ''),
                    model_id=record.get('model_id', '')
                )
                count += 1
            
            logger.info(f"迁移下载记录: {count} 条")
            return count
        
        except Exception as e:
            logger.error(f"迁移下载记录失败: {e}")
            return 0
    
    def migrate_personas(self) -> int:
        """迁移人格配置"""
        personas_file = os.path.join(self.base_dir, 'personas.json')
        
        if not os.path.exists(personas_file):
            # 添加默认人格
            self.db.add_persona(
                key='default',
                name='默认助手',
                icon='🤖',
                description='通用AI助手',
                system_prompt=''
            )
            return 1
        
        try:
            with open(personas_file, 'r', encoding='utf-8') as f:
                personas = json.load(f)
            
            count = 0
            for key, persona in personas.items():
                self.db.add_persona(
                    key=key,
                    name=persona.get('name', '未命名'),
                    icon=persona.get('icon', '🤖'),
                    icon_path=persona.get('icon_path', ''),
                    description=persona.get('description', ''),
                    system_prompt=persona.get('system_prompt', '')
                )
                count += 1
            
            logger.info(f"迁移人格配置: {count} 个")
            return count
        
        except Exception as e:
            logger.error(f"迁移人格配置失败: {e}")
            return 0
    
    def backup_json_files(self):
        """备份原始 JSON 文件"""
        try:
            # 创建备份目录
            os.makedirs(self.backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_subdir = os.path.join(self.backup_dir, f'backup_{timestamp}')
            os.makedirs(backup_subdir, exist_ok=True)
            
            # 备份对话历史
            if os.path.exists(self.history_dir):
                history_backup = os.path.join(backup_subdir, 'history')
                shutil.copytree(self.history_dir, history_backup)
                logger.info(f"备份对话历史到: {history_backup}")
            
            # 备份下载记录
            records_file = os.path.join(self.base_dir, 'download_records.json')
            if os.path.exists(records_file):
                shutil.copy(records_file, os.path.join(backup_subdir, 'download_records.json'))
                logger.info("备份下载记录")
            
            # 备份人格配置
            personas_file = os.path.join(self.base_dir, 'personas.json')
            if os.path.exists(personas_file):
                shutil.copy(personas_file, os.path.join(backup_subdir, 'personas.json'))
                logger.info("备份人格配置")
            
            logger.info(f"所有文件已备份到: {backup_subdir}")
        
        except Exception as e:
            logger.error(f"备份文件失败: {e}")
    
    def rollback(self, backup_timestamp: str = None):
        """回滚到 JSON 格式（从备份恢复）"""
        try:
            if backup_timestamp:
                backup_path = os.path.join(self.backup_dir, f'backup_{backup_timestamp}')
            else:
                # 使用最新的备份
                backups = sorted([d for d in os.listdir(self.backup_dir) if d.startswith('backup_')])
                if not backups:
                    return False, "没有找到备份"
                backup_path = os.path.join(self.backup_dir, backups[-1])
            
            if not os.path.exists(backup_path):
                return False, f"备份不存在: {backup_path}"
            
            # 恢复对话历史
            history_backup = os.path.join(backup_path, 'history')
            if os.path.exists(history_backup):
                if os.path.exists(self.history_dir):
                    shutil.rmtree(self.history_dir)
                shutil.copytree(history_backup, self.history_dir)
            
            # 恢复下载记录
            records_backup = os.path.join(backup_path, 'download_records.json')
            if os.path.exists(records_backup):
                shutil.copy(records_backup, os.path.join(self.base_dir, 'download_records.json'))
            
            # 恢复人格配置
            personas_backup = os.path.join(backup_path, 'personas.json')
            if os.path.exists(personas_backup):
                shutil.copy(personas_backup, os.path.join(self.base_dir, 'personas.json'))
            
            logger.info(f"已从备份恢复: {backup_path}")
            return True, f"已恢复到: {backup_path}"
        
        except Exception as e:
            error_msg = f"回滚失败: {e}"
            logger.error(error_msg)
            return False, error_msg


def auto_migrate_on_startup():
    """启动时自动检查并迁移"""
    migration = DataMigration()
    
    if migration.check_migration_needed():
        logger.info("检测到旧的 JSON 数据，开始自动迁移...")
        success, message = migration.migrate_all()
        
        if success:
            logger.info("自动迁移成功")
        else:
            logger.error(f"自动迁移失败: {message}")
        
        return success, message
    else:
        logger.info("无需迁移")
        return True, "无需迁移"
