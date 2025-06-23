from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import asyncio

from services.resource_queue_service import ResourceQueueService

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queue", tags=["队列化分析"])

class AnalysisRequest(BaseModel):
    directory: str
    options: Optional[Dict[str, Any]] = None

@router.post("/analyze")
async def start_queued_analysis(request: AnalysisRequest):
    """启动队列化分析任务"""
    try:
        # 获取文件列表
        file_list = None
        if request.options and "fileList" in request.options:
            file_list = request.options["fileList"]
            logger.info(f"Received file list with {len(file_list)} files")
        
        # 使用队列服务启动分析任务
        result = await ResourceQueueService.start_analysis_task(
            request.directory,
            file_list,
            request.options
        )
        
        return {
            "code": 200,
            "message": "Analysis task queued",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error starting queued analysis: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        status = await ResourceQueueService.get_task_status(task_id)
        
        return {
            "code": 200,
            "message": "Task status retrieved",
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }

@router.post("/auto-analyze")
async def start_auto_analysis():
    """启动队列化自动分析任务"""
    try:
        result = await ResourceQueueService.auto_analyze_with_queue()
        
        return {
            "code": 200,
            "message": "Auto analysis task queued",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error starting auto analysis: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }

@router.get("/output")
async def get_analysis_output():
    """获取分析结果"""
    try:
        # 获取当前结果
        result = await ResourceQueueService.get_auto_analysis_result()
        
        return {
            "code": 200,
            "message": "Analysis output retrieved",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting analysis output: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }