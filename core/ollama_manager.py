"""Ollama 服务管理"""

import subprocess
import requests
import time
import os
import sys
import logging

logger = logging.getLogger(__name__)


class OllamaManager:
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.process = None
        self.ollama_path = self._find_ollama()
        
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _find_ollama(self):
        """查找 Ollama 可执行文件"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        embedded_path = os.path.join(base_dir, "runtime", "ollama", "ollama.exe")
        if os.path.exists(embedded_path):
            return embedded_path
        
        try:
            result = subprocess.run(
                ["where", "ollama"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return "ollama"
        except:
            pass
        
        return None
    
    def is_installed(self):
        """检查 Ollama 是否可用"""
        return self.ollama_path is not None
    
    def is_running(self):
        """检查 Ollama 服务是否运行"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def start_service(self):
        """启动 Ollama 服务"""
        if not self.ollama_path:
            return False, "Ollama 未找到"
        
        if self.is_running():
            return True, "服务已在运行"
        
        try:
            env = os.environ.copy()
            models_dir = os.path.join(self.base_dir, "ollama_models")
            os.makedirs(models_dir, exist_ok=True)
            env["OLLAMA_MODELS"] = models_dir
            
            self.process = subprocess.Popen(
                [self.ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            for i in range(30):
                if self.is_running():
                    return True, "服务启动成功"
                time.sleep(1)
            
            return False, "服务启动超时"
        except Exception as e:
            return False, f"启动失败: {e}"
    
    def stop_service(self):
        """停止 Ollama 服务"""
        if self.process:
            self.process.terminate()
            self.process = None
            return True
        return False
    
    def list_models(self):
        """获取已安装的模型列表"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = []
                for m in data.get("models", []):
                    size_bytes = m.get("size", 0)
                    size_gb = size_bytes / (1024**3)
                    models.append({
                        "name": m.get("name", ""),
                        "size": f"{size_gb:.2f} GB",
                        "modified": m.get("modified_at", "")
                    })
                return models
        except:
            pass
        return []
    
    def delete_model(self, model_name):
        """从 Ollama 中删除模型"""
        try:
            logger.info(f"从 Ollama 删除模型: {model_name}")
            response = requests.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=60
            )
            success = response.status_code == 200
            if success:
                logger.info(f"Ollama 模型删除成功: {model_name}")
            else:
                logger.warning(f"Ollama 模型删除失败: {model_name}, 状态码: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"删除 Ollama 模型异常: {e}")
            return False
    
    def create_model_from_gguf(self, model_name, gguf_path, progress_callback=None):
        """从 GGUF 文件创建 Ollama 模型"""
        if not self.ollama_path:
            if progress_callback:
                progress_callback("错误: Ollama 未找到")
            return False
        
        if not os.path.exists(gguf_path):
            if progress_callback:
                progress_callback(f"错误: GGUF 文件不存在\n{gguf_path}")
            return False
        
        gguf_path = os.path.abspath(gguf_path)
        
        if progress_callback:
            progress_callback(f"GGUF 文件: {gguf_path}")
        
        # Modelfile 保存到 gguf 文件所在目录
        gguf_dir = os.path.dirname(gguf_path)
        modelfile_path = os.path.join(gguf_dir, f"Modelfile_{model_name}")
        
        # 根据模型名称选择合适的模板
        model_name_lower = model_name.lower()
        
        if 'llama' in model_name_lower:
            # Llama 3 模型格式
            modelfile_content = f'''FROM "{gguf_path}"

TEMPLATE """{{{{- if .System }}}}<|start_header_id|>system<|end_header_id|>

{{{{ .System }}}}<|eot_id|>{{{{- end }}}}<|start_header_id|>user<|end_header_id|>

{{{{ .Prompt }}}}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"
PARAMETER temperature 0.7
PARAMETER top_p 0.9
'''
        else:
            # Qwen/DeepSeek 等使用 ChatML 格式
            modelfile_content = f'''FROM "{gguf_path}"

TEMPLATE """{{{{- if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{- end }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
"""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0.7
PARAMETER top_p 0.9
'''
        
        try:
            if progress_callback:
                progress_callback("创建 Modelfile...")
            
            with open(modelfile_path, "w", encoding="utf-8") as f:
                f.write(modelfile_content)
            
            if progress_callback:
                progress_callback(f"执行: ollama create {model_name}")
            
            env = os.environ.copy()
            models_dir = os.path.join(self.base_dir, "ollama_models")
            os.makedirs(models_dir, exist_ok=True)
            env["OLLAMA_MODELS"] = models_dir
            
            if progress_callback:
                progress_callback("正在创建模型，请稍候...")
            
            process = subprocess.Popen(
                [self.ollama_path, "create", model_name, "-f", modelfile_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=self.base_dir,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            stdout_data, stderr_data = process.communicate(timeout=600)
            
            def safe_decode(data):
                if not data:
                    return ""
                for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                    try:
                        return data.decode(encoding)
                    except:
                        continue
                return data.decode('utf-8', errors='ignore')
            
            stdout_text = safe_decode(stdout_data)
            stderr_text = safe_decode(stderr_data)
            
            if stdout_text.strip():
                if progress_callback:
                    progress_callback(f"输出: {stdout_text.strip()}")
            
            if stderr_text.strip():
                if progress_callback:
                    progress_callback(f"信息: {stderr_text.strip()}")
            
            if os.path.exists(modelfile_path):
                os.remove(modelfile_path)
                if progress_callback:
                    progress_callback(f"已清理 Modelfile: {modelfile_path}")
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback("✅ 模型创建成功!")
                return True
            else:
                if progress_callback:
                    progress_callback(f"❌ 创建失败，返回码: {process.returncode}")
                return False
        
        except subprocess.TimeoutExpired:
            if progress_callback:
                progress_callback("❌ 创建超时")
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ 异常: {e}")
            return False
        finally:
            if os.path.exists(modelfile_path):
                try:
                    os.remove(modelfile_path)
                    if progress_callback:
                        progress_callback(f"已清理 Modelfile: {modelfile_path}")
                except Exception as del_err:
                    if progress_callback:
                        progress_callback(f"清理 Modelfile 失败: {del_err}")