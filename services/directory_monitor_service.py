"""
目录监听服务
监听指定目录的文件变化，当PDF和JSON文件数量发生变化时自动触发资源分析
"""

import os
import asyncio
import logging
import time
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

logger = logging.getLogger(__name__)

class DirectoryMonitorService:
    """目录监听服务类"""
    
    def __init__(self):
        self.observers: Dict[str, Observer] = {}
        self.file_counts: Dict[str, int] = {}
        self.last_analysis_time: Dict[str, datetime] = {}
        self.analysis_cooldown = timedelta(minutes=5)  # 分析冷却时间，避免频繁触发
        self.is_running = False
        self.monitored_directories: Set[str] = set()
        
    async def start_monitoring(self, base_dirs: list = None):
        """开始监听目录"""
        if self.is_running:
            logger.info("Directory monitoring is already running")
            return
            
        self.is_running = True
        
        # 默认监听目录
        if base_dirs is None:
            base_dirs = ["D:\\pdf"]
            
        # 确保目录存在
        valid_dirs = []
        for base_dir in base_dirs:
            if os.path.exists(base_dir):
                valid_dirs.append(base_dir)
                logger.info(f"Adding directory to monitor: {base_dir}")
            else:
                logger.warning(f"Directory does not exist: {base_dir}")
                
        if not valid_dirs:
            logger.error("No valid directories to monitor")
            return
            
        # 为每个目录创建监听器
        for base_dir in valid_dirs:
            await self._setup_directory_monitor(base_dir)
            
        logger.info(f"Started monitoring {len(valid_dirs)} directories")
        
    async def stop_monitoring(self):
        """停止监听"""
        self.is_running = False
        
        for path, observer in self.observers.items():
            observer.stop()
            observer.join()
            logger.info(f"Stopped monitoring: {path}")
            
        self.observers.clear()
        self.monitored_directories.clear()
        logger.info("Directory monitoring stopped")
        
    async def _setup_directory_monitor(self, base_dir: str):
        """为指定目录设置监听器"""
        try:
            # 初始化文件计数
            initial_count = await self._count_target_files(base_dir)
            self.file_counts[base_dir] = initial_count
            self.last_analysis_time[base_dir] = datetime.now() - self.analysis_cooldown
            
            # 创建事件处理器
            event_handler = DirectoryEventHandler(base_dir, self)
            
            # 创建观察者
            observer = Observer()
            observer.schedule(event_handler, base_dir, recursive=True)
            observer.start()
            
            self.observers[base_dir] = observer
            self.monitored_directories.add(base_dir)
            
            logger.info(f"Setup monitor for {base_dir}, initial file count: {initial_count}")
            
        except Exception as e:
            logger.error(f"Failed to setup monitor for {base_dir}: {e}")
            
    async def _count_target_files(self, directory: str) -> int:
        """统计目录中PDF和JSON文件的数量"""
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.pdf', '.json')):
                        count += 1
        except Exception as e:
            logger.error(f"Error counting files in {directory}: {e}")
            
        return count
        
    async def _handle_file_change(self, base_dir: str):
        """处理文件变化事件"""
        try:
            # 检查冷却时间
            now = datetime.now()
            if base_dir in self.last_analysis_time:
                time_since_last = now - self.last_analysis_time[base_dir]
                if time_since_last < self.analysis_cooldown:
                    logger.debug(f"Analysis cooldown active for {base_dir}, skipping")
                    return
                    
            # 统计当前文件数量
            current_count = await self._count_target_files(base_dir)
            previous_count = self.file_counts.get(base_dir, 0)
            
            # 检查文件数量是否发生变化
            if current_count != previous_count:
                logger.info(f"File count changed in {base_dir}: {previous_count} -> {current_count}")
                
                # 更新记录
                self.file_counts[base_dir] = current_count
                self.last_analysis_time[base_dir] = now
                
                # 触发自动分析
                await self._trigger_auto_analysis(base_dir)
            else:
                logger.debug(f"No file count change in {base_dir}")
                
        except Exception as e:
            logger.error(f"Error handling file change for {base_dir}: {e}")
            
    async def _trigger_auto_analysis(self, base_dir: str):
        """触发自动分析"""
        try:
            logger.info(f"Triggering auto analysis for directory: {base_dir}")
            
            # 导入并调用资源服务的自动分析函数
            from services.resource_service import ResourceService
            
            # 检查是否已有分析在运行
            if ResourceService._auto_analysis_running:
                logger.info("Auto analysis already running, skipping trigger")
                return
                
            # 异步启动分析任务
            asyncio.create_task(ResourceService.auto_analyze_local_directories(base_dir))
            
            logger.info(f"Auto analysis triggered for {base_dir}")
            
        except Exception as e:
            logger.error(f"Failed to trigger auto analysis for {base_dir}: {e}")
            
    def get_monitoring_status(self) -> Dict:
        """获取监听状态"""
        return {
            "is_running": self.is_running,
            "monitored_directories": list(self.monitored_directories),
            "file_counts": self.file_counts.copy(),
            "last_analysis_times": {
                path: time.isoformat() for path, time in self.last_analysis_time.items()
            }
        }


class DirectoryEventHandler(FileSystemEventHandler):
    """文件系统事件处理器"""
    
    def __init__(self, base_dir: str, monitor_service: DirectoryMonitorService):
        super().__init__()
        self.base_dir = base_dir
        self.monitor_service = monitor_service
        self.last_event_time = 0
        self.event_debounce = 2.0  # 事件防抖时间（秒）
        
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and self._is_target_file(event.src_path):
            self._handle_event("created", event.src_path)
            
    def on_deleted(self, event):
        """文件删除事件"""
        if not event.is_directory and self._is_target_file(event.src_path):
            self._handle_event("deleted", event.src_path)
            
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory:
            # 检查源文件或目标文件是否为目标类型
            if self._is_target_file(event.src_path) or self._is_target_file(event.dest_path):
                self._handle_event("moved", f"{event.src_path} -> {event.dest_path}")
                
    def _is_target_file(self, file_path: str) -> bool:
        """检查是否为目标文件类型（PDF或JSON）"""
        return file_path.lower().endswith(('.pdf', '.json'))
        
    def _handle_event(self, event_type: str, file_path: str):
        """处理文件事件"""
        current_time = time.time()
        
        # 事件防抖：避免短时间内重复触发
        if current_time - self.last_event_time < self.event_debounce:
            return
            
        self.last_event_time = current_time
        
        logger.debug(f"File {event_type}: {file_path}")
        
        # 异步处理文件变化
        asyncio.create_task(self.monitor_service._handle_file_change(self.base_dir))


# 全局监听服务实例
directory_monitor = DirectoryMonitorService()


async def start_directory_monitoring(base_dirs: list = None):
    """启动目录监听服务"""
    try:
        await directory_monitor.start_monitoring(base_dirs)
        logger.info("Directory monitoring service started successfully")
    except Exception as e:
        logger.error(f"Failed to start directory monitoring: {e}")


async def stop_directory_monitoring():
    """停止目录监听服务"""
    try:
        await directory_monitor.stop_monitoring()
        logger.info("Directory monitoring service stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop directory monitoring: {e}")


def get_monitoring_status() -> Dict:
    """获取监听状态"""
    return directory_monitor.get_monitoring_status()
