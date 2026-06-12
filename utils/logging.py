# utils/logging.py

"""
loguru 日志配置
开发环境：标准输出彩色 + 文件滚动 + 错误日志分离
"""

from loguru import logger
import sys


def configure_loguru(level='DEBUG'):
    """配置 loguru 日志（在 settings 就绪后调用）"""

    # 清除默认 handler
    logger.remove()

    # 标准输出：彩色友好，用于开发调试
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )

    # 文件滚动：按日期分片，保留30天
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        compression="gz"
    )

    # 错误日志单独记录，保留90天
    logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        compression="gz"
    )

    return logger