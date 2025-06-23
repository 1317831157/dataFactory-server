import uuid
import logging
from typing import Dict, Any, List, Optional
import asyncio

from services.rate_limiter import rate_limiter, task_queue
from services.resource_service import ResourceService, AnalysisTask

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResourceQueueService:
    """资源队列服务，用于限流和队列化处理资源分析任务"""
    
    # 端点限流配置
    ENDPOINT_LIMITS = {
        "analyze": 5,  # 每分钟最多5个分析请求
        "auto_analyze": 1  # 每分钟最多1个自动分析请求
    }
    
    @staticmethod
    async def start_analysis_task(base_dir: str, file_list=None, options=None) -> Dict[str, Any]:
        """
        启动限流的异步分析任务
        
        Args:
            base_dir: 基础目录路径
            file_list: 文件列表，如果提供则只分析这些文件
            options: 其他选项
        
        Returns:
            Dict: 包含任务ID和状态的字典
        """
        # 检查限流
        if not await rate_limiter.check_rate_limit("analyze"):
            return {
                "task_id": None,
                "status": "rate_limited",
                "message": "请求频率过高，请稍后再试"
            }
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 将任务添加到队列
        await task_queue.enqueue_task(
            task_id,
            ResourceQueueService._run_analysis_task,
            base_dir,
            file_list,
            options
        )
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "分析任务已加入队列"
        }
    
    @staticmethod
    async def _run_analysis_task(base_dir: str, file_list=None, options=None) -> Dict[str, Any]:
        """
        运行分析任务的包装函数
        
        Args:
            base_dir: 基础目录路径
            file_list: 文件列表
            options: 其他选项
            
        Returns:
            Dict: 分析结果
        """
        # 调用原始的ResourceService方法
        task_id = await ResourceService.start_analysis_task(base_dir, file_list, options)
        
        # 等待任务完成
        while True:
            task_status = await ResourceQueueService.get_task_status(task_id)
            if task_status["status"] in ["completed", "failed"]:
                return task_status
            await asyncio.sleep(1)
    
    @staticmethod
    async def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务状态信息
        """
        # 检查队列中的任务
        queue_status = await task_queue.get_task_status(task_id)
        if queue_status["status"] != "not_found":
            return queue_status
        
        # 检查ResourceService中的任务
        if task_id in ResourceService._analysis_tasks:
            task = ResourceService._analysis_tasks[task_id]
            return {
                "task_id": task_id,
                "status": task.status,
                "progress": task.progress,
                "result": task.result,
                "error": task.error
            }
        
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": "任务不存在"
        }
    
    @staticmethod
    async def auto_analyze_with_queue() -> Dict[str, Any]:
        """
        使用队列系统启动自动分析任务
        
        Returns:
            Dict: 包含任务ID和状态的字典
        """
        # 检查限流
        if not await rate_limiter.check_rate_limit("auto_analyze"):
            return {
                "status": "rate_limited",
                "message": "自动分析请求频率过高，请稍后再试"
            }
        
        # 检查是否已有自动分析任务在运行
        if ResourceService._auto_analysis_running:
            return {
                "status": "already_running",
                "message": "自动分析任务已在运行中"
            }
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 将任务添加到队列
        await task_queue.enqueue_task(
            task_id,
            ResourceService.auto_analyze_local_directories
        )
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "自动分析任务已加入队列"
        }
    
    @staticmethod
    async def get_auto_analysis_result() -> List[Dict[str, Any]]:
        """
        获取自动分析结果，如果需要则启动新的分析
        
        Returns:
            List: 分析结果列表
        """
        # 直接调用原始方法
        return await ResourceService.get_auto_analysis_result()