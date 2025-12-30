import subprocess
import platform
import os
import psutil

def detect_hardware():
    """检测硬件信息"""
    info = {
        "操作系统": f"{platform.system()} {platform.release()}",
        "处理器": platform.processor(),
        "内存": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
        "GPU型号": None,
        "GPU显存": None,
        "GPU可用": False
    }
    
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                parts = output.split(", ")
                info["GPU型号"] = parts[0]
                info["GPU显存"] = parts[1] if len(parts) > 1 else "未知"
                info["GPU可用"] = True
    except Exception:
        info["GPU型号"] = "未检测到 NVIDIA GPU"
    
    return info

def get_recommended_models(gpu_memory_gb):
    """根据显存推荐模型"""
    if gpu_memory_gb >= 8:
        return ["Qwen2.5-7B-Q8", "Qwen2.5-7B-Q4", "Llama3-8B-Q4"]
    elif gpu_memory_gb >= 6:
        return ["Qwen2.5-7B-Q4", "Qwen2.5-3B-Q4", "Llama3-8B-Q4"]
    elif gpu_memory_gb >= 4:
        return ["Qwen2.5-3B-Q4", "Qwen2-1.5B-Q4"]
    else:
        return ["Qwen2-1.5B-Q4"]