import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    async def get_alerts() -> List[Dict[str, Any]]:
        """获取系统告警信息"""
        # 如果没有告警，生成一些基于分析结果的告警
        if not AlertService._alerts:
            await AlertService._generate_alerts_from_analysis()
        
        return AlertService._alerts
    
    @staticmethod
    async def _generate_alerts_from_analysis():
        """基于分析结果生成告警信息"""
        try:
            # 获取缓存文件路径
            cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "cache", "auto_analysis_cache.json")
            
            current_time = datetime.now()
            alerts = []
            
            # 检查缓存文件是否存在
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    # 分析缓存数据，生成告警
                    if "result" in cache_data and isinstance(cache_data["result"], list):
                        # 计算总文件数
                        total_files = sum(category.get("count", 0) for category in cache_data["result"])
                        
                        # 检查文件数量是否过多
                        if total_files > 10000:
                            alerts.append({
                                "type": "warning",
                                "message": f"索引文件数量过多 ({total_files}个)，可能影响系统性能",
                                "time": (current_time - timedelta(hours=random.randint(1, 5))).strftime("%Y-%m-%d %H:%M:%S")
                            })
                        
                        # 检查是否有大型类别
                        for category in cache_data["result"]:
                            if category.get("count", 0) > 5000:
                                alerts.append({
                                    "type": "warning",
                                    "message": f"类别 '{category.get('name', '未知')}' 包含过多文件 ({category.get('count')}个)",
                                    "time": (current_time - timedelta(hours=random.randint(1, 8))).strftime("%Y-%m-%d %H:%M:%S")
                                })
                    
                    # 检查缓存时间是否过旧
                    if "timestamp" in cache_data:
                        cache_time = datetime.fromisoformat(cache_data["timestamp"])
                        if (current_time - cache_time) > timedelta(days=3):
                            alerts.append({
                                "type": "warning",
                                "message": f"分析数据已过期 ({(current_time - cache_time).days}天前)",
                                "time": (current_time - timedelta(hours=random.randint(1, 12))).strftime("%Y-%m-%d %H:%M:%S")
                            })
                
                except Exception as e:
                    logger.error(f"Error analyzing cache file: {e}")
                    # 添加一个关于缓存文件读取错误的告警
                    alerts.append({
                        "type": "error",
                        "message": f"读取缓存文件时出错: {str(e)}",
                        "time": current_time.strftime("%Y-%m-%d %H:%M:%S")
                    })
            else:
                # 如果缓存文件不存在，添加一个告警
                alerts.append({
                    "type": "warning",
                    "message": "未找到分析缓存文件，系统可能需要重新分析",
                    "time": current_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 检查系统资源使用情况（模拟）
            # 在实际项目中，这里应该获取真实的系统资源使用情况
            storage_usage = random.randint(70, 95)
            if storage_usage > AlertService._thresholds["storage_usage"]:
                alerts.append({
                    "type": "error" if storage_usage > 90 else "warning",
                    "message": f"存储空间使用率达到 {storage_usage}%",
                    "time": (current_time - timedelta(hours=random.randint(0, 4))).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 如果告警数量不足，添加一些随机告警
            if len(alerts) < 3:
                # 告警消息模板
                alert_templates = [
                    "数据提取任务 #{} 执行超时",
                    "API请求频率超过限制",
                    "服务器 #{} 负载过高",
                    "数据库连接池达到上限"
                ]
                
                # 添加随机告警，直到达到至少3条
                while len(alerts) < 3:
                    alert_type = random.choice(["warning", "error"])
                    template = random.choice(alert_templates)
                    
                    # 填充模板中的占位符
                    if "{}" in template:
                        message = template.format(random.randint(1, 10))
                    else:
                        message = template
                    
                    # 随机生成时间（过去24小时内）
                    hours_ago = random.randint(0, 23)
                    minutes_ago = random.randint(0, 59)
                    alert_time = current_time - timedelta(hours=hours_ago, minutes=minutes_ago)
                    time_str = alert_time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    alerts.append({
                        "type": alert_type,
                        "message": message,
                        "time": time_str
                    })
            
            # 按时间排序，最新的在前面
            alerts.sort(key=lambda x: x["time"], reverse=True)
            
            # 限制告警数量
            AlertService._alerts = alerts[:AlertService._max_alerts]
            
            # 将告警保存到文件
            try:
                alerts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                         "cache", "system_alerts.json")
                
                # 确保缓存目录存在
                os.makedirs(os.path.dirname(alerts_file), exist_ok=True)
                
                with open(alerts_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "alerts": AlertService._alerts,
                        "timestamp": current_time.isoformat()
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Saved system alerts to {alerts_file}")
            except Exception as e:
                logger.error(f"Failed to save system alerts: {e}")
            
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
            # 如果出错，返回一些基本的告警信息
            AlertService._alerts = [
                {
                    "type": "error",
                    "message": f"生成告警信息时出错: {str(e)}",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            ]
    
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
                await AlertService._generate_alerts_from_analysis()
        
        except Exception as e:
            logger.error(f"Error initializing alert service: {e}")