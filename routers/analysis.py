from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import asyncio
from utils.error_handlers import handle_pydantic_errors
from services.resource_service import ResourceService
# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

class FileInfo(BaseModel):
    name: str
    path: str
    type: str

class AnalysisRequest(BaseModel):
    directory: str
    options: Optional[Dict[str, Any]] = None
    fileList: Optional[List[FileInfo]] = None

@router.post("/analyze")
async def start_analysis(request: AnalysisRequest):
    """启动分析任务"""
    try:
        from services.resource_service import ResourceService
        
        # 获取文件列表
        file_list = None
        if request.options and "fileList" in request.options:
            file_list = request.options["fileList"]
            logger.info(f"Received file list with {len(file_list)} files")
        
        # 传递directory和file_list参数
        task_id = await ResourceService.start_analysis_task(
            request.directory,
            file_list,
            request.options
        )
        
        return {
            "code": 200,
            "message": "Analysis task started",
            "data": {
                "task_id": task_id,
                "status": "pending"
            }
        }
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }

@router.get("/analyze/progress/{task_id}")
async def get_analysis_progress(task_id: str):
    """获取分析任务进度"""
    try:
        from services.resource_service import ResourceService
        status = await ResourceService.get_task_status(task_id)
        if status["status"] == "not_found":
            return {
                "code": 404,
                "message": "Task not found",
                "data": None
            }
        return {
            "code": 200,
            "message": "Success",
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting task progress: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }

@router.get("/output")
async def get_analysis_output():
    """获取分析结果"""
    try:
      
        print("/output",ResourceService._auto_analysis_running)
        # 如果分析未运行，则启动新的分析任务
        if not ResourceService._auto_analysis_running:
            logger.info("Analysis not running, starting new analysis task")
            # 创建异步任务并保存任务引用
            asyncio.create_task(ResourceService.auto_analyze_local_directories())
            # 给任务一点时间开始执行
            await asyncio.sleep(0.1)
            
            # 再次检查运行标志，确认任务已启动
            if ResourceService._auto_analysis_running:
                logger.info("Analysis task started successfully")
            else:
                logger.warning("Analysis task did not start properly")
        
        # 获取当前结果
        result = await ResourceService.get_auto_analysis_result()
        
        # 获取分析进度
        analysis_progress = {
            "is_running": ResourceService._auto_analysis_running,
            "progress": 0
        }
        
        # 如果有正在运行的任务，获取其进度
        if ResourceService._auto_analysis_running:
            # 查找与自动分析相关的任务
            for task_id, task in ResourceService._analysis_tasks.items():
                if hasattr(task, 'is_auto_analysis') and task.is_auto_analysis:
                    analysis_progress["progress"] = task.progress
                    analysis_progress["status"] = task.status
                    break
            
            logger.info(f"Analysis progress: {analysis_progress}")
        
        return {
            "code": 200,  # 使用202 Accepted状态码表示请求已接受但处理尚未完成
            "message": "Analysis started, please try again later",
            "data": result,
            "analysis_progress": analysis_progress
        }
    except Exception as e:
        logger.error(f"Error getting analysis output: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auto-analysis")
@handle_pydantic_errors
async def get_auto_analysis():
    """获取自动分析结果"""
    try:
        from services.resource_service import ResourceService
        result = await ResourceService.get_auto_analysis_result()
        
        # 获取分析进度
        analysis_progress = {
            "is_running": ResourceService._auto_analysis_running,
            "progress": 0
        }
        
        # 如果有正在运行的任务，获取其进度
        if ResourceService._auto_analysis_running:
            # 查找与自动分析相关的任务
            for task_id, task in ResourceService._analysis_tasks.items():
                if hasattr(task, 'is_auto_analysis') and task.is_auto_analysis:
                    analysis_progress["progress"] = task.progress
                    analysis_progress["status"] = task.status
                    break
        
        return {
            "code": 200,
            "message": "Success",
            "data": result,
            "analysis_progress": analysis_progress
        }
    except Exception as e:
        logger.error(f"Error getting auto analysis result: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None,
            "analysis_progress": {"is_running": False, "progress": 0}
        }













