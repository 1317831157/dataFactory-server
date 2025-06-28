"""
数据展示模态框后端接口
为 DataDisplayModal 组件提供完整的API支持
使用 get_auto_analysis_result 作为主要数据源
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
import uuid
import time
import random
from datetime import datetime, timedelta
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["数据展示模态框"])

# ==================== 数据模型定义 ====================

class DataSourceOption(BaseModel):
    """数据源选项"""
    label: str
    value: str

class MetricData(BaseModel):
    """指标数据"""
    title: str
    value: str
    trend: str

class LatestDataItem(BaseModel):
    """最新数据项"""
    title: str
    type: str
    dataSize: int
    updateDate: str

class ChartData(BaseModel):
    """图表数据"""
    categories: List[str]
    values: List[int]

class DataSourceConfigResponse(BaseModel):
    """数据源配置响应"""
    dataSourceOptions: List[DataSourceOption]
    fieldOptions: List[str]
    subTypeOptions: Dict[str, List[str]]
    exportOptions: List[str]

class DataStatsResponse(BaseModel):
    """数据统计响应"""
    metricData: List[MetricData]
    chartData: ChartData
    latestData: List[LatestDataItem]

class DataUpdateParams(BaseModel):
    """数据更新参数"""
    dataSource: str
    selectedSubTypes: List[str]
    dateRange: List[str]  # [start_date, end_date]
    selectedFields: List[str]

class DataExportParams(BaseModel):
    """数据导出参数"""
    format: str
    dataSource: Optional[str] = None
    dateRange: Optional[List[str]] = None
    fields: Optional[List[str]] = None

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportStatus(str, Enum):
    """导出状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# ==================== 配置数据 ====================

# 数据源选项配置
DATA_SOURCE_OPTIONS = [
    DataSourceOption(label="📚 学术论文", value="academic_papers"),
    DataSourceOption(label="📊 调查报告", value="survey_reports"),
    DataSourceOption(label="📖 专业书籍", value="professional_books"),
    DataSourceOption(label="📜 政策文件", value="policy_documents"),
    DataSourceOption(label="⚖️ 法规标准", value="regulations"),
]

# 研究领域选项
FIELD_OPTIONS = [
    "计算机科学", "人工智能", "数据科学", "机器学习",
    "深度学习", "自然语言处理", "计算机视觉", "知识图谱"
]

# 子类型选项映射
SUB_TYPE_OPTIONS = {
    "academic_papers": ["期刊论文", "会议论文", "学位论文", "预印本"],
    "survey_reports": ["行业报告", "市场调研", "用户研究", "技术评估"],
    "professional_books": ["教材", "专著", "参考书", "技术手册"],
    "policy_documents": ["国家政策", "行业政策", "地方政策", "国际政策"],
    "regulations": ["国家标准", "行业标准", "企业标准", "国际标准"]
}

# 导出格式选项
EXPORT_OPTIONS = ["CSV", "Excel", "PDF", "JSON"]

# 全局任务存储（生产环境应使用数据库）
update_tasks: Dict[str, Dict] = {}
export_tasks: Dict[str, Dict] = {}

# ==================== 辅助函数 ====================

def map_resource_to_data_type(resource_name: str) -> str:
    """将资源名称映射到数据类型"""
    name_lower = resource_name.lower()
    
    if any(keyword in name_lower for keyword in ["论文", "paper", "学术", "研究"]):
        return "学术论文"
    elif any(keyword in name_lower for keyword in ["报告", "report", "调研", "分析"]):
        return "调查报告"
    elif any(keyword in name_lower for keyword in ["书籍", "book", "教材", "专著"]):
        return "专业书籍"
    elif any(keyword in name_lower for keyword in ["政策", "policy", "规定", "制度"]):
        return "政策文件"
    elif any(keyword in name_lower for keyword in ["法规", "标准", "规范", "条例"]):
        return "法规标准"
    else:
        return "学术论文"  # 默认类型

async def get_auto_analysis_data():
    """获取自动分析数据"""
    try:
        from services.resource_service import ResourceService
        return await ResourceService.get_auto_analysis_result()
    except Exception as e:
        logger.error(f"Failed to get auto analysis result: {e}")
        return None

def generate_task_id() -> str:
    """生成任务ID"""
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

async def simulate_task_progress(task_id: str, task_dict: Dict[str, Dict], duration: int = 5):
    """模拟任务进度"""
    if task_id not in task_dict:
        return
    
    task = task_dict[task_id]
    start_time = time.time()
    
    # 模拟进度更新
    for progress in range(0, 101, 10):
        if task_id not in task_dict:  # 任务可能被取消
            return
            
        task["progress"] = progress
        task["status"] = TaskStatus.RUNNING if progress < 100 else TaskStatus.COMPLETED
        
        if progress < 100:
            await asyncio.sleep(duration / 10)
    
    # 完成任务
    if task_id in task_dict:
        task["status"] = TaskStatus.COMPLETED
        task["progress"] = 100
        task["endTime"] = datetime.now().isoformat()
        task["duration"] = int((time.time() - start_time) * 1000)

# ==================== API接口 ====================

@router.get("/config")
async def get_data_source_config():
    """获取数据源配置信息"""
    try:
        config = DataSourceConfigResponse(
            dataSourceOptions=DATA_SOURCE_OPTIONS,
            fieldOptions=FIELD_OPTIONS,
            subTypeOptions=SUB_TYPE_OPTIONS,
            exportOptions=EXPORT_OPTIONS
        )
        
        return {
            "code": 200,
            "message": "Success",
            "data": config.model_dump()
        }
    except Exception as e:
        logger.error(f"Error getting data source config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{data_source}/sub-types")
async def get_sub_type_options(data_source: str):
    """根据数据源类型获取子类型选项"""
    try:
        sub_types = SUB_TYPE_OPTIONS.get(data_source, [])

        return {
            "code": 200,
            "message": "Success",
            "data": {"subTypes": sub_types}
        }
    except Exception as e:
        logger.error(f"Error getting sub type options: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_data_stats(
    dataSource: Optional[str] = Query(None, description="数据源类型"),
    dateRange: Optional[str] = Query(None, description="日期范围"),
    fields: Optional[str] = Query(None, description="研究领域")
):
    """获取数据统计信息，使用get_auto_analysis_result作为数据源"""
    try:
        logger.info(f"Getting data stats for dataSource: {dataSource}, dateRange: {dateRange}, fields: {fields}")

        # 获取自动分析结果
        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data and len(auto_analysis_data) > 0:
            # 基于真实数据生成统计信息
            # auto_analysis_data 是字典列表，每个字典包含 {"id", "name", "count", "icon", "color", "files"}
            total_count = sum(item.get("count", 0) for item in auto_analysis_data)

            # 生成指标数据
            metric_data = [
                MetricData(title="文献总量", value=f"{total_count:,}", trend="+12.5%"),
                MetricData(title="图文数据集", value=f"{int(total_count * 0.3):,}", trend="+8.3%"),
                MetricData(title="数据覆盖率", value="25.8%", trend="+2.1%"),
                MetricData(title="数据源类型", value=str(len(auto_analysis_data)), trend="+1")
            ]

            # 生成图表数据（取前5个资源）
            categories = [item.get("name", "未知") for item in auto_analysis_data[:5]]
            values = [item.get("count", 0) for item in auto_analysis_data[:5]]
            chart_data = ChartData(categories=categories, values=values)

            # 生成最新数据列表
            latest_data = []
            for i, item in enumerate(auto_analysis_data[:5]):
                item_name = item.get("name", "未知")
                item_count = item.get("count", 0)
                data_type = map_resource_to_data_type(item_name)
                latest_data.append(LatestDataItem(
                    title=item_name,
                    type=data_type,
                    dataSize=item_count,
                    updateDate=(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                ))
        else:
            # 使用默认数据
            logger.info("Using default data as auto analysis result is not available")
            metric_data = [
                MetricData(title="文献总量", value="52,489", trend="+12.5%"),
                MetricData(title="图文数据集", value="15,932", trend="+8.3%"),
                MetricData(title="数据覆盖率", value="25.8%", trend="+2.1%"),
                MetricData(title="数据源类型", value="8", trend="+1")
            ]

            chart_data = ChartData(
                categories=["学术论文", "调查报告", "专业书籍", "政策文件", "法规标准"],
                values=[25000, 12000, 8000, 4500, 3000]
            )

            latest_data = [
                LatestDataItem(title="人工智能发展白皮书", type="调查报告", dataSize=1250, updateDate="2024-01-15"),
                LatestDataItem(title="数据安全标准规范", type="法规标准", dataSize=856, updateDate="2024-01-14"),
                LatestDataItem(title="机器学习最新进展", type="学术论文", dataSize=2103, updateDate="2024-01-13"),
                LatestDataItem(title="知识图谱应用研究", type="学术论文", dataSize=1587, updateDate="2024-01-12"),
                LatestDataItem(title="行业数字化转型报告", type="调查报告", dataSize=945, updateDate="2024-01-10")
            ]

        stats_response = DataStatsResponse(
            metricData=metric_data,
            chartData=chart_data,
            latestData=latest_data
        )

        return {
            "code": 200,
            "message": "Success",
            "data": stats_response.model_dump()
        }
    except Exception as e:
        logger.error(f"Error getting data stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metric_data():
    """获取指标卡数据"""
    try:
        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data and len(auto_analysis_data) > 0:
            total_count = sum(item.get("count", 0) for item in auto_analysis_data)
            metrics = [
                MetricData(title="文献总量", value=f"{total_count:,}", trend="+12.5%"),
                MetricData(title="图文数据集", value=f"{int(total_count * 0.3):,}", trend="+8.3%"),
                MetricData(title="数据覆盖率", value="25.8%", trend="+2.1%"),
                MetricData(title="数据源类型", value=str(len(auto_analysis_data)), trend="+1")
            ]
        else:
            metrics = [
                MetricData(title="文献总量", value="52,489", trend="+12.5%"),
                MetricData(title="图文数据集", value="15,932", trend="+8.3%"),
                MetricData(title="数据覆盖率", value="25.8%", trend="+2.1%"),
                MetricData(title="数据源类型", value="8", trend="+1")
            ]

        return {
            "code": 200,
            "message": "Success",
            "data": {"metrics": [metric.model_dump() for metric in metrics]}
        }
    except Exception as e:
        logger.error(f"Error getting metric data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart-data")
async def get_chart_data(
    dataSource: Optional[str] = Query(None, description="数据源类型"),
    dateRange: Optional[str] = Query(None, description="日期范围")
):
    """获取图表数据"""
    try:
        logger.info(f"Getting chart data for dataSource: {dataSource}, dateRange: {dateRange}")

        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data and len(auto_analysis_data) > 0:
            categories = [item.get("name", "未知") for item in auto_analysis_data[:5]]
            values = [item.get("count", 0) for item in auto_analysis_data[:5]]
        else:
            categories = ["学术论文", "调查报告", "专业书籍", "政策文件", "法规标准"]
            values = [25000, 12000, 8000, 4500, 3000]

        chart_data = ChartData(categories=categories, values=values)

        return {
            "code": 200,
            "message": "Success",
            "data": chart_data.model_dump()
        }
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
async def get_latest_data(
    limit: Optional[int] = Query(5, description="返回数量限制"),
    dataSource: Optional[str] = Query(None, description="数据源类型"),
    type: Optional[str] = Query(None, description="数据类型")
):
    """获取最新数据列表"""
    try:
        logger.info(f"Getting latest data with limit: {limit}, dataSource: {dataSource}, type: {type}")

        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data and len(auto_analysis_data) > 0:
            latest_data = []
            for i, item in enumerate(auto_analysis_data[:limit]):
                item_name = item.get("name", "未知")
                item_count = item.get("count", 0)
                data_type = map_resource_to_data_type(item_name)
                latest_data.append(LatestDataItem(
                    title=item_name,
                    type=data_type,
                    dataSize=item_count,
                    updateDate=(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                ))
        else:
            default_data = [
                LatestDataItem(title="人工智能发展白皮书", type="调查报告", dataSize=1250, updateDate="2024-01-15"),
                LatestDataItem(title="数据安全标准规范", type="法规标准", dataSize=856, updateDate="2024-01-14"),
                LatestDataItem(title="机器学习最新进展", type="学术论文", dataSize=2103, updateDate="2024-01-13"),
                LatestDataItem(title="知识图谱应用研究", type="学术论文", dataSize=1587, updateDate="2024-01-12"),
                LatestDataItem(title="行业数字化转型报告", type="调查报告", dataSize=945, updateDate="2024-01-10")
            ]
            latest_data = default_data[:limit]

        return {
            "code": 200,
            "message": "Success",
            "data": {"data": [item.model_dump() for item in latest_data]}
        }
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_data(params: DataUpdateParams, background_tasks: BackgroundTasks):
    """更新数据"""
    try:
        logger.info(f"Updating data with params: {params.model_dump()}")

        # 生成任务ID
        task_id = generate_task_id()

        # 创建任务记录
        task = {
            "taskId": task_id,
            "status": TaskStatus.PENDING,
            "progress": 0,
            "startTime": datetime.now().isoformat(),
            "params": params.model_dump()
        }

        update_tasks[task_id] = task

        # 启动后台任务模拟数据更新
        background_tasks.add_task(simulate_task_progress, task_id, update_tasks, 8)

        return {
            "code": 200,
            "message": "数据更新请求已提交",
            "data": {
                "success": True,
                "message": "数据更新中，请稍后查看结果",
                "taskId": task_id
            }
        }
    except Exception as e:
        logger.error(f"Error updating data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update/progress/{task_id}")
async def get_update_progress(task_id: str):
    """获取数据更新进度"""
    try:
        logger.info(f"Getting update progress for task: {task_id}")

        if task_id not in update_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = update_tasks[task_id]

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "progress": task["progress"],
                "status": task["status"],
                "message": f"数据更新进度: {task['progress']}%"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting update progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
async def export_data(params: DataExportParams, background_tasks: BackgroundTasks):
    """导出数据"""
    try:
        logger.info(f"Exporting data with params: {params.model_dump()}")

        # 生成任务ID
        task_id = generate_task_id()

        # 创建导出任务记录
        task = {
            "taskId": task_id,
            "status": ExportStatus.PENDING,
            "progress": 0,
            "startTime": datetime.now().isoformat(),
            "params": params.model_dump(),
            "format": params.format
        }

        export_tasks[task_id] = task

        # 启动后台任务模拟数据导出
        background_tasks.add_task(simulate_export_task, task_id, params.format)

        return {
            "code": 200,
            "message": "数据导出请求已提交",
            "data": {
                "taskId": task_id,
                "status": ExportStatus.PROCESSING
            }
        }
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/status/{task_id}")
async def get_export_status(task_id: str):
    """获取导出任务状态"""
    try:
        logger.info(f"Getting export status for task: {task_id}")

        if task_id not in export_tasks:
            raise HTTPException(status_code=404, detail="Export task not found")

        task = export_tasks[task_id]

        response_data = {
            "status": task["status"],
            "progress": task["progress"]
        }

        # 如果任务完成，添加下载链接
        if task["status"] == ExportStatus.COMPLETED:
            response_data["downloadUrl"] = f"/api/downloads/{task_id}.{task['format'].lower()}"

        # 如果任务失败，添加错误信息
        if task["status"] == ExportStatus.FAILED:
            response_data["error"] = task.get("error", "导出失败")

        return {
            "code": 200,
            "message": "Success",
            "data": response_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime")
async def get_realtime_updates():
    """获取实时数据更新"""
    try:
        # 获取最新的指标数据
        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data and len(auto_analysis_data) > 0:
            total_count = sum(item.get("count", 0) for item in auto_analysis_data)
            metrics = [
                MetricData(title="文献总量", value=f"{total_count:,}", trend="+12.5%"),
                MetricData(title="图文数据集", value=f"{int(total_count * 0.3):,}", trend="+8.3%"),
                MetricData(title="数据覆盖率", value="25.8%", trend="+2.1%"),
                MetricData(title="数据源类型", value=str(len(auto_analysis_data)), trend="+1")
            ]
        else:
            metrics = [
                MetricData(title="文献总量", value="52,489", trend="+12.5%"),
                MetricData(title="图文数据集", value="15,932", trend="+8.3%"),
                MetricData(title="数据覆盖率", value="25.8%", trend="+2.1%"),
                MetricData(title="数据源类型", value="8", trend="+1")
            ]

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "lastUpdate": datetime.now().isoformat(),
                "hasNewData": random.choice([True, False]),  # 模拟随机更新
                "newDataCount": random.randint(0, 5),
                "metrics": [metric.model_dump() for metric in metrics]
            }
        }
    except Exception as e:
        logger.error(f"Error getting realtime updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitoring/status")
async def get_monitoring_status():
    """获取目录监听状态"""
    try:
        from services.directory_monitor_service import get_monitoring_status

        status = get_monitoring_status()

        return {
            "code": 200,
            "message": "Success",
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 辅助任务函数 ====================

async def simulate_export_task(task_id: str, format: str):
    """模拟导出任务"""
    if task_id not in export_tasks:
        return

    task = export_tasks[task_id]
    start_time = time.time()

    try:
        logger.info(f"Starting export task {task_id} with format: {format}")

        # 模拟导出进度
        for progress in range(0, 101, 20):
            if task_id not in export_tasks:  # 任务可能被取消
                return

            task["progress"] = progress
            task["status"] = ExportStatus.PROCESSING if progress < 100 else ExportStatus.COMPLETED

            if progress < 100:
                await asyncio.sleep(1)  # 导出任务稍快一些

        # 完成任务
        if task_id in export_tasks:
            task["status"] = ExportStatus.COMPLETED
            task["progress"] = 100
            task["endTime"] = datetime.now().isoformat()
            task["duration"] = int((time.time() - start_time) * 1000)
            logger.info(f"Export task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Export task {task_id} failed: {e}")
        if task_id in export_tasks:
            task["status"] = ExportStatus.FAILED
            task["error"] = str(e)
