from fastapi import APIRouter, HTTPException
from models.resource import ResourceResponse
from services.resource_service import ResourceService
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/resource", tags=["资源管理"])

@router.get("/status")
async def get_resource_status():
    """
    获取资源状态
    """
    try:
        return {
            "code": 200,
            "message": "获取资源状态成功",
            "data": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    except Exception as e:
        logger.error(f"Error getting resource status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data", response_model=ResourceResponse)
async def get_resource_data():
    """
    获取资源数据列表
    """
    try:
        resource_items = await ResourceService.get_resource_data()
        return ResourceResponse(
            code=200,
            message="获取资源数据成功",
            data=resource_items
        )
    except Exception as e:
        logger.error(f"Error getting resource data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{base_dir:path}")
async def start_analysis(base_dir: str):
    """
    启动资源分析任务
    """
    try:
        task_id = await ResourceService.start_analysis_task(base_dir)
        return {
            "code": 200,
            "message": "分析任务已启动",
            "data": {
                "task_id": task_id
            }
        }
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    """
    try:
        status = await ResourceService.get_task_status(task_id)
        return {
            "code": 200,
            "message": "获取任务状态成功",
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
