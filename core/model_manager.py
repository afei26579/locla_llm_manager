"""模型下载管理"""

import os
import sys
import json
import re
from datetime import datetime

from .database import get_database
from .logger import get_logger

# 使用统一的日志系统
logger = get_logger('model_manager')


class ModelManager:
    # 量化版本的比特数映射（每个参数占用的比特数）
    QUANTIZATION_BITS = {
        'f16': 16.0,
        'f32': 32.0,
        'q2_k': 2.5,
        'q3_k_s': 3.0,
        'q3_k_m': 3.5,
        'q3_k_l': 3.75,
        'q4_0': 4.5,
        'q4_1': 5.0,
        'q4_k_s': 4.5,
        'q4_k_m': 5.0,
        'q5_0': 5.5,
        'q5_1': 6.0,
        'q5_k_s': 5.5,
        'q5_k_m': 6.0,
        'q6_k': 6.5,
        'q8_0': 8.5,
        'q8_1': 9.0,
    }
    
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.models_dir = os.path.join(self.base_dir, "models")
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.db = get_database()
        self.models_config = self._load_models_config()
        
        logger.info(f"ModelManager 初始化完成，模型目录: {self.models_dir}")
    
    # ==================== 下载记录管理（使用数据库）====================
    
    def add_download_record(self, model_name: str, ollama_name: str, gguf_path: str, 
                        quantization: str = '', model_id: str = ''):
        """添加下载记录（使用 模型名-量化版本 作为唯一 key）"""
        # 生成唯一 key
        record_key = self.generate_record_key(model_name, quantization)
        
        self.db.add_download_record(
            record_key=record_key,
            model_name=model_name,
            ollama_name=ollama_name,
            gguf_path=gguf_path,
            quantization=quantization,
            model_id=model_id
        )
        
        logger.info(f"添加下载记录: {record_key} -> ollama: {ollama_name}, gguf: {gguf_path}")

    def get_download_record(self, name: str):
        """获取下载记录"""
        return self.db.find_download_record(name)

    def remove_download_record(self, name: str):
        """删除下载记录"""
        record = self.get_download_record(name)
        if not record:
            return False
        
        record_key = record.get('record_key', '')
        if record_key:
            self.db.delete_download_record(record_key)
            logger.info(f"删除下载记录: {record_key}")
            return True
        
        return False
    
    def get_gguf_path_by_name(self, name: str):
        """根据模型名获取 GGUF 文件路径"""
        record = self.get_download_record(name)
        if record:
            return record.get('gguf_path')
        return None
    
    def list_download_records(self):
        """列出所有下载记录"""
        return self.db.list_download_records()
    
    # ==================== 模型配置管理 ====================
    
    def _load_models_config(self):
        """从数据库加载模型配置"""
        from .database import get_database
        
        try:
            db = get_database()
            config = db.list_models()
            
            if config:
                logger.info(f"成功从数据库加载模型配置")
                return config
            else:
                logger.warning("数据库中没有模型配置，使用默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"从数据库加载模型配置失败: {e}")
            return self._get_default_config()
    
    def _save_models_config(self, config):
        """保存模型配置到数据库"""
        from .database import get_database
        
        try:
            db = get_database()
            
            # 遍历配置并保存到数据库
            for category, subcategories in config.items():
                for subcategory, models in subcategories.items():
                    for model in models:
                        db.add_model(
                            model_id=model['id'],
                            category=category,
                            subcategory=subcategory,
                            name=model['name'],
                            params=model['params'],
                            params_b=model['params_b'],
                            ctx=model['ctx'],
                            lang=model['lang'],
                            distilled=model['distilled'],
                            quantizations=model['quantizations'],
                            file_pattern=model['file_pattern']
                        )
            logger.info("模型配置已保存到数据库")
        except Exception as e:
            logger.error(f"保存模型配置到数据库失败: {e}")
    
    def _get_default_config(self):
        return {"text": {}, "coder": {}, "ocr": {}, "image": {}, "video": {}, "audio": {}}
    
    def get_all_categories(self):
        return list(self.models_config.keys())
    
    def get_category_families(self, category):
        if category in self.models_config:
            return list(self.models_config[category].keys())
        return []
    
    def get_models_by_category(self, category):
        models = []
        if category in self.models_config:
            for family, family_models in self.models_config[category].items():
                for model in family_models:
                    model_copy = model.copy()
                    model_copy['family'] = family
                    model_copy['category'] = category
                    models.append(model_copy)
        return models
    
    def get_all_models_flat(self):
        all_models = []
        for category in self.models_config:
            all_models.extend(self.get_models_by_category(category))
        return all_models
    
    def get_model_by_name(self, model_name):
        for category in self.models_config:
            for family, models in self.models_config[category].items():
                for model in models:
                    if model.get('name') == model_name:
                        model_copy = model.copy()
                        model_copy['family'] = family
                        model_copy['category'] = category
                        return model_copy
        return None
    
    def get_recommended_models(self):
        recommended = {}
        for model in self.get_all_models_flat():
            name = model.get('name', '')
            if name:
                quantizations = model.get('quantizations', [])
                default_quant = self._get_default_quantization(quantizations)
                params_b = model.get('params_b', 1.0)
                
                # 计算每个量化版本的大小
                quant_details = {}
                for quant in quantizations:
                    size_gb = self.estimate_model_size_gb(params_b, quant)
                    vram_gb = self.estimate_vram_usage_gb(params_b, quant)
                    quant_details[quant] = {
                        'size_gb': round(size_gb, 1),
                        'vram_gb': round(vram_gb, 1),
                        'bits': self.QUANTIZATION_BITS.get(quant.lower(), 4.5)
                    }
                
                recommended[name] = {
                    "model_id": model.get('id', ''),
                    "file_pattern": model.get('file_pattern', ''),
                    "default_quant": default_quant,
                    "size": f"{params_b * 0.5:.1f} GB",  # 保留旧的估算（向后兼容）
                    "vram": f"{params_b * 0.6:.1f} GB",  # 保留旧的估算（向后兼容）
                    "description": self._generate_description(model),
                    "quantizations": quantizations,
                    "quant_details": quant_details,  # 新增：详细的量化信息
                    "params": model.get('params', ''),
                    "params_b": params_b,
                    "ctx": model.get('ctx', 0),
                    "lang": model.get('lang', []),
                    "category": model.get('category', ''),
                    "family": model.get('family', '')
                }
        return recommended
    
    def _get_default_quantization(self, quantizations):
        if not quantizations:
            return 'Q4_K_M'
        preferred = ['Q4_K_M', 'q4_K_M', 'Q4_0', 'q4_0', 'Q5_K_M', 'q5_K_M', 'Q8_0', 'q8_0']
        for pref in preferred:
            for q in quantizations:
                if q.lower() == pref.lower():
                    return q
        return quantizations[0]
    
    def _generate_description(self, model):
        parts = []
        family = model.get('family', '').upper()
        if family:
            parts.append(family)
        params = model.get('params', '')
        if params:
            parts.append(f"{params} 参数")
        lang = model.get('lang', [])
        if 'zh' in lang and 'en' in lang:
            parts.append("中英双语")
        elif 'zh' in lang:
            parts.append("中文")
        elif 'en' in lang:
            parts.append("英文")
        if model.get('distilled'):
            parts.append("蒸馏版")
        return '，'.join(parts) if parts else '大语言模型'
    
    def get_gguf_filename(self, model_name, quantization):
        model_info = self.get_model_by_name(model_name)
        if not model_info:
            return None
        file_pattern = model_info.get('file_pattern', '')
        if not file_pattern:
            return None
        return file_pattern.replace('{quant}', quantization)
    
    def generate_ollama_name(self, model_name: str, quantization: str = '') -> str:
        """生成 Ollama 模型名称（包含 :latest 标签）
        
        例如：Qwen3-0.6B-q8_0:latest
        """
        clean_name = model_name.replace(' ', '-')
        
        if quantization:
            name = f"{clean_name}-{quantization}"
        else:
            name = clean_name
        
        # Ollama 会自动添加 :latest 标签，这里直接包含
        return f"{name}:latest"
        
    def generate_record_key(self, model_name: str, quantization: str) -> str:
        """生成下载记录的唯一 key（模型名-量化版本，小写）
        
        例如：qwen2.5-coder-0.5b-instruct-q4_K_M
        """
        # 使用小写，保留原始格式确保唯一性
        key = f"{model_name}-{quantization}".lower()
        return key
    def download_model(self, model_name, progress_callback=None, quantization=None):
        """从 ModelScope 下载模型，使用自定义进度回调"""
        logger.info(f"========== 开始下载模型 ==========")
        logger.info(f"[下载] 模型名: {model_name}, 量化版本: {quantization}")
        
        model_info = self.get_model_by_name(model_name)
        if not model_info:
            logger.error(f"[下载] 模型不存在: {model_name}")
            return None, None, f"模型不存在: {model_name}"
        
        model_id = model_info.get('id', '')
        quantizations = model_info.get('quantizations', [])
        logger.info(f"[下载] ModelID: {model_id}, 可用量化版本: {quantizations}")
        
        if quantization is None:
            quantization = self._get_default_quantization(quantizations)
            logger.info(f"[下载] 使用默认量化版本: {quantization}")
        else:
            matched = None
            for q in quantizations:
                if q.lower() == quantization.lower():
                    matched = q
                    break
            if not matched:
                logger.error(f"[下载] 不支持的量化版本: {quantization}")
                return None, None, f"不支持的量化版本: {quantization}"
            quantization = matched
        
        filename = self.get_gguf_filename(model_name, quantization)
        if not filename:
            logger.error(f"[下载] 无法确定文件名")
            return None, None, "无法确定文件名"
        
        ollama_name = self.generate_ollama_name(model_name, quantization)
        logger.info(f"[下载] 目标文件: {filename}, Ollama名称: {ollama_name}")
        
        if progress_callback:
            progress_callback(5, f"准备下载 {model_name} ({quantization})...")
        
        # 检查本地是否已存在
        local_dir = os.path.join(self.models_dir, model_id.replace('/', '_'))
        existing_path = self._find_gguf_file(local_dir, filename) if os.path.exists(local_dir) else None
        
        if existing_path and os.path.exists(existing_path):
            file_size = os.path.getsize(existing_path) / (1024 * 1024)
            logger.info(f"[下载] 文件已存在: {existing_path} ({file_size:.1f} MB)")
            if progress_callback:
                progress_callback(100, "文件已存在，跳过下载")
            
            self.add_download_record(model_name, ollama_name, existing_path, quantization, model_id)
            return existing_path, ollama_name, None
        
        # 尝试使用 modelscope 下载
        try:
            if progress_callback:
                progress_callback(10, f"连接 ModelScope...")
            
            logger.info(f"[下载] 开始从 ModelScope 下载...")
            gguf_path = self._download_with_progress(model_id, filename, local_dir, progress_callback)
            
            if gguf_path and os.path.exists(gguf_path):
                file_size = os.path.getsize(gguf_path) / (1024 * 1024)
                logger.info(f"[下载] 下载成功: {gguf_path} ({file_size:.1f} MB)")
                self.add_download_record(model_name, ollama_name, gguf_path, quantization, model_id)
                if progress_callback:
                    progress_callback(100, "下载完成!")
                logger.info(f"========== 下载完成 ==========")
                return gguf_path, ollama_name, None
            else:
                logger.error(f"[下载] 下载完成但未找到文件: {filename}")
                return None, None, f"下载完成但未找到文件: {filename}"
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[下载] 下载异常: {error_msg}")
            
            if "symbolic link" in error_msg.lower() or "symlink" in error_msg.lower():
                logger.info(f"[下载] 检测到符号链接问题，尝试 HTTP 直接下载...")
                if progress_callback:
                    progress_callback(15, "尝试备用下载方式...")
                return self._download_http(model_id, filename, model_name, quantization, ollama_name, progress_callback)
            
            return None, None, f"下载失败: {e}"
    
    def _download_with_progress(self, model_id, filename, local_dir, progress_callback):
        """使用 modelscope 下载，并监控进度"""
        import threading
        import time
        import sys
        import io
        
        logger.info(f"[下载] 开始下载: model_id={model_id}, filename={filename}, local_dir={local_dir}")
        
        result = {'path': None, 'error': None, 'done': False}
        
        def do_download():
            try:
                # 打包后 sys.stdout 可能为 None，需要处理
                if sys.stdout is None:
                    sys.stdout = io.StringIO()
                if sys.stderr is None:
                    sys.stderr = io.StringIO()
                
                from modelscope import snapshot_download
                
                logger.info(f"[下载] 调用 snapshot_download...")
                
                model_dir = snapshot_download(
                    model_id=model_id,
                    allow_patterns=filename,
                    local_dir=local_dir
                )
                
                result['path'] = self._find_gguf_file(model_dir, filename)
                logger.info(f"[下载] snapshot_download 完成，文件路径: {result['path']}")
            except Exception as e:
                logger.error(f"[下载] 下载异常: {e}")
                result['error'] = e
            finally:
                result['done'] = True
        
        # 启动下载线程
        download_thread = threading.Thread(target=do_download)
        download_thread.start()
        
        # 监控进度（通过文件大小估算）
        last_size = 0
        check_count = 0
        while not result['done']:
            time.sleep(1)
            check_count += 1
            
            current_size = self._get_download_size(local_dir, filename)
            if current_size > 0 and current_size != last_size:
                size_mb = current_size / (1024 * 1024)
                # 使用文件大小估算进度
                estimated_percent = min(15 + int(size_mb / 50), 90)
                
                logger.debug(f"[下载] 文件大小监控: {size_mb:.1f} MB, 估算进度: {estimated_percent}%")
                
                if progress_callback:
                    progress_callback(estimated_percent, f"下载中: {size_mb:.1f} MB...")
                last_size = current_size
            elif check_count % 10 == 0:
                logger.debug(f"[下载] 等待中... (检查次数: {check_count})")
                if progress_callback and check_count <= 30:
                    progress_callback(15, "正在下载...")
        
        download_thread.join()
        
        if result['error']:
            logger.error(f"[下载] 最终错误: {result['error']}")
            raise result['error']
        
        logger.info(f"[下载] 下载完成，返回路径: {result['path']}")
        return result['path']
    
    def _get_download_size(self, local_dir, filename):
        """获取正在下载的文件大小"""
        if not os.path.exists(local_dir):
            return 0
        
        total_size = 0
        for root, dirs, files in os.walk(local_dir):
            for f in files:
                if f.endswith('.gguf') or f.endswith('.tmp') or filename.lower() in f.lower():
                    try:
                        total_size += os.path.getsize(os.path.join(root, f))
                    except:
                        pass
        return total_size
    
    def _download_http(self, model_id, filename, model_name, quantization, ollama_name, progress_callback=None):
        """HTTP 直接下载（带进度）"""
        try:
            import requests
            
            if progress_callback:
                progress_callback(10, "获取下载链接...")
            
            url = f"https://modelscope.cn/models/{model_id}/resolve/master/{filename}"
            logger.info(f"HTTP 下载 URL: {url}")
            
            safe_model_id = model_id.replace("/", "_")
            target_dir = os.path.join(self.models_dir, safe_model_id)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)
            
            if os.path.exists(target_path):
                self.add_download_record(model_name, ollama_name, target_path, quantization, model_id)
                if progress_callback:
                    progress_callback(100, "文件已存在")
                return target_path, ollama_name, None
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            temp_path = target_path + ".tmp"
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            percent = int((downloaded / total_size) * 100)
                            downloaded_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            progress_callback(percent, f"下载中: {downloaded_mb:.1f}/{total_mb:.1f} MB ({percent}%)")
            
            os.rename(temp_path, target_path)
            
            self.add_download_record(model_name, ollama_name, target_path, quantization, model_id)
            
            if progress_callback:
                progress_callback(100, "下载完成!")
            
            return target_path, ollama_name, None
        
        except Exception as e:
            logger.error(f"HTTP 下载失败: {e}")
            return None, None, f"下载失败: {e}"
    
    def _find_gguf_file(self, model_dir, filename):
        """在下载目录中查找 GGUF 文件"""
        if not os.path.exists(model_dir):
            return None
        
        direct_path = os.path.join(model_dir, filename)
        if os.path.exists(direct_path):
            return direct_path
        
        for root, dirs, files in os.walk(model_dir):
            for f in files:
                if f == filename or f.lower() == filename.lower():
                    return os.path.join(root, f)
        
        for root, dirs, files in os.walk(model_dir):
            for f in files:
                if f.endswith('.gguf'):
                    return os.path.join(root, f)
        
        return None
    
    def delete_model_files(self, name: str) -> tuple:
        """删除模型相关文件（包括整个模型目录）"""
        import shutil
        
        record = self.get_download_record(name)
        
        if record:
            gguf_path = record.get('gguf_path', '')
            if gguf_path:
                # 获取模型目录（gguf 文件的父目录）
                model_dir = os.path.dirname(gguf_path)
                
                # 确保目录在 models 目录下，防止误删
                if model_dir and self.models_dir in model_dir and os.path.exists(model_dir):
                    try:
                        # 删除整个模型目录
                        shutil.rmtree(model_dir)
                        logger.info(f"成功删除模型目录: {model_dir}")
                        self.remove_download_record(name)
                        return True, model_dir
                    except Exception as e:
                        logger.error(f"删除模型目录失败: {e}")
                        # 尝试只删除 gguf 文件
                        try:
                            if os.path.exists(gguf_path):
                                os.remove(gguf_path)
                                logger.info(f"回退：成功删除 GGUF 文件: {gguf_path}")
                                self.remove_download_record(name)
                                return True, gguf_path
                        except:
                            pass
                        return False, model_dir
                elif gguf_path and os.path.exists(gguf_path):
                    # 如果目录不在 models 下，只删除 gguf 文件
                    try:
                        os.remove(gguf_path)
                        logger.info(f"成功删除 GGUF 文件: {gguf_path}")
                        self.remove_download_record(name)
                        return True, gguf_path
                    except Exception as e:
                        logger.error(f"删除 GGUF 文件失败: {e}")
                        return False, gguf_path
                else:
                    self.remove_download_record(name)
                    return True, gguf_path
            else:
                self.remove_download_record(name)
                return True, None
        
        return False, None
    
    def get_local_gguf_files(self):
        gguf_files = []
        for root, dirs, files in os.walk(self.models_dir):
            for f in files:
                if f.endswith(".gguf"):
                    path = os.path.join(root, f)
                    size_bytes = os.path.getsize(path)
                    gguf_files.append({
                        "name": f,
                        "path": path,
                        "size": f"{size_bytes / (1024**3):.2f} GB"
                    })
        return gguf_files
    
    def reload_config(self):
        """重新加载配置"""
        self.models_config = self._load_models_config()
    
    def get_recommended_models_for_hardware(self, vram_gb: float = 0, ram_gb: float = 16):
        all_models = self.get_recommended_models()
        max_params = self._calculate_max_params(vram_gb, ram_gb)
        return {k: v for k, v in all_models.items() if v.get('params_b', 1.0) <= max_params}
    
    def estimate_model_size_gb(self, params_b: float, quantization: str) -> float:
        """估算模型文件大小（GB）
        
        Args:
            params_b: 模型参数量（单位：十亿）
            quantization: 量化版本（如 q4_k_m, q8_0）
        
        Returns:
            估算的文件大小（GB）
        """
        quant_lower = quantization.lower()
        
        # 获取每个参数的比特数
        bits_per_param = self.QUANTIZATION_BITS.get(quant_lower, 4.5)  # 默认 4.5 bits
        
        # 计算：参数量(B) * bits_per_param / 8(bits->bytes) / 1024^3(bytes->GB)
        # 简化：params_b * bits_per_param / 8
        size_gb = params_b * bits_per_param / 8.0
        
        # 添加一些开销（元数据、对齐等），约 5%
        size_gb *= 1.05
        
        return size_gb
    
    def estimate_vram_usage_gb(self, params_b: float, quantization: str) -> float:
        """估算运行时显存占用（GB）
        
        Args:
            params_b: 模型参数量（单位：十亿）
            quantization: 量化版本
        
        Returns:
            估算的显存占用（GB）
        """
        # 模型文件大小
        model_size = self.estimate_model_size_gb(params_b, quantization)
        
        # 运行时需要额外的显存用于：
        # - KV cache
        # - 激活值
        # - 临时缓冲区
        # 通常是模型大小的 1.2-1.5 倍
        vram_usage = model_size * 1.3
        
        return vram_usage
    
    def get_suitable_quantizations(self, params_b: float, available_vram_gb: float, 
                                   all_quantizations: list) -> list:
        """根据显存大小筛选合适的量化版本
        
        Args:
            params_b: 模型参数量（单位：十亿）
            available_vram_gb: 可用显存（GB）
            all_quantizations: 所有可用的量化版本列表
        
        Returns:
            合适的量化版本列表（按推荐程度排序）
        """
        suitable = []
        
        for quant in all_quantizations:
            vram_needed = self.estimate_vram_usage_gb(params_b, quant)
            
            # 保留 10% 的显存余量
            if vram_needed <= available_vram_gb * 0.9:
                size_gb = self.estimate_model_size_gb(params_b, quant)
                suitable.append({
                    'quantization': quant,
                    'size_gb': size_gb,
                    'vram_gb': vram_needed,
                    'bits': self.QUANTIZATION_BITS.get(quant.lower(), 4.5)
                })
        
        # 按质量（bits）降序排序，优先推荐高质量版本
        suitable.sort(key=lambda x: x['bits'], reverse=True)
        
        return suitable
    
    def get_recommended_quantization(self, params_b: float, available_vram_gb: float,
                                    all_quantizations: list) -> str:
        """获取推荐的量化版本
        
        Args:
            params_b: 模型参数量（单位：十亿）
            available_vram_gb: 可用显存（GB）
            all_quantizations: 所有可用的量化版本列表
        
        Returns:
            推荐的量化版本，如果都不合适则返回最小的
        """
        suitable = self.get_suitable_quantizations(params_b, available_vram_gb, all_quantizations)
        
        if suitable:
            # 返回质量最高的合适版本
            return suitable[0]['quantization']
        
        # 如果都不合适，返回最小的量化版本
        if all_quantizations:
            min_quant = min(all_quantizations, 
                          key=lambda q: self.QUANTIZATION_BITS.get(q.lower(), 4.5))
            return min_quant
        
        return 'q4_k_m'  # 默认值
    
    def _calculate_max_params(self, vram_gb: float, ram_gb: float) -> float:
        if vram_gb >= 24: return 70
        elif vram_gb >= 16: return 32
        elif vram_gb >= 12: return 14
        elif vram_gb >= 8: return 8
        elif vram_gb >= 6: return 7
        elif vram_gb >= 4: return 3
        elif vram_gb > 0: return 1.7
        elif ram_gb >= 32: return 8
        elif ram_gb >= 16: return 4
        elif ram_gb >= 8: return 1.7
        else: return 0.6
    
    @property
    def RECOMMENDED_MODELS(self):
        return self.get_recommended_models()