"""聊天功能 - 使用 SQLite 数据库版本"""

import requests
import json
from datetime import datetime
from typing import Optional, List, Dict, Callable
import logging

from .database import get_database

logger = logging.getLogger(__name__)


class ChatManager:
    """聊天管理器（数据库版本）"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.db = get_database()
        
        self.current_model = None
        self.current_chat_id = None
        self.is_generating = False
        self.current_persona = "default"
        
        # 确保默认人格存在
        self._ensure_default_persona()
    
    def _ensure_default_persona(self):
        """确保默认人格存在"""
        if not self.db.get_persona('default'):
            self.db.add_persona(
                key='default',
                name='默认助手',
                icon='🤖',
                description='通用AI助手',
                system_prompt=''
            )
    
    def set_model(self, model_name: str):
        """设置当前模型"""
        self.current_model = model_name
    
    def new_chat(self, persona_key: str = "default") -> str:
        """创建新对话"""
        self.current_persona = persona_key
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.db.create_conversation(chat_id, "", persona_key)
        self.current_chat_id = chat_id
        
        return chat_id
    
    def get_personas(self) -> Dict[str, Dict]:
        """获取所有人格"""
        return self.db.list_personas()
    
    def add_persona(self, key: str, name: str, icon: str, description: str, 
                   system_prompt: str, icon_path: str = "", persona_type: str = "assistant",
                   background_images: list = None):
        """添加人格"""
        bg_str = json.dumps(background_images) if background_images else ''
        self.db.add_persona(key, name, icon, icon_path, description, system_prompt, persona_type, bg_str)
    
    def update_persona(self, key: str, name: str, icon: str, description: str, 
                      system_prompt: str, icon_path: str = "", persona_type: str = "assistant",
                      background_images: list = None):
        """更新人格"""
        bg_str = json.dumps(background_images) if background_images else ''
        self.db.add_persona(key, name, icon, icon_path, description, system_prompt, persona_type, bg_str)
    
    def delete_persona(self, key: str) -> bool:
        """删除人格（debug 模式下允许删除默认助手）"""
        # 读取 debug 配置
        import os
        import sys
        import json
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_path = os.path.join(base_dir, 'config.json')
        debug_mode = False
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                debug_mode = config.get('debug', False)
        except Exception as e:
            logger.warning(f"读取 debug 配置失败: {e}")
        
        # 非 debug 模式下不允许删除默认助手
        if key == "default" and not debug_mode:
            return False
        
        return self.db.delete_persona(key)
    
    def set_persona(self, persona_key: str):
        """设置当前人格"""
        if self.db.get_persona(persona_key):
            self.current_persona = persona_key
    
    def get_current_persona(self) -> Dict:
        """获取当前人格信息"""
        persona = self.db.get_persona(self.current_persona)
        if persona:
            return persona
        return {
            'name': '默认助手',
            'icon': '🤖',
            'description': '通用AI助手',
            'system_prompt': ''
        }
    
    def _get_context_messages(self) -> List[Dict]:
        """获取当前对话的上下文消息（用于发送给 API）"""
        if not self.current_chat_id or not self.current_model:
            return []
        
        messages = []
        
        # 添加系统提示词
        persona = self.get_current_persona()
        system_prompt = persona.get('system_prompt', '')
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 获取当前模型的历史消息
        db_messages = self.db.get_messages_by_model(self.current_chat_id, self.current_model)
        
        for msg in db_messages:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        return messages
    
    def get_all_messages_sorted(self) -> List[Dict]:
        """获取所有消息（按时间排序，用于 UI 显示）"""
        if not self.current_chat_id:
            return []
        
        messages = self.db.get_messages(self.current_chat_id)
        return messages
    
    def chat(self, user_message: str, stream_callback: Optional[Callable] = None) -> str:
        """发送消息并获取回复"""
        if not self.current_model:
            return "请先选择模型"
        
        if self.is_generating:
            return "正在生成回复，请稍候..."
        
        self.is_generating = True
        
        try:
            # 如果没有当前对话，创建新对话
            if not self.current_chat_id:
                self.new_chat(self.current_persona)
            
            # 记录用户消息
            timestamp = datetime.now().isoformat()
            self.db.add_message(
                conv_id=self.current_chat_id,
                model=self.current_model,
                role='user',
                content=user_message,
                timestamp=timestamp
            )
            
            # 设置标题（使用第一条用户消息）
            conv = self.db.get_conversation(self.current_chat_id)
            if not conv['title']:
                title = user_message[:15]
                if len(user_message) > 15:
                    title += "..."
                self.db.update_conversation(self.current_chat_id, title=title)
            
            # 获取上下文消息
            messages = self._get_context_messages()
            
            # 输出系统提示词日志
            from core.logger import get_logger
            logger = get_logger('chat')
            persona = self.get_current_persona()
            system_prompt = persona.get('system_prompt', '')
            if system_prompt:
                logger.info(f"当前对话使用的系统提示词: {system_prompt}")
            else:
                logger.info("当前对话未设置系统提示词")
            logger.info(f"当前使用模型: {self.current_model}")
            logger.info(f"当前助手/角色: {persona.get('name', '默认')}")
            
            # 调用 Ollama API
            if stream_callback:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.current_model,
                        "messages": messages,
                        "stream": True
                    },
                    stream=True,
                    timeout=300
                )
                
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                full_response += chunk
                                stream_callback(chunk)
                        except:
                            pass
                
                # 记录 AI 回复
                completed_at = datetime.now().isoformat()
                self.db.add_message(
                    conv_id=self.current_chat_id,
                    model=self.current_model,
                    role='assistant',
                    content=full_response,
                    timestamp=timestamp,
                    completed_at=completed_at
                )
                
                return full_response
            else:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.current_model,
                        "messages": messages,
                        "stream": False
                    },
                    timeout=300
                )
                
                data = response.json()
                assistant_message = data.get("message", {}).get("content", "")
                
                # 记录 AI 回复
                completed_at = datetime.now().isoformat()
                self.db.add_message(
                    conv_id=self.current_chat_id,
                    model=self.current_model,
                    role='assistant',
                    content=assistant_message,
                    timestamp=timestamp,
                    completed_at=completed_at
                )
                
                return assistant_message
        
        except Exception as e:
            logger.error(f"聊天请求失败: {e}")
            return f"请求失败: {e}"
        
        finally:
            self.is_generating = False
    
    def load_history(self, chat_id: str) -> Dict:
        """加载历史对话"""
        conv = self.db.get_conversation(chat_id)
        if not conv:
            return {}
        
        self.current_chat_id = chat_id
        self.current_persona = conv.get('persona', 'default')
        
        # 返回兼容格式
        return {
            'id': conv['id'],
            'title': conv['title'],
            'persona': conv['persona'],
            'created_at': conv['created_at'],
            'updated_at': conv['updated_at']
        }
    
    def list_history(self) -> List[Dict]:
        """列出所有对话历史"""
        conversations = self.db.list_conversations(limit=100)
        
        # 转换为兼容格式
        histories = []
        for conv in conversations:
            # 获取该对话使用的模型
            messages = self.db.get_messages(conv['id'], limit=1)
            models_used = list(set([msg['model'] for msg in self.db.get_messages(conv['id'])]))
            
            histories.append({
                'filename': f"{conv['id']}.json",  # 兼容旧格式
                'id': conv['id'],
                'title': conv['title'],
                'persona': conv.get('persona', 'default'),  # 添加 persona 字段
                'timestamp': conv.get('created_at', ''),  # 添加 timestamp 字段
                'models': models_used,
                'created_at': conv['created_at'],
                'updated_at': conv['updated_at'],
                'messages_count': conv.get('message_count', 0)
            })
        
        return histories
    
    def delete_history(self, filename: str) -> bool:
        """删除历史对话"""
        # 兼容旧格式的 filename
        chat_id = filename.replace('.json', '')
        return self.db.delete_conversation(chat_id)
    
    def save_history(self, chat_id: str = None):
        """保存对话（数据库版本自动保存，此方法保留兼容性）"""
        # 数据库版本实时保存，无需手动调用
        # 但保留此方法以兼容现有代码
        if chat_id:
            self.current_chat_id = chat_id
        
        # 更新 updated_at
        if self.current_chat_id:
            conv = self.db.get_conversation(self.current_chat_id)
            if conv:
                self.db.update_conversation(
                    self.current_chat_id,
                    title=conv['title']
                )
        
        return self.current_chat_id
    
    def get_title(self) -> str:
        """获取当前对话标题"""
        if self.current_chat_id:
            conv = self.db.get_conversation(self.current_chat_id)
            if conv:
                return conv['title'] or "新对话"
        return "新对话"
    
    def clear_conversation(self):
        """清空当前对话"""
        self.current_chat_id = None
    
    def export_to_json(self, chat_id: str) -> Optional[Dict]:
        """导出对话为 JSON 格式"""
        return self.db.export_conversation_to_json(chat_id)
    
    def search_messages(self, keyword: str) -> List[Dict]:
        """搜索消息内容"""
        return self.db.search_messages(keyword)
