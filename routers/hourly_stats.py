from fastapi import APIRouter, HTTPException
import logging
from typing import List

from services.hourly_stats_service import HourlyStatsService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["统计数据"])

@router.get("/hourly-data-volume")
async def get_hourly_data_volume():
    """
    获取每小时数据提取量
    返回过去24小时内每3小时的数据提取量
    """
    try:
        # 使用HourlyStatsService获取数据
        hourly_data = await HourlyStatsService.get_hourly_data_volume()
        
        return {
            "code": 200,
            "message": "获取每小时数据提取量成功",
            "data": hourly_data
        }
    except Exception as e:
        logger.error(f"Error in get_hourly_data_volume: {e}")
        return {
            "code": 500,
            "message": f"获取数据失败: {str(e)}",
            "data": []
        }