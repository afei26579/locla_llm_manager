"""聊天功能 - 使用 SQLite 数据库版本"""

import requests
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Callable

from .database import get_database
from .logger import get_logger

logger = get_logger('chat')


def filter_think_content(text: str) -> str:
    """过滤掉思考标签及其内容
    
    支持的标签格式：
    - <think>...</think>
    - <thinking>...</thinking>
    - <reasoning>...</reasoning>
    
    也处理不完整的标签和模板残留
    """
    filtered = text
    
    # 完整标签匹配
    patterns = [
        r'<think>.*?</think>',
        r'<thinking>.*?</thinking>',
        r'<reasoning>.*?</reasoning>',
    ]
    
    for pattern in patterns:
        filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
    
    # 处理模板残留标记后跟思考内容的情况
    # 例如：<|im_end>>思考内容...</think>
    template_think_patterns = [
        r'<\|im_end\|?>+.*?</think>',
        r'<\|im_end\|?>+.*?</thinking>',
        r'<\|im_end\|?>+.*?</reasoning>',
    ]
    for pattern in template_think_patterns:
        filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
    
    # 处理只有结束标签的情况（思考内容可能在文本中间）
    # 匹配：任意非<字符序列 + </think>（但前面不能是正常内容的一部分）
    # 使用更宽松的匹配：从上一个 > 或文本开头到 </think>
    incomplete_patterns = [
        r'>[^<]*</think>',
        r'>[^<]*</thinking>',
        r'>[^<]*</reasoning>',
    ]
    for pattern in incomplete_patterns:
        filtered = re.sub(pattern, '>', filtered, flags=re.DOTALL)
    
    # 处理文本开头的不完整标签
    start_incomplete = [
        r'^[^<]*</think>',
        r'^[^<]*</thinking>',
        r'^[^<]*</reasoning>',
    ]
    for pattern in start_incomplete:
        filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
    
    # 处理只有开始标签（流式输出中）
    incomplete_start_patterns = [
        r'<think>[^<]*$',
        r'<thinking>[^<]*$',
        r'<reasoning>[^<]*$',
    ]
    for pattern in incomplete_start_patterns:
        filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
    
    # 清理模板残留标记
    filtered = re.sub(r'<\|im_end\|?>+', '', filtered)
    filtered = re.sub(r'<\|im_start\|?>+', '', filtered)
    
    # 清理多余的空行
    filtered = re.sub(r'\n{3,}', '\n\n', filtered)
    return filtered.strip()


def extract_think_content(text: str) -> tuple:
    """提取思考内容和正文内容
    
    支持多种标签格式和不完整标签
    
    Returns:
        (think_content, main_content) - 思考内容和正文内容
    """
    think_parts = []
    
    # 完整标签匹配
    tag_patterns = [
        r'<think>(.*?)</think>',
        r'<thinking>(.*?)</thinking>',
        r'<reasoning>(.*?)</reasoning>',
    ]
    
    for pattern in tag_patterns:
        matches = re.findall(pattern, text, flags=re.DOTALL)
        think_parts.extend(matches)
    
    # 处理模板残留后跟思考内容
    template_patterns = [
        r'<\|im_end\|?>+(.*?)</think>',
        r'<\|im_end\|?>+(.*?)</thinking>',
        r'<\|im_end\|?>+(.*?)</reasoning>',
    ]
    for pattern in template_patterns:
        matches = re.findall(pattern, text, flags=re.DOTALL)
        think_parts.extend(matches)
    
    # 处理 > 后跟思考内容到 </think> 的情况
    incomplete_patterns = [
        r'>([^<]*)</think>',
        r'>([^<]*)</thinking>',
        r'>([^<]*)</reasoning>',
    ]
    for pattern in incomplete_patterns:
        matches = re.findall(pattern, text, flags=re.DOTALL)
        think_parts.extend(matches)
    
    # 处理文本开头的不完整结束标签
    start_incomplete = [
        r'^([^<]*)</think>',
        r'^([^<]*)</thinking>',
        r'^([^<]*)</reasoning>',
    ]
    for pattern in start_incomplete:
        match = re.match(pattern, text, flags=re.DOTALL)
        if match:
            think_parts.append(match.group(1))
    
    # 处理只有开始标签（流式输出中）
    incomplete_start_patterns = [
        r'<think>([^<]*)$',
        r'<thinking>([^<]*)$',
        r'<reasoning>([^<]*)$',
    ]
    for pattern in incomplete_start_patterns:
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            think_parts.append(match.group(1))
    
    think_content = '\n'.join([p.strip() for p in think_parts if p.strip()])
    
    # 移除所有思考标签得到正文
    main_content = filter_think_content(text)
    
    return think_content, main_content


class RepeatDetector:
    """检测 LLM 输出中的重复内容"""
    
    def __init__(self, min_pattern_len: int = 20, max_repeats: int = 3):
        """
        Args:
            min_pattern_len: 最小重复模式长度
            max_repeats: 允许的最大重复次数
        """
        self.min_pattern_len = min_pattern_len
        self.max_repeats = max_repeats
        self.detected_pattern = None
        self.first_occurrence = 0
    
    def check(self, text: str) -> bool:
        """检查文本是否包含重复内容
        
        Returns:
            True 如果检测到过多重复
        """
        if len(text) < self.min_pattern_len * 2:
            return False
        
        # 只检查最后一部分文本，提高效率
        check_len = min(len(text), 2000)
        check_text = text[-check_len:]
        
        # 尝试不同长度的模式
        for pattern_len in range(self.min_pattern_len, min(200, len(check_text) // 2)):
            # 从末尾取一个模式
            pattern = check_text[-pattern_len:]
            
            # 计算这个模式在文本中出现的次数
            count = 0
            pos = 0
            first_pos = -1
            while True:
                found = check_text.find(pattern, pos)
                if found == -1:
                    break
                if first_pos == -1:
                    first_pos = found
                count += 1
                pos = found + 1
            
            if count >= self.max_repeats:
                self.detected_pattern = pattern
                # 计算在原文中的位置
                self.first_occurrence = len(text) - check_len + first_pos
                logger.warning(f"[重复检测] 发现重复模式: 长度={pattern_len}, 次数={count}")
                logger.debug(f"[重复检测] 模式内容: {pattern[:50]}...")
                return True
        
        return False
    
    def truncate(self, text: str) -> str:
        """截断重复部分，保留第一次出现的内容"""
        if self.detected_pattern and self.first_occurrence > 0:
            # 保留到第一次重复结束的位置
            truncate_pos = self.first_occurrence + len(self.detected_pattern)
            return text[:truncate_pos].rstrip()
        return text


class ChatManager:
    """聊天管理器（数据库版本）"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.db = get_database()
        
        self.current_model = None
        self.current_chat_id = None
        self.is_generating = False
        self.stop_requested = False  # 停止生成标志
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
                   background_images: list = None, scene_designs: list = None,
                   enable_suggestions: bool = True, gender: str = "", user_identity: str = ""):
        """添加人格"""
        bg_str = json.dumps(background_images) if background_images else ''
        self.db.add_persona(key, name, icon, icon_path, description, system_prompt, persona_type, bg_str,
                           scene_designs, enable_suggestions, gender, user_identity)
    
    def update_persona(self, key: str, name: str, icon: str, description: str, 
                      system_prompt: str, icon_path: str = "", persona_type: str = "assistant",
                      background_images: list = None, scene_designs: list = None,
                      enable_suggestions: bool = True, gender: str = "", user_identity: str = ""):
        """更新人格"""
        bg_str = json.dumps(background_images) if background_images else ''
        self.db.add_persona(key, name, icon, icon_path, description, system_prompt, persona_type, bg_str,
                           scene_designs, enable_suggestions, gender, user_identity)
    
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
            persona['key'] = self.current_persona  # 确保包含 key
            return persona
        return {
            'key': 'default',
            'name': '默认助手',
            'icon': '🤖',
            'description': '通用AI助手',
            'system_prompt': ''
        }
    
    def _get_context_messages(self) -> List[Dict]:
        """获取当前对话的上下文消息（用于发送给 API）"""
        if not self.current_chat_id or not self.current_model:
            logger.warning(f"[上下文] 缺少必要信息: chat_id={self.current_chat_id}, model={self.current_model}")
            return []
        
        messages = []
        
        # 添加系统提示词
        persona = self.get_current_persona()
        system_prompt = persona.get('system_prompt', '')
        user_identity = persona.get('user_identity', '')
        
        # 如果有用户身份设计，将其加入系统提示词
        if system_prompt:
            if user_identity:
                full_prompt = f"{system_prompt}\n\n【用户身份】\n{user_identity}"
            else:
                full_prompt = system_prompt
            messages.append({"role": "system", "content": full_prompt})
        
        # 检查是否是角色扮演类型
        is_roleplay = persona.get('type', 'assistant') == 'roleplay'
        
        # 获取当前模型的历史消息
        db_messages = self.db.get_messages_by_model(self.current_chat_id, self.current_model)
        
        logger.info(f"[上下文] chat_id={self.current_chat_id}, model={self.current_model}, 历史消息数={len(db_messages)}")
        
        for msg in db_messages:
            content = msg['content']
            # 角色扮演模式下，过滤掉历史消息中的思考内容
            if is_roleplay and msg['role'] == 'assistant':
                content = filter_think_content(content)
            
            messages.append({
                "role": msg['role'],
                "content": content
            })
            logger.debug(f"[上下文] 添加消息: role={msg['role']}, content={content[:50]}...")
        
        logger.info(f"[上下文] 最终消息数={len(messages)} (含系统提示词)")
        return messages
    
    def get_all_messages_sorted(self) -> List[Dict]:
        """获取所有消息（按时间排序，用于 UI 显示）"""
        if not self.current_chat_id:
            return []
        
        messages = self.db.get_messages(self.current_chat_id)
        return messages
    
    def chat(self, user_message: str, stream_callback: Optional[Callable] = None, 
             options: Optional[Dict] = None) -> str:
        """发送消息并获取回复
        
        Args:
            user_message: 用户消息
            stream_callback: 流式回调函数
            options: Ollama 模型参数 (temperature, top_p, top_k, etc.)
        """
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
            persona = self.get_current_persona()
            system_prompt = persona.get('system_prompt', '')
            
            logger.info(f"当前使用模型: {self.current_model}")
            logger.info(f"当前助手/角色: {persona.get('name', '默认')}")
            if options:
                logger.info(f"模型参数: {options}")
            
            # 构建请求参数
            request_data = {
                "model": self.current_model,
                "messages": messages,
                "stream": True if stream_callback else False
            }
            
            # 添加自定义参数
            if options:
                # 过滤掉默认值和无效值
                filtered_options = {}
                for k, v in options.items():
                    if k == 'num_predict' and v == -1:
                        continue  # -1 表示无限，不传
                    if k == 'seed' and v == -1:
                        continue  # -1 表示随机，不传
                    filtered_options[k] = v
                if filtered_options:
                    request_data['options'] = filtered_options
            
            logger.info(f"当前使用模型: {self.current_model}")
            logger.info(f"当前助手/角色: {persona.get('name', '默认')}")
            
            # 调用 Ollama API
            if stream_callback:
                logger.info(f"发送流式请求到 Ollama: {self.base_url}/api/chat")
                logger.info(f"请求参数: model={self.current_model}, messages_count={len(messages)}")
                
                try:
                    response = requests.post(
                        f"{self.base_url}/api/chat",
                        json=request_data,
                        stream=True,
                        timeout=300
                    )
                except requests.exceptions.ConnectionError:
                    error_msg = "⚠️ 无法连接到模型引擎，请检查服务是否已启动"
                    logger.error(f"连接错误: 无法连接到 Ollama")
                    stream_callback(error_msg)
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                except requests.exceptions.Timeout:
                    error_msg = "⚠️ 请求超时，模型响应时间过长"
                    logger.error(f"请求超时")
                    stream_callback(error_msg)
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                
                logger.info(f"响应状态码: {response.status_code}")
                
                # 处理非 200 状态码
                if response.status_code != 200:
                    error_msg = self._parse_ollama_error(response)
                    logger.error(f"Ollama API 错误: {response.text}")
                    stream_callback(error_msg)
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                
                full_response = ""
                chunk_count = 0
                
                # 重复检测相关变量
                repeat_detector = RepeatDetector(min_pattern_len=20, max_repeats=3)
                should_stop = False
                user_stopped = False
                
                for line in response.iter_lines():
                    # 检查用户停止请求
                    if self.stop_requested:
                        logger.info("[用户停止] 用户请求停止生成")
                        response.close()
                        user_stopped = True
                        stream_callback("\n\n⏹ [已停止生成]")
                        break
                    
                    if should_stop:
                        logger.warning("[重复检测] 检测到重复内容，停止生成")
                        response.close()
                        break
                    
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                full_response += chunk
                                stream_callback(chunk)
                                chunk_count += 1
                                
                                # 检测重复
                                if repeat_detector.check(full_response):
                                    should_stop = True
                                    # 截断重复部分
                                    full_response = repeat_detector.truncate(full_response)
                                    stream_callback("\n\n⚠️ [检测到重复内容，已自动停止]")
                        except Exception as e:
                            logger.error(f"解析响应行失败: {e}, line={line}")
                
                logger.info(f"流式响应完成: 收到 {chunk_count} 个块, 总长度 {len(full_response)} 字符, 用户停止={user_stopped}")
                
                # 处理空回复（非用户主动停止的情况）
                if not full_response.strip() and not user_stopped:
                    logger.warning("警告: AI 回复为空！")
                    logger.warning(f"模型: {self.current_model}")
                    logger.warning(f"上下文消息数: {len(messages)}")
                    error_msg = "⚠️ 模型返回了空回复，可能原因：\n• 模型加载异常\n• 输入内容触发了安全限制\n• 请尝试重新发送或切换模型"
                    stream_callback(error_msg)
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                
                # 检查是否是角色扮演类型，如果是则过滤思考内容
                is_roleplay = persona.get('type', 'assistant') == 'roleplay'
                content_to_save = filter_think_content(full_response) if is_roleplay else full_response
                
                # 记录 AI 回复
                completed_at = datetime.now().isoformat()
                self.db.add_message(
                    conv_id=self.current_chat_id,
                    model=self.current_model,
                    role='assistant',
                    content=content_to_save,
                    timestamp=timestamp,
                    completed_at=completed_at
                )
                
                # 返回原始响应（前端会根据类型处理显示）
                return full_response
            else:
                try:
                    response = requests.post(
                        f"{self.base_url}/api/chat",
                        json=request_data,
                        timeout=300
                    )
                except requests.exceptions.ConnectionError:
                    error_msg = "⚠️ 无法连接到模型引擎，请检查服务是否已启动"
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                except requests.exceptions.Timeout:
                    error_msg = "⚠️ 请求超时，模型响应时间过长"
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                
                if response.status_code != 200:
                    error_msg = self._parse_ollama_error(response)
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                
                data = response.json()
                assistant_message = data.get("message", {}).get("content", "")
                
                if not assistant_message.strip():
                    error_msg = "⚠️ 模型返回了空回复，请尝试重新发送"
                    self._save_error_response(error_msg, timestamp)
                    return error_msg
                
                # 检查是否是角色扮演类型，如果是则过滤思考内容
                is_roleplay = persona.get('type', 'assistant') == 'roleplay'
                content_to_save = filter_think_content(assistant_message) if is_roleplay else assistant_message
                
                # 记录 AI 回复
                completed_at = datetime.now().isoformat()
                self.db.add_message(
                    conv_id=self.current_chat_id,
                    model=self.current_model,
                    role='assistant',
                    content=content_to_save,
                    timestamp=timestamp,
                    completed_at=completed_at
                )
                
                return assistant_message
        
        except Exception as e:
            logger.error(f"聊天请求失败: {e}")
            error_msg = f"⚠️ 请求失败: {self._translate_error(str(e))}"
            return error_msg
        
        finally:
            self.is_generating = False
    
    def _parse_ollama_error(self, response) -> str:
        """解析 Ollama 错误响应，返回中文提示"""
        status_code = response.status_code
        
        try:
            error_data = response.json()
            error_text = error_data.get('error', '')
        except:
            error_text = response.text
        
        logger.error(f"Ollama 错误 [{status_code}]: {error_text}")
        
        # 根据状态码和错误内容返回中文提示
        if status_code == 500:
            if 'not supported by your version' in error_text or 'need to upgrade' in error_text:
                return "⚠️ 当前 Ollama 版本不支持此模型\n请升级 Ollama 到最新版本后重试"
            elif 'model not found' in error_text.lower():
                return "⚠️ 模型未找到\n请在设置中重新下载模型"
            elif 'out of memory' in error_text.lower() or 'oom' in error_text.lower():
                return "⚠️ 内存不足，无法加载模型\n请尝试使用更小的模型或关闭其他程序"
            elif 'terminated' in error_text.lower():
                return "⚠️ 模型运行异常终止\n可能是内存不足或模型文件损坏，请尝试重新下载"
            else:
                return f"⚠️ 模型运行错误\n请尝试重启模型引擎或重新下载模型"
        
        elif status_code == 404:
            return f"⚠️ 模型 {self.current_model} 不存在\n请在设置中下载此模型"
        
        elif status_code == 400:
            return "⚠️ 请求参数错误\n请检查输入内容是否正常"
        
        elif status_code == 503:
            return "⚠️ 模型引擎暂时不可用\n请稍后重试或重启服务"
        
        elif status_code == 408:
            return "⚠️ 请求超时\n模型响应时间过长，请重试"
        
        else:
            return f"⚠️ 服务器错误 (错误码: {status_code})\n请检查模型引擎状态"
    
    def _translate_error(self, error: str) -> str:
        """将常见英文错误翻译为中文"""
        translations = {
            'Connection refused': '连接被拒绝，模型引擎可能未启动',
            'Connection reset': '连接被重置，请检查网络',
            'timed out': '连接超时',
            'No such file': '文件不存在',
            'Permission denied': '权限不足',
            'out of memory': '内存不足',
        }
        
        for en, zh in translations.items():
            if en.lower() in error.lower():
                return zh
        
        return error
    
    def _save_error_response(self, error_msg: str, timestamp: str):
        """保存错误响应到数据库"""
        try:
            completed_at = datetime.now().isoformat()
            self.db.add_message(
                conv_id=self.current_chat_id,
                model=self.current_model,
                role='assistant',
                content=error_msg,
                timestamp=timestamp,
                completed_at=completed_at
            )
        except Exception as e:
            logger.error(f"保存错误响应失败: {e}")
    
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
    
    def get_role_scene_config(self, persona_key: str) -> dict:
        """获取角色场景配置"""
        persona = self.db.get_persona(persona_key)
        if not persona:
            return {
                'scene_designs': [],
                'enable_suggestions': False
            }
        
        return {
            'scene_designs': persona.get('scene_designs', []),
            'enable_suggestions': persona.get('enable_suggestions', True)
        }
    
    def get_random_scene(self, persona_key: str) -> dict:
        """根据当前时间段获取对应场景设计"""
        import random
        from datetime import datetime
        
        config = self.get_role_scene_config(persona_key)
        scene_designs = config.get('scene_designs', [])
        
        if not scene_designs:
            return {'scene': '', 'suggestions': []}
        
        # 获取当前小时
        current_hour = datetime.now().hour
        
        # 根据时间确定当前时间段
        def get_current_period():
            if 0 <= current_hour < 4:
                return 'midnight'  # 凌晨
            elif 4 <= current_hour < 6:
                return 'dawn'  # 拂晓
            elif 6 <= current_hour < 10:
                return 'morning'  # 晨间
            elif 10 <= current_hour < 12:
                return 'forenoon'  # 上午
            elif 12 <= current_hour < 14:
                return 'noon'  # 中午
            elif 14 <= current_hour < 17:
                return 'afternoon'  # 午后
            elif 17 <= current_hour < 19:
                return 'dusk'  # 傍晚
            else:
                return 'night'  # 夜晚
        
        current_period = get_current_period()
        
        # 筛选匹配当前时间段的场景（包括 any）
        matching_scenes = [
            s for s in scene_designs 
            if s.get('time_period', 'any') in ('any', current_period)
        ]
        
        # 如果没有匹配的场景，使用所有场景
        if not matching_scenes:
            matching_scenes = scene_designs
        
        return random.choice(matching_scenes)
    
    def generate_suggestions(self, ai_response: str, count: int = 3) -> list:
        """根据 AI 回复生成推荐选项"""
        import time
        start_time = time.time()
        logger.info(f"[推荐生成] 开始生成推荐，count={count}")
        logger.debug(f"[推荐生成] AI原始回复长度: {len(ai_response)}, 内容前100字: {ai_response[:100]}...")
        
        if not self.current_model:
            logger.warning("[推荐生成] 无当前模型，跳过生成")
            return []
        
        logger.info(f"[推荐生成] 使用模型: {self.current_model}")
        
        try:
            # 先过滤掉深度思考内容，只使用实际回复
            filtered_response = filter_think_content(ai_response)
            logger.debug(f"[推荐生成] 过滤后回复长度: {len(filtered_response) if filtered_response else 0}")
            
            if not filtered_response:
                logger.warning("[推荐生成] 过滤后回复为空，跳过生成")
                return []
            
            # 简化的 prompt，要求更快速的响应
            prompt = f"""根据 AI 的回复，生成 {count} 个简短的用户回复选项。
要求：每个选项 10-15 字，自然流畅，只返回选项文本（每行一个，不要编号）。

AI 回复：{filtered_response[:200]}

用户回复选项："""
            
            logger.debug(f"[推荐生成] 请求 prompt:\n{prompt}")
            
            request_body = {
                "model": self.current_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 80,
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            logger.info(f"[推荐生成] 发送请求到 {self.base_url}/api/generate")
            logger.debug(f"[推荐生成] 请求参数: model={self.current_model}, temperature=0.8, num_predict=80")
            
            # 调用 Ollama API，使用更短的超时时间
            api_start = time.time()
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_body,
                timeout=15
            )
            api_elapsed = time.time() - api_start
            logger.info(f"[推荐生成] API 响应: status={response.status_code}, 耗时={api_elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                suggestions_text = data.get('response', '').strip()
                logger.debug(f"[推荐生成] LLM 原始返回:\n{suggestions_text}")
                
                # 先过滤掉可能的深度思考内容
                suggestions_text = filter_think_content(suggestions_text)
                logger.debug(f"[推荐生成] 过滤思考内容后:\n{suggestions_text}")
                
                # 解析返回的选项
                suggestions = []
                for line in suggestions_text.split('\n'):
                    line = line.strip()
                    # 移除可能的编号
                    if line and len(line) > 2:
                        # 移除开头的数字、点、括号等
                        import re
                        cleaned = re.sub(r'^[\d\.\)\]】\-\*]+\s*', '', line)
                        if cleaned and len(cleaned) <= 50:
                            suggestions.append(cleaned)
                            logger.debug(f"[推荐生成] 解析到选项: {cleaned}")
                        else:
                            logger.debug(f"[推荐生成] 跳过选项(过长或为空): {cleaned[:30] if cleaned else '空'}...")
                
                result = suggestions[:count]
                total_elapsed = time.time() - start_time
                logger.info(f"[推荐生成] 完成，生成 {len(result)} 个推荐，总耗时={total_elapsed:.2f}s")
                logger.info(f"[推荐生成] 最终结果: {result}")
                return result
            else:
                logger.error(f"[推荐生成] API 返回错误: status={response.status_code}, body={response.text[:200]}")
            
            return []
        
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            logger.warning(f"[推荐生成] 请求超时(15s)，已耗时={elapsed:.2f}s")
            return []
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[推荐生成] 生成失败: {e}, 已耗时={elapsed:.2f}s")
            import traceback
            logger.debug(f"[推荐生成] 异常堆栈:\n{traceback.format_exc()}")
            return []
