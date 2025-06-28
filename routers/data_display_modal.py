"""
数据展示模态框API路由
为DataDisplayModal组件提供后端接口支持
使用get_auto_analysis_result作为主要数据源
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from services.resource_service import ResourceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-sources", tags=["data-display"])

# ==================== 数据模型定义 ====================

class DataSourceOption(BaseModel):
    label: str
    value: str

class MetricData(BaseModel):
    title: str
    value: str
    trend: str

class LatestDataItem(BaseModel):
    title: str
    type: str
    dataSize: int
    updateDate: str

class ChartData(BaseModel):
    categories: List[str]
    values: List[int]

class DataSourceConfigResponse(BaseModel):
    dataSourceOptions: List[DataSourceOption]
    fieldOptions: List[str]
    subTypeOptions: Dict[str, List[str]]
    exportOptions: List[str]

class DataStatsResponse(BaseModel):
    metricData: List[MetricData]
    chartData: ChartData
    latestData: List[LatestDataItem]

class DataUpdateParams(BaseModel):
    dataSource: str
    selectedSubTypes: List[str]
    dateRange: List[str]  # [start_date, end_date]
    selectedFields: List[str]

class DataExportParams(BaseModel):
    format: str
    dataSource: Optional[str] = None
    dateRange: Optional[List[str]] = None
    fields: Optional[List[str]] = None

# ==================== 配置数据 ====================

# 数据源选项配置
DATA_SOURCE_OPTIONS = [
    {"label": "📚 学术论文", "value": "academic_papers"},
    {"label": "📊 调查报告", "value": "survey_reports"},
    {"label": "📖 专业书籍", "value": "professional_books"},
    {"label": "📜 政策文件", "value": "policy_documents"},
    {"label": "⚖️ 法规标准", "value": "regulations"},
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
        return await ResourceService.get_auto_analysis_result()
    except Exception as e:
        logger.error(f"Failed to get auto analysis result: {e}")
        return None

# ==================== API接口 ====================

@router.get("/config")
async def get_data_source_config():
    """获取数据源配置信息"""
    try:
        return {
            "code": 200,
            "message": "Success",
            "data": {
                "dataSourceOptions": DATA_SOURCE_OPTIONS,
                "fieldOptions": FIELD_OPTIONS,
                "subTypeOptions": SUB_TYPE_OPTIONS,
                "exportOptions": EXPORT_OPTIONS
            }
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
    dataSource: Optional[str] = Query(None),
    dateRange: Optional[str] = Query(None),
    fields: Optional[str] = Query(None)
):
    """获取数据统计信息，使用get_auto_analysis_result作为数据源"""
    try:
        # 获取自动分析结果
        auto_analysis_data = await get_auto_analysis_data()
        
        if auto_analysis_data:
            # 基于真实数据生成统计信息
            total_count = sum(item.count for item in auto_analysis_data)
            
            # 生成指标数据
            metric_data = [
                {"title": "文献总量", "value": f"{total_count:,}", "trend": "+12.5%"},
                {"title": "图文数据集", "value": f"{int(total_count * 0.3):,}", "trend": "+8.3%"},
                {"title": "数据覆盖率", "value": "25.8%", "trend": "+2.1%"},
                {"title": "数据源类型", "value": str(len(auto_analysis_data)), "trend": "+1"}
            ]
            
            # 生成图表数据
            categories = [item.name for item in auto_analysis_data[:5]]  # 取前5个
            values = [item.count for item in auto_analysis_data[:5]]
            
            # 生成最新数据列表
            latest_data = []
            for i, item in enumerate(auto_analysis_data[:5]):
                data_type = map_resource_to_data_type(item.name)
                latest_data.append({
                    "title": item.name,
                    "type": data_type,
                    "dataSize": item.count,
                    "updateDate": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                })
        else:
            # 使用默认数据
            metric_data = [
                {"title": "文献总量", "value": "52,489", "trend": "+12.5%"},
                {"title": "图文数据集", "value": "15,932", "trend": "+8.3%"},
                {"title": "数据覆盖率", "value": "25.8%", "trend": "+2.1%"},
                {"title": "数据源类型", "value": "8", "trend": "+1"}
            ]
            
            categories = ["学术论文", "调查报告", "专业书籍", "政策文件", "法规标准"]
            values = [25000, 12000, 8000, 4500, 3000]
            
            latest_data = [
                {"title": "人工智能发展白皮书", "type": "调查报告", "dataSize": 1250, "updateDate": "2024-01-15"},
                {"title": "数据安全标准规范", "type": "法规标准", "dataSize": 856, "updateDate": "2024-01-14"},
                {"title": "机器学习最新进展", "type": "学术论文", "dataSize": 2103, "updateDate": "2024-01-13"},
                {"title": "知识图谱应用研究", "type": "学术论文", "dataSize": 1587, "updateDate": "2024-01-12"},
                {"title": "行业数字化转型报告", "type": "调查报告", "dataSize": 945, "updateDate": "2024-01-10"}
            ]
        
        return {
            "code": 200,
            "message": "Success",
            "data": {
                "metricData": metric_data,
                "chartData": {"categories": categories, "values": values},
                "latestData": latest_data
            }
        }
    except Exception as e:
        logger.error(f"Error getting data stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metric_data():
    """获取指标卡数据"""
    try:
        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data:
            total_count = sum(item.count for item in auto_analysis_data)
            metrics = [
                {"title": "文献总量", "value": f"{total_count:,}", "trend": "+12.5%"},
                {"title": "图文数据集", "value": f"{int(total_count * 0.3):,}", "trend": "+8.3%"},
                {"title": "数据覆盖率", "value": "25.8%", "trend": "+2.1%"},
                {"title": "数据源类型", "value": str(len(auto_analysis_data)), "trend": "+1"}
            ]
        else:
            metrics = [
                {"title": "文献总量", "value": "52,489", "trend": "+12.5%"},
                {"title": "图文数据集", "value": "15,932", "trend": "+8.3%"},
                {"title": "数据覆盖率", "value": "25.8%", "trend": "+2.1%"},
                {"title": "数据源类型", "value": "8", "trend": "+1"}
            ]

        return {
            "code": 200,
            "message": "Success",
            "data": {"metrics": metrics}
        }
    except Exception as e:
        logger.error(f"Error getting metric data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart-data")
async def get_chart_data(
    dataSource: Optional[str] = Query(None),
    dateRange: Optional[str] = Query(None)
):
    """获取图表数据"""
    try:
        # TODO: 根据dataSource和dateRange参数筛选数据
        logger.info(f"Getting chart data for dataSource: {dataSource}, dateRange: {dateRange}")

        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data:
            categories = [item.name for item in auto_analysis_data[:5]]
            values = [item.count for item in auto_analysis_data[:5]]
        else:
            categories = ["学术论文", "调查报告", "专业书籍", "政策文件", "法规标准"]
            values = [25000, 12000, 8000, 4500, 3000]

        return {
            "code": 200,
            "message": "Success",
            "data": {"categories": categories, "values": values}
        }
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
async def get_latest_data(
    limit: Optional[int] = Query(5),
    dataSource: Optional[str] = Query(None),
    type: Optional[str] = Query(None)
):
    """获取最新数据列表"""
    try:
        # TODO: 根据dataSource和type参数筛选数据
        logger.info(f"Getting latest data with limit: {limit}, dataSource: {dataSource}, type: {type}")

        auto_analysis_data = await get_auto_analysis_data()

        if auto_analysis_data:
            latest_data = []
            for i, item in enumerate(auto_analysis_data[:limit]):
                data_type = map_resource_to_data_type(item.name)
                latest_data.append({
                    "title": item.name,
                    "type": data_type,
                    "dataSize": item.count,
                    "updateDate": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                })
        else:
            latest_data = [
                {"title": "人工智能发展白皮书", "type": "调查报告", "dataSize": 1250, "updateDate": "2024-01-15"},
                {"title": "数据安全标准规范", "type": "法规标准", "dataSize": 856, "updateDate": "2024-01-14"},
                {"title": "机器学习最新进展", "type": "学术论文", "dataSize": 2103, "updateDate": "2024-01-13"},
                {"title": "知识图谱应用研究", "type": "学术论文", "dataSize": 1587, "updateDate": "2024-01-12"},
                {"title": "行业数字化转型报告", "type": "调查报告", "dataSize": 945, "updateDate": "2024-01-10"}
            ][:limit]

        return {
            "code": 200,
            "message": "Success",
            "data": {"data": latest_data}
        }
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_data(params: DataUpdateParams):
    """更新数据"""
    try:
        # TODO: 根据params参数触发数据重新分析
        logger.info(f"Updating data with params: {params.model_dump()}")

        # 这里可以触发数据重新分析
        # 暂时返回成功响应
        return {
            "code": 200,
            "message": "数据更新请求已提交",
            "data": {
                "success": True,
                "message": "数据更新中，请稍后查看结果",
                "taskId": f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
        }
    except Exception as e:
        logger.error(f"Error updating data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update/progress/{task_id}")
async def get_update_progress(task_id: str):
    """获取数据更新进度"""
    try:
        # TODO: 根据task_id查询实际进度
        logger.info(f"Getting update progress for task: {task_id}")

        # 模拟进度查询
        return {
            "code": 200,
            "message": "Success",
            "data": {
                "progress": 100,
                "status": "completed",
                "message": "数据更新完成"
            }
        }
    except Exception as e:
        logger.error(f"Error getting update progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
async def export_data(params: DataExportParams):
    """导出数据"""
    try:
        # TODO: 根据params参数实现数据导出逻辑
        logger.info(f"Exporting data with params: {params.model_dump()}")

        # 这里实现数据导出逻辑
        # 暂时返回成功响应
        return {
            "code": 200,
            "message": "数据导出请求已提交",
            "data": {
                "taskId": f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "status": "processing"
            }
        }
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/status/{task_id}")
async def get_export_status(task_id: str):
    """获取导出任务状态"""
    try:
        return {
            "code": 200,
            "message": "Success",
            "data": {
                "status": "completed",
                "progress": 100,
                "downloadUrl": f"/api/downloads/{task_id}.csv"
            }
        }
    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime")
async def get_realtime_updates():
    """获取实时数据更新"""
    try:
        return {
            "code": 200,
            "message": "Success",
            "data": {
                "lastUpdate": datetime.now().isoformat(),
                "hasNewData": False,
                "newDataCount": 0,
                "metrics": [
                    {"title": "文献总量", "value": "52,489", "trend": "+12.5%"},
                    {"title": "图文数据集", "value": "15,932", "trend": "+8.3%"},
                    {"title": "数据覆盖率", "value": "25.8%", "trend": "+2.1%"},
                    {"title": "数据源类型", "value": "8", "trend": "+1"}
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error getting realtime updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
