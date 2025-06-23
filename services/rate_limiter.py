import asyncio
import time
from typing import Dict, Any, Callable, Awaitable, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimiter:
    """请求限流器，控制API请求频率"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        初始化限流器
        
        Args:
            max_requests: 时间窗口内允许的最大请求数
            time_window: 时间窗口大小(秒)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_timestamps: Dict[str, list] = {}  # 按endpoint存储请求时间戳
        self._lock = asyncio.Lock()  # 用于线程安全操作
    
    async def check_rate_limit(self, endpoint: str) -> bool:
        """
        检查是否超过限流阈值
        
        Args:
            endpoint: API端点标识
            
        Returns:
            bool: 如果未超过限制返回True，否则返回False
        """
        async with self._lock:
            current_time = time.time()
            
            # 初始化endpoint的时间戳列表
            if endpoint not in self.request_timestamps:
                self.request_timestamps[endpoint] = []
            
            # 清理过期的时间戳
            self.request_timestamps[endpoint] = [
                ts for ts in self.request_timestamps[endpoint]
                if current_time - ts < self.time_window
            ]
            
            # 检查是否超过限制
            if len(self.request_timestamps[endpoint]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for endpoint: {endpoint}")
                return False
            
            # 添加新的时间戳
            self.request_timestamps[endpoint].append(current_time)
            return True

class TaskQueue:
    """任务队列系统，用于处理长时间运行的任务"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        """
        初始化任务队列
        
        Args:
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks = 0
        self.task_queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._worker_task = None
        self.task_results: Dict[str, Any] = {}
    
    async def start_worker(self):
        """启动工作线程处理队列中的任务"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("Task queue worker started")
    
    async def _process_queue(self):
        """处理队列中的任务"""
        while True:
            try:
                # 等待队列中的任务
                task_id, task_func, args, kwargs = await self.task_queue.get()
                
                # 更新运行中的任务数
                async with self._lock:
                    self.running_tasks += 1
                
                logger.info(f"Processing task {task_id}, current running tasks: {self.running_tasks}")
                
                try:
                    # 执行任务
                    result = await task_func(*args, **kwargs)
                    self.task_results[task_id] = {
                        "status": "completed",
                        "result": result
                    }
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    self.task_results[task_id] = {
                        "status": "failed",
                        "error": str(e)
                    }
                finally:
                    # 更新运行中的任务数
                    async with self._lock:
                        self.running_tasks -= 1
                    
                    # 标记任务完成
                    self.task_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error in task queue worker: {e}")
                await asyncio.sleep(1)  # 避免CPU占用过高
    
    async def enqueue_task(self, task_id: str, task_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> str:
        """
        将任务添加到队列
        
        Args:
            task_id: 任务ID
            task_func: 异步任务函数
            *args, **kwargs: 传递给任务函数的参数
            
        Returns:
            str: 任务ID
        """
        # 确保工作线程已启动
        await self.start_worker()
        
        # 初始化任务结果
        self.task_results[task_id] = {
            "status": "pending",
            "result": None
        }
        
        # 将任务添加到队列
        await self.task_queue.put((task_id, task_func, args, kwargs))
        logger.info(f"Task {task_id} added to queue, queue size: {self.task_queue.qsize()}")
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务状态信息
        """
        if task_id not in self.task_results:
            return {
                "status": "not_found",
                "result": None
            }
        
        return self.task_results[task_id]

# 创建全局实例
rate_limiter = RateLimiter()
task_queue = TaskQueue()