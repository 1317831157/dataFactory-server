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
from services.database import Task, Alert

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["数据分析仪表盘"])

@router.get("/visit-statistics")
async def get_visit_statistics():
    """
    获取访问统计数据（从数据库最新分析结果统计）
    """
    try:
        visit_data = []
        # 查找24小时内最新的自动分析任务
        task = await Task.find_one(
            Task.task_type == "auto_resource_analysis",
            Task.status == "completed",
            sort=[("end_time", -1)]
        )
        if task and task.result and "categories" in task.result:
            for category in task.result["categories"]:
                if "name" in category and "count" in category:
                    visit_data.append({
                        "name": category["name"],
                        "value": category["count"]
                    })
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
    获取每小时数据提取量（从数据库分析结果统计）
    返回过去24小时内每3小时的数据提取量
    """
    try:
        now = datetime.now()
        start_time = now - timedelta(hours=24)
        # 查找24小时内所有已完成的自动分析任务
        tasks = await Task.find(
            Task.task_type == "auto_resource_analysis",
            Task.status == "completed",
            Task.end_time >= start_time
        ).to_list()
        
        # 构建8个3小时区间
        buckets = [start_time + timedelta(hours=3*i) for i in range(9)]  # 8段+1
        hourly_data = [0 for _ in range(8)]
        for task in tasks:
            if not hasattr(task, "end_time") or not task.end_time or not task.result or "categories" not in task.result:
                continue
            # 计算该任务属于哪个区间
            for i in range(8):
                if buckets[i] <= task.end_time < buckets[i+1]:
                    # 统计本次分析的总文件数
                    total_count = sum(cat.get("count", 0) for cat in task.result["categories"])
                    hourly_data[i] += total_count
                    break

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
    返回最近的告警消息列表（直接从数据库查询）
    """
    try:
        # 从数据库获取最新的报警信息
        alerts = await AlertService.get_alerts(limit=20)  # 默认查20条最新
        return {
            "code": 200,
            "message": "获取告警信息成功",
            "data": alerts
        }
    except Exception as e:
        logger.error(f"Error in get_alert_messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))



