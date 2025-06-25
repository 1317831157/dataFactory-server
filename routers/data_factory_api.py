import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body, Path
from pydantic import BaseModel, Field

# 导入现有的服务
from services.resource_service import ResourceService
# 导入新的服务
from services.source_analysis_service import SourceAnalysisService
from services.database import AnalysisResult, AnalyzedFolder, AnalyzedFile # 导入模型用于响应

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()

# 数据模型定义
class CrawlRequest(BaseModel):
    sourceType: str
    limit: Optional[int] = 100

class DataSourceStatisticsData(BaseModel):
    counts: Dict[str, int]
    totalCount: int

class DataSourceStatistics(BaseModel):
    code: int = 200
    message: str = "success"
    data: DataSourceStatisticsData

class FormattedCrawlResult(BaseModel):
    title: str
    source: str
    time: str
    fileCount: int
    files: List[AnalyzedFile]

class CrawlResultsResponse(BaseModel):
    results: List[FormattedCrawlResult]
    total: int

class ProcessingStatistics(BaseModel):
    validPapers: int
    formulas: int
    trashData: int
    processingRate: float

class AnalysisTaskRequest(BaseModel):
    name: str
    modelId: str
    dataSource: str
    parameters: Dict[str, Any]

# 数据采集相关接口
@router.get("/collection/statistics", response_model=DataSourceStatistics)
async def get_source_statistics():
    """获取数据源统计信息"""
    try:
        # 获取自动分析结果
        analysis_result = await ResourceService.get_auto_analysis_result()
        # print('analysis_result',analysis_result)
        # 初始化计数字典 - 动态创建，不预定义字段
        counts = {}
        
        # 将分析结果映射到数据源类型
        if analysis_result:
            for item in analysis_result:
                category = item.get("name", "").lower()
                count = item.get("count", 0)
                
                # 直接使用分析结果中的类别名称
                if category:
                    counts[category] = count
        
        # 计算总数
        total_count = sum(counts.values())
        
        result = {
            "counts": counts,
            "totalCount": total_count
        }
        
        return {
            "code": 200,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting source statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collection/crawl")
async def start_crawling(request: CrawlRequest, background_tasks: BackgroundTasks):
    """开始数据分析。分析任务现在是持久化的。"""
    try:
        # 核心逻辑已移入服务中，包括检查任务是否已在运行
        # 我们仍然使用后台任务来避免阻塞API
        background_tasks.add_task(
            SourceAnalysisService.analyze_source_by_type, 
            request.sourceType, 
            request.limit
        )
        
        return {
            "code": 200,
            "message": "success",
            "data": {"status": "started", "message": "分析任务已在后台启动"}
        }
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/collection/crawl/stop")
# async def stop_crawling():
#     """
#     停止数据爬取 (功能已停用)。
#     在新的持久化架构中，安全地停止一个正在遍历本地文件的任务是复杂的，
#     需要引入更重量级的任务队列（如Celery）和进程管理。
#     因此暂时停用此接口，以避免不可预期的行为。
#     """
#     return {
#         "code": 503,
#         "message": "Service Unavailable",
#         "data": {"message": "此功能已停用，无法安全地中断正在进行的磁盘扫描任务。"}
#     }

@router.get("/collection/results", response_model_exclude_none=True)
async def get_crawl_results(
    sourceType: str = Query(..., description="数据源类型"),
    page: int = Query(1, description="页码"),
    pageSize: int = Query(10, description="每页数量")
):
    """获取指定数据源的最新分析结果。"""
    try:
        # 1. 从服务获取持久化的分析结果
        analysis_doc: AnalysisResult | None = await SourceAnalysisService.get_analysis_result(sourceType)
        
        # 2. 检查结果是否存在或是否已完成
        if not analysis_doc or analysis_doc.status != "completed":
            status_message = "分析正在进行中" if (analysis_doc and analysis_doc.status == "running") else "没有可用的分析结果"
            return {
                "code": 200,
                "message": "success",
                "data": {"results": [], "total": 0, "status": analysis_doc.status if analysis_doc else 'not_found', "message": status_message}
            }
        
        # 3. 分页处理
        result_list: List[AnalyzedFolder] = analysis_doc.results
        total = len(result_list)
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paged_results = result_list[start_idx:end_idx]
        
        # 4. 格式化为前端需要的格式
        formatted_results: List[FormattedCrawlResult] = []
        for item in paged_results:
            # 现在 item 是一个 Pydantic 模型，我们可以直接访问属性
            formatted_results.append(FormattedCrawlResult(
                title=item.folder_name,
                source=item.folder_path,
                time=analysis_doc.timestamp.isoformat(), # 使用任务完成的时间戳
                fileCount=item.file_count,
                files=item.files
            ))
        
        return {
            "code": 200,
            "message": "success",
            "data": {"results": formatted_results, "total": total, "status": analysis_doc.status}
        }
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 数据处理相关接口
@router.get("/processing/statistics")
async def get_processing_statistics():
    """获取处理统计数据"""
    try:
        # 获取自动分析结果，用于统计处理数据
        analysis_result = await ResourceService.get_auto_analysis_result()
        
        # 计算总文件夹数
        total_folders = sum(item.get("count", 0) for item in analysis_result) if analysis_result else 0
        
        # 模拟数据处理统计
        result = {
            "validPapers": int(total_folders * 0.7),  # 假设70%是有效论文
            "formulas": int(total_folders * 0.3),     # 假设30%包含公式
            "trashData": int(total_folders * 0.1),    # 假设10%是废弃数据
            "processingRate": 0.85                    # 假设处理率为85%
        }
        
        return {
            "code": 200,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting processing statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing/papers/valid")
async def get_valid_papers(
    page: int = Query(1, description="页码"),
    pageSize: int = Query(10, description="每页数量")
):
    """获取有效论文数据"""
    try:
        # 模拟数据
        papers = []
        for i in range(50):
            papers.append({
                "id": i + 1,
                "title": f"有效论文 #{i+1}",
                "author": f"作者 {i%10 + 1}",
                "journal": f"期刊 {i%5 + 1}",
                "year": 2020 + (i % 4),
                "keywords": [f"关键词{j}" for j in range(1, 4)]
            })
        
        # 分页处理
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paged_papers = papers[start_idx:end_idx]
        
        return {
            "code": 200,
            "message": "success",
            "data": {"papers": paged_papers, "total": len(papers)}
        }
    except Exception as e:
        logger.error(f"Error getting valid papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing/formulas")
async def get_formulas(
    page: int = Query(1, description="页码"),
    pageSize: int = Query(10, description="每页数量")
):
    """获取公式数据"""
    try:
        # 模拟数据
        formulas = []
        for i in range(30):
            formulas.append({
                "id": i + 1,
                "formula": f"E = mc^2 + {i}",
                "paper_title": f"论文标题 #{i+1}",
                "context": f"公式出现的上下文描述 {i}",
                "page": i % 10 + 1
            })
        
        # 分页处理
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paged_formulas = formulas[start_idx:end_idx]
        
        return {
            "code": 200,
            "message": "success",
            "data": {"formulas": paged_formulas, "total": len(formulas)}
        }
    except Exception as e:
        logger.error(f"Error getting formulas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing/trash")
async def get_trash_data(
    page: int = Query(1, description="页码"),
    pageSize: int = Query(10, description="每页数量")
):
    """获取废弃数据"""
    try:
        # 模拟数据
        trash_data = []
        for i in range(20):
            trash_data.append({
                "id": i + 1,
                "filename": f"废弃文件 #{i+1}.pdf",
                "reason": f"废弃原因 {i % 3 + 1}",
                "size": f"{i * 100 + 50}KB",
                "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            })
        
        # 分页处理
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paged_trash = trash_data[start_idx:end_idx]
        
        return {
            "code": 200,
            "message": "success",
            "data": {"trash": paged_trash, "total": len(trash_data)}
        }
    except Exception as e:
        logger.error(f"Error getting trash data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing/trend")
async def get_processing_trend(
    timeRange: str = Query("week", description="时间范围: day, week, month")
):
    """获取处理趋势数据"""
    try:
        # 根据时间范围确定数据点数量
        if timeRange == "day":
            points = 24  # 24小时
            label_format = "HH:00"
        elif timeRange == "week":
            points = 7   # 7天
            label_format = "MM-DD"
        else:  # month
            points = 30  # 30天
            label_format = "MM-DD"
        
        # 生成模拟数据
        trend_data = {
            "labels": [],
            "validPapers": [],
            "formulas": [],
            "trashData": []
        }
        
        for i in range(points):
            # 生成日期标签
            if timeRange == "day":
                date = datetime.now() - timedelta(hours=points-i-1)
                label = date.strftime("%H:00")
            else:
                date = datetime.now() - timedelta(days=points-i-1)
                label = date.strftime("%m-%d")
            
            trend_data["labels"].append(label)
            
            # 生成随机数据
            import random
            base = random.randint(50, 100)
            trend_data["validPapers"].append(base)
            trend_data["formulas"].append(int(base * 0.4))
            trend_data["trashData"].append(int(base * 0.1))
        
        return {
            "code": 200,
            "message": "success",
            "data": trend_data
        }
    except Exception as e:
        logger.error(f"Error getting processing trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 数据展示相关接口
@router.get("/display/sources")
async def get_data_sources():
    """获取数据源列表"""
    try:
        sources = [
            {"id": "academic", "name": "学术论文", "count": 117},
            {"id": "report", "name": "调查报告", "count": 117},
            {"id": "book", "name": "专业书籍", "count": 117},
            {"id": "policy", "name": "政策文件", "count": 117},
            {"id": "standard", "name": "法规标准", "count": 117}
        ]
        
        return {
            "code": 200,
            "message": "success",
            "data": {"sources": sources}
        }
    except Exception as e:
        logger.error(f"Error getting data sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 将路由器添加到应用程序中
# 在主应用程序中使用:
# from routers.data_factory_api import router as data_factory_router
# app.include_router(data_factory_router, prefix="/api")








