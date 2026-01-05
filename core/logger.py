"""日志系统模块

统一的日志配置，将日志输出到文件和控制台
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name='app', level=logging.DEBUG):
    """配置日志系统
    
    Args:
        name: 日志记录器名称
        level: 日志级别
    
    Returns:
        配置好的 logger 对象
    """
    # 确定日志目录（exe 所在目录）
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 创建 logs 目录
    log_folder = os.path.join(log_dir, 'logs')
    os.makedirs(log_folder, exist_ok=True)
    
    # 日志文件名（按日期）
    log_filename = datetime.now().strftime('app_%Y%m%d.log')
    log_filepath = os.path.join(log_folder, log_filename)
    
    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 文件处理器（带轮转，单个文件最大 10MB，保留 5 个备份）
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 记录启动信息
    logger.info("=" * 60)
    logger.info(f"日志系统已启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"日志文件: {log_filepath}")
    logger.info(f"运行模式: {'打包模式 (exe)' if getattr(sys, 'frozen', False) else '开发模式'}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info("=" * 60)
    
    return logger


def log_exception(logger, exc_info=True):
    """记录异常信息的装饰器
    
    Args:
        logger: logger 对象
        exc_info: 是否记录异常堆栈
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"函数 {func.__name__} 执行失败: {e}",
                    exc_info=exc_info
                )
                raise
        return wrapper
    return decorator


# 全局 logger 实例缓存
_loggers = {}


def get_logger(name='app'):
    """获取 logger 实例
    
    Args:
        name: logger 名称
    
    Returns:
        logger 对象
    """
    global _loggers
    if name not in _loggers:
        _loggers[name] = setup_logger(name)
    return _loggers[name]


if __name__ == '__main__':
    # 测试日志系统
    logger = get_logger()
    logger.debug("这是 DEBUG 级别日志")
    logger.info("这是 INFO 级别日志")
    logger.warning("这是 WARNING 级别日志")
    logger.error("这是 ERROR 级别日志")
    
    try:
        1 / 0
    except Exception as e:
        logger.exception("捕获到异常")
