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

class CrawlResult(BaseModel):
    title: str
    source: str
    time: str

class CrawlResultsResponse(BaseModel):
    results: List[CrawlResult]
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

# 全局变量，用于模拟爬虫状态
crawling_tasks = {}

# 数据采集相关接口
@router.get("/collection/statistics", response_model=DataSourceStatistics)
async def get_source_statistics():
    """获取数据源统计信息"""
    try:
        # 获取自动分析结果
        analysis_result = await ResourceService.get_auto_analysis_result()
        
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
    """开始数据爬取"""
    try:
        task_id = f"crawl_{request.sourceType}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 检查是否已有相同类型的爬虫任务在运行
        for tid, task in crawling_tasks.items():
            if task.get("sourceType") == request.sourceType and task.get("status") == "running":
                return {
                    "code": 200,
                    "message": "success",
                    "data": {"task_id": tid, "status": "already_running", "message": "已有相同类型的爬虫任务在运行"}
                }
        
        # 创建新任务
        crawling_tasks[task_id] = {
            "sourceType": request.sourceType,
            "limit": request.limit,
            "status": "running",
            "startTime": datetime.now(),
            "results": []
        }
        
        # 使用新的SourceAnalysisService分析指定类型的文件
        background_tasks.add_task(SourceAnalysisService.analyze_source_by_type, 
                                 request.sourceType, 
                                 request.limit)
        
        return {
            "code": 200,
            "message": "success",
            "data": {"task_id": task_id, "status": "started", "message": "爬取任务已启动"}
        }
    except Exception as e:
        logger.error(f"Error starting crawling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collection/crawl/stop")
async def stop_crawling():
    """停止数据爬取"""
    try:
        # 停止所有运行中的爬虫任务
        stopped_count = 0
        for task_id, task in crawling_tasks.items():
            if task.get("status") == "running":
                task["status"] = "stopped"
                stopped_count += 1
        
        return {
            "code": 200,
            "message": "success",
            "data": {"stopped_count": stopped_count, "message": f"已停止{stopped_count}个爬虫任务"}
        }
    except Exception as e:
        logger.error(f"Error stopping crawling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collection/results")
async def get_crawl_results(
    sourceType: str = Query(..., description="数据源类型"),
    page: int = Query(1, description="页码"),
    pageSize: int = Query(10, description="每页数量")
):
    """获取爬取结果"""
    try:
        # 直接从SourceAnalysisService获取分析结果
        analysis_results = await SourceAnalysisService.get_analysis_result(sourceType)
        
        # 如果没有结果，返回空列表
        if not analysis_results or "result" not in analysis_results:
            return {
                "code": 200,
                "message": "success",
                "data": {"results": [], "total": 0}
            }
        
        # 获取结果列表
        result_list = analysis_results.get("result", [])
        total = len(result_list)
        
        # 计算分页
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paged_results = result_list[start_idx:end_idx]
        
        # 转换为前端需要的格式
        formatted_results = []
        for item in paged_results:
            # 从文件夹中提取第一个文件作为标题
            title = item.get("folder_name", "未知文件夹")
            
            # 使用文件夹路径作为来源
            source = item.get("folder_path", "未知路径")
            
            # 获取文件列表
            files = item.get("files", [])
            file_count = item.get("file_count", 0)
            
            # 创建结果项
            result_item = {
                "title": title,
                "source": source,
                "time": datetime.now().isoformat(),
                "fileCount": file_count,
                "files": files
            }
            
            formatted_results.append(result_item)
        
        return {
            "code": 200,
            "message": "success",
            "data": {"results": formatted_results, "total": total}
        }
    except Exception as e:
        logger.error(f"Error getting crawl results: {e}")
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








