from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services.resource_service import ResourceService

router = APIRouter()

class AnalysisRequest(BaseModel):
    directory: str
    options: Optional[Dict[str, Any]] = None

@router.post("/analyze")
async def start_analysis(request: AnalysisRequest):
    """启动异步分析任务"""
    try:
        task_id = await ResourceService.start_analysis_task(request.directory)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/progress/{task_id}")
async def get_analysis_progress(task_id: str):
    """获取分析任务进度"""
    status = await ResourceService.get_task_status(task_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    return status