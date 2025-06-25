import asyncio
import logging
from services.hourly_stats_service import HourlyStatsService
from services.alert_service import AlertService

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
    
    
    logger.info("Services initialized successfully")

