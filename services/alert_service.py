import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from beanie import Document
from pydantic import Field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Alert(Document):
    message: str
    level: str = "warning"
    timestamp: datetime = Field(default_factory=datetime.now)
    extra: Optional[dict] = None
    
    class Settings:
        name = "alerts"

class AlertService:
    """系统告警服务"""
    
    # 存储告警信息的类变量
    _alerts = []
    _max_alerts = 10  # 最多保存的告警数量
    
    # 告警类型和对应的阈值
    _thresholds = {
        "storage_usage": 80,  # 存储空间使用率阈值（百分比）
        "api_rate": 100,      # API请求频率阈值（每分钟请求数）
        "task_timeout": 30,   # 任务超时阈值（分钟）
        "server_load": 80,    # 服务器负载阈值（百分比）
        "db_connections": 90  # 数据库连接池使用率阈值（百分比）
    }
    
  
    
    @staticmethod
    async def initialize():
        """初始化服务，加载保存的告警信息"""
        try:
            alerts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "cache", "system_alerts.json")
            
            if os.path.exists(alerts_file):
                with open(alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "alerts" in data and isinstance(data["alerts"], list):
                    AlertService._alerts = data["alerts"]
                    logger.info(f"Loaded {len(AlertService._alerts)} alerts from {alerts_file}")
                else:
                    logger.warning(f"Invalid alerts data in {alerts_file}")
            else:
                logger.info("No saved alerts found, will generate on first request")
                # 初始化时生成一些告警
                await AlertService._generate_initial_alerts()
        
        except Exception as e:
            logger.error(f"Error initializing alert service: {e}")

    @staticmethod
    async def get_alerts(limit: int = 20):
        """从数据库查询最新的报警信息"""
        alerts = await Alert.find().sort("-timestamp").limit(limit).to_list()
        # 转为 dict 便于前端展示
        return [a.model_dump(exclude={"id"}) for a in alerts]

    @staticmethod
    async def add_alert(message: str, level: str = "warning", extra: dict = None):
        """插入报警信息到数据库"""
        alert = Alert(
            message=message,
            level=level,
            timestamp=datetime.now(),
            extra=extra or {}
        )
        await alert.insert()

    @staticmethod
    async def _generate_initial_alerts():
        """生成初始告警信息"""
        try:
            # 生成一些示例告警
            initial_alerts = [
                {
                    "message": "系统启动完成，所有服务正常运行",
                    "level": "info",
                    "extra": {"service": "system"}
                },
                {
                    "message": "数据库连接正常",
                    "level": "info",
                    "extra": {"service": "database"}
                }
            ]

            for alert_data in initial_alerts:
                await AlertService.add_alert(**alert_data)

            logger.info(f"Generated {len(initial_alerts)} initial alerts")

        except Exception as e:
            logger.error(f"Error generating initial alerts: {e}")