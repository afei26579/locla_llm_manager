"""聊天功能"""

import requests
import json
import os
import sys
from datetime import datetime

class ChatManager:
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.history_dir = os.path.join(base_dir, "history")
        os.makedirs(self.history_dir, exist_ok=True)
        
        self.current_model = None
        self.current_chat_data = None  # 当前对话数据
        self.is_generating = False  # 是否正在生成回复
        self.personas = self._load_personas()
        self.current_persona = "default"
    
    def set_model(self, model_name):
        """设置当前模型"""
        self.current_model = model_name
    
    def new_chat(self, persona_key: str = "default"):
        """创建新对话"""
        self.current_persona = persona_key
        self.current_chat_data = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "title": "",
            "persona": persona_key,  # 新增
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sessions": []
        }
        return self.current_chat_data["id"]

    def _load_personas(self):
        """加载人格配置"""
        personas_file = os.path.join(
            os.path.dirname(self.history_dir), "personas.json"
        )
        if os.path.exists(personas_file):
            try:
                with open(personas_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"default": {"name": "默认助手", "icon": "🤖", "description": "通用AI助手", "system_prompt": ""}}

    def _save_personas(self):
        """保存人格配置"""
        personas_file = os.path.join(
            os.path.dirname(self.history_dir), "personas.json"
        )
        with open(personas_file, 'w', encoding='utf-8') as f:
            json.dump(self.personas, f, ensure_ascii=False, indent=2)

    def get_personas(self):
        """获取所有人格"""
        return self.personas

    def add_persona(self, key: str, name: str, icon: str, description: str, system_prompt: str, icon_path: str = ""):
        """添加人格"""
        self.personas[key] = {
            "name": name,
            "icon": icon,
            "icon_path": icon_path,
            "description": description,
            "system_prompt": system_prompt
        }
        self._save_personas()

    def update_persona(self, key: str, name: str, icon: str, description: str, system_prompt: str, icon_path: str = ""):
        """更新人格"""
        if key in self.personas:
            self.personas[key] = {
                "name": name,
                "icon": icon,
                "icon_path": icon_path,
                "description": description,
                "system_prompt": system_prompt
            }
            self._save_personas()

    def delete_persona(self, key: str):
        """删除人格"""
        if key != "default" and key in self.personas:
            del self.personas[key]
            self._save_personas()
            return True
        return False

    def set_persona(self, persona_key: str):
        """设置当前人格"""
        if persona_key in self.personas:
            self.current_persona = persona_key

    def get_current_persona(self):
        """获取当前人格信息"""
        return self.personas.get(self.current_persona, self.personas.get("default"))

    def _get_or_create_session(self, model_name):
        """获取或创建当前模型的会话"""
        if not self.current_chat_data:
            self.new_chat()
        
        # 查找现有会话
        for session in self.current_chat_data["sessions"]:
            if session["model"] == model_name:
                return session
        
        # 创建新会话
        session = {
            "model": model_name,
            "started_at": datetime.now().isoformat(),
            "messages": []
        }
        self.current_chat_data["sessions"].append(session)
        return session
    
    def _get_current_session_messages(self):
        """获取当前模型的对话历史（包含系统提示词）"""
        if not self.current_chat_data or not self.current_model:
            return []
        
        messages = []
        
        # 添加系统提示词
        persona = self.get_current_persona()
        system_prompt = persona.get("system_prompt", "")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史
        session = self._get_or_create_session(self.current_model)
        for m in session["messages"]:
            messages.append({"role": m["role"], "content": m["content"]})
        
        return messages

    def get_all_messages_sorted(self):
        """获取所有模型的消息，按时间排序（用于 UI 显示）"""
        if not self.current_chat_data:
            return []
        
        all_messages = []
        for session in self.current_chat_data["sessions"]:
            model = session["model"]
            for msg in session["messages"]:
                all_messages.append({
                    "model": model,
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp", ""),
                    "completed_at": msg.get("completed_at", "")
                })
        
        # 按时间排序
        all_messages.sort(key=lambda x: x.get("timestamp", ""))
        return all_messages
    
    def chat(self, user_message, stream_callback=None):
        """发送消息"""
        if not self.current_model:
            return "请先选择模型"
        
        if self.is_generating:
            return "正在生成回复，请稍候..."
        
        self.is_generating = True
        
        try:
            # 获取当前模型的会话
            session = self._get_or_create_session(self.current_model)
            
            # 记录用户消息
            user_msg = {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            }
            session["messages"].append(user_msg)
            
            # 设置 title（使用第一条用户消息）
            if not self.current_chat_data["title"]:
                title = user_message[:15]
                if len(user_message) > 15:
                    title += "..."
                self.current_chat_data["title"] = title
            
            # 更新时间
            self.current_chat_data["updated_at"] = datetime.now().isoformat()
            
            # 获取当前会话的消息历史
            messages = self._get_current_session_messages()
            
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
                ai_msg = {
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": user_msg["timestamp"],  # 与用户消息关联
                    "completed_at": datetime.now().isoformat()
                }
                session["messages"].append(ai_msg)
                
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
                ai_msg = {
                    "role": "assistant",
                    "content": assistant_message,
                    "timestamp": user_msg["timestamp"],
                    "completed_at": datetime.now().isoformat()
                }
                session["messages"].append(ai_msg)
                
                return assistant_message
        
        except Exception as e:
            # 移除失败的用户消息
            if session["messages"] and session["messages"][-1]["role"] == "user":
                session["messages"].pop()
            return f"请求失败: {e}"
        
        finally:
            self.is_generating = False
    
    def clear_conversation(self):
        """清空对话"""
        self.current_chat_data = None
    
    def save_history(self, chat_id=None):
        """保存聊天记录"""
        if not self.current_chat_data:
            return None
        
        if chat_id:
            self.current_chat_data["id"] = chat_id
        
        self.current_chat_data["updated_at"] = datetime.now().isoformat()
        
        filename = os.path.join(self.history_dir, f"{self.current_chat_data['id']}.json")
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.current_chat_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def load_history(self, filename):
        """加载聊天记录"""
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        filepath = os.path.join(self.history_dir, filename)
        
        with open(filepath, "r", encoding="utf-8") as f:
            self.current_chat_data = json.load(f)
        
        # 兼容旧格式
        if "sessions" not in self.current_chat_data:
            # 旧格式转换
            old_messages = self.current_chat_data.get("messages", [])
            old_model = self.current_chat_data.get("model", "unknown")
            
            self.current_chat_data["sessions"] = [{
                "model": old_model,
                "started_at": self.current_chat_data.get("timestamp", datetime.now().isoformat()),
                "messages": [
                    {
                        "role": m.get("role", "user"),
                        "content": m.get("content", ""),
                        "timestamp": self.current_chat_data.get("timestamp", "")
                    }
                    for m in old_messages
                ]
            }]
            
            if "messages" in self.current_chat_data:
                del self.current_chat_data["messages"]
            if "model" in self.current_chat_data:
                del self.current_chat_data["model"]
        self.current_persona = self.current_chat_data.get("persona", "default")
        return self.current_chat_data
    
    def list_history(self):
        """列出所有聊天记录"""
        histories = []
        
        for f in os.listdir(self.history_dir):
            if f.endswith(".json"):
                filepath = os.path.join(self.history_dir, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                    
                    # 统计消息数量
                    total_messages = 0
                    models_used = []
                    if "sessions" in data:
                        for session in data["sessions"]:
                            total_messages += len(session.get("messages", []))
                            if session.get("model") and session["model"] not in models_used:
                                models_used.append(session["model"])
                    else:
                        # 兼容旧格式
                        total_messages = len(data.get("messages", []))
                        if data.get("model"):
                            models_used.append(data["model"])
                    
                    histories.append({
                        "filename": f,
                        "id": data.get("id", f.replace(".json", "")),
                        "title": data.get("title", "未命名对话"),
                        "models": models_used,
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", data.get("timestamp", "")),
                        "messages_count": total_messages
                    })
                except:
                    pass
        
        return sorted(histories, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    def delete_history(self, filename):
        """删除聊天记录"""
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        filepath = os.path.join(self.history_dir, filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except:
            pass
        return False
    
    def get_title(self):
        """获取当前对话标题"""
        if self.current_chat_data:
            return self.current_chat_data.get("title", "新对话")
        return "新对话"