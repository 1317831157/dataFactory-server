import os
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time

# 导入ResourceService以使用其auto_analyze_local_directories方法
from services.resource_service import ResourceService
from services.database import Task

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HourlyStatsService:
    """每小时数据统计服务"""
    
    # 存储每小时统计数据的类变量
    _hourly_stats = []
    _last_update_time = None
    _update_interval = timedelta(hours=3)  # 每3小时更新一次
    _is_updating = False
    _max_data_points = 8  # 保存最近8个数据点（对应24小时，每3小时一个点）
    
    
    @staticmethod
    async def initialize():
        """初始化服务，加载保存的统计数据"""
        try:
            stats_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "cache", "hourly_stats.json")
            
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "stats" in data and isinstance(data["stats"], list):
                    HourlyStatsService._hourly_stats = data["stats"]
                
                if "last_update" in data:
                    HourlyStatsService._last_update_time = datetime.fromisoformat(data["last_update"])
                
                logger.info(f"Loaded hourly stats from {stats_file}")
            else:
                logger.info("No saved hourly stats found, will create on first request")
        
        except Exception as e:
            logger.error(f"Error initializing hourly stats service: {e}")
