import asyncio
import logging
from services.hourly_stats_service import HourlyStatsService
from services.alert_service import AlertService
from services.directory_monitor_service import start_directory_monitoring, stop_directory_monitoring

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_services():
    """初始化所有服务"""
    logger.info("Initializing services...")

    # 初始化HourlyStatsService
    await HourlyStatsService.initialize()

    # 初始化AlertService
    await AlertService.initialize()

    # 初始化目录监听服务
    try:
        # 可以从配置文件或环境变量读取监听目录
        monitor_dirs = ["D:\\pdf"]  # 默认监听目录
        await start_directory_monitoring(monitor_dirs)
        logger.info("Directory monitoring service started successfully")
    except Exception as e:
        logger.error(f"Failed to start directory monitoring service: {e}")

    logger.info("Services initialized successfully")

async def cleanup_services():
    """清理所有服务"""
    logger.info("Cleaning up services...")

    # 停止目录监听服务
    try:
        await stop_directory_monitoring()
        logger.info("Directory monitoring service stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop directory monitoring service: {e}")

    logger.info("Services cleanup completed")

