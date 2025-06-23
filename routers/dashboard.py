from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import random
from datetime import datetime, timedelta
import json
import os
import logging

# 导入服务
from services.hourly_stats_service import HourlyStatsService
from services.alert_service import AlertService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["数据分析仪表盘"])

@router.get("/visit-statistics")
async def get_visit_statistics():
    """
    获取访问统计数据，用于饼图展示
    返回不同来源的访问统计
    """
    try:
        # 从auto_analysis_cache.json读取数据
        cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "auto_analysis_cache.json")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 转换数据格式为[{"name": "分类名", "value": 数量}]
                visit_data = []
                
                if "result" in cache_data and isinstance(cache_data["result"], list):
                    for category in cache_data["result"]:
                        if "name" in category and "count" in category:
                            visit_data.append({
                                "name": category["name"],
                                "value": category["count"]
                            })
            except Exception as e:
                logger.error(f"Error reading cache file: {e}")
        
        return {
            "code": 200,
            "message": "获取访问统计数据成功",
            "data": visit_data
        }
    except Exception as e:
        logger.error(f"Error in get_visit_statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_alert_messages():
    """
    获取系统告警信息
    返回最近的告警消息列表
    """
    try:
        # 使用AlertService获取告警信息
        alerts = await AlertService.get_alerts()
        
        return {
            "code": 200,
            "message": "获取告警信息成功",
            "data": alerts
        }
    except Exception as e:
        logger.error(f"Error in get_alert_messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))



