import sys
import os
# 使用OpenAI客户端调用DeepSeek API
from openai import OpenAI
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.resource import ResourceItem
import pathlib
from typing import List, Dict, Tuple
import random
import json
import hashlib
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnalysisTask:
    def __init__(self, task_id):
        self.task_id = task_id
        self.status = "pending"  # pending, running, completed, failed
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = time.time()
        self.is_auto_analysis = False  # 默认不是自动分析任务

class ResourceService:
    """资源服务类"""
    
    # 缓存分类结果，避免频繁请求大模型API
    _cache = {}
    _cache_time = None
    _cache_duration = timedelta(hours=1)  # 缓存有效期1小时
    
    # 存储任务状态的字典
    _analysis_tasks = {}
    
    # 添加类变量用于存储自动分析的结果
    _auto_analysis_result = None
    _auto_analysis_time = None
    _auto_analysis_running = False

    @staticmethod
    async def get_resource_data() -> list[ResourceItem]:
        """获取资源数据列表"""
        # 直接返回自动分析结果
        auto_analysis_result = await ResourceService.get_auto_analysis_result()
        if auto_analysis_result:
            return auto_analysis_result
        
        # 如果自动分析结果为空，则使用原有逻辑
        # 检查缓存是否有效
        now = datetime.now()
        if (ResourceService._cache and ResourceService._cache_time and 
            now - ResourceService._cache_time < ResourceService._cache_duration):
            logger.info("Using cached resource data")
            return ResourceService._cache
        
        # 扫描目录路径 (可以从配置文件读取)
        base_dir = os.path.join(os.path.expanduser("~"), "Documents")
        
        # 收集文件夹信息
        folder_info = await ResourceService._collect_folder_info(base_dir)
        
        # 智能分析文件夹并生成分类
        categories = await ResourceService._analyze_and_categorize_folders(folder_info)
        
        # 统计各类资源数量
        result = []
        for i, (category, folders) in enumerate(categories.items(), 1):
            # 为每个分类生成一个稳定的颜色
            color = ResourceService._generate_color(category)
            # 为每个分类选择一个合适的图标
            icon = ResourceService._select_icon(category)
            
            result.append(
                ResourceItem(
                    id=i,
                    name=category,
                    count=len(folders),
                    icon=icon,
                    color=color
                )
            )
        
        # 如果没有找到任何资源，返回默认数据
        if not result:
            result = [
                ResourceItem(id=1, name="文档", count=0, icon="📄", color="#1890ff"),
                ResourceItem(id=2, name="图像", count=0, icon="🖼️", color="#52c41a"),
                ResourceItem(id=3, name="音频", count=0, icon="🎵", color="#722ed1"),
                ResourceItem(id=4, name="视频", count=0, icon="🎬", color="#faad14"),
                ResourceItem(id=5, name="数据", count=0, icon="📊", color="#13c2c2"),
            ]
        
        # 更新缓存
        ResourceService._cache = result
        ResourceService._cache_time = now
        
        return result
    
    @staticmethod
    async def _collect_folder_info(base_dir: str) -> List[Dict]:
        """收集目录中的文件夹信息"""
        folder_info = []
        
        # 如果是C盘路径，直接返回空列表
        if base_dir.startswith("C:"):
            logger.info(f"Skipping C: drive path: {base_dir}")
            return folder_info
            
        try:
            # 遍历目录，只收集文件夹
            for root, dirs, _ in os.walk(base_dir):
                for dir_name in dirs:
                    # 跳过隐藏目录、系统目录和C盘路径
                    if dir_name.startswith('.') or dir_name.startswith('$') or root.startswith("C:"):
                        continue
                    
                    dir_path = os.path.join(root, dir_name)
                    try:
                        # 获取文件夹信息
                        dir_stat = os.stat(dir_path)
                        
                        # 计算文件夹深度
                        depth = len(os.path.relpath(dir_path, base_dir).split(os.sep))
                        
                        # 收集文件夹信息
                        folder_info.append({
                            'name': dir_name,
                            'path': dir_path,
                            'depth': depth,
                            'modified': datetime.fromtimestamp(dir_stat.st_mtime).isoformat(),
                            'relative_path': os.path.relpath(dir_path, base_dir)
                        })
                    except (PermissionError, FileNotFoundError) as e:
                        logger.warning(f"Error accessing folder {dir_path}: {e}")
        except Exception as e:
            logger.error(f"Error scanning directory {base_dir}: {e}")
        
        return folder_info
    
    @staticmethod
    async def _analyze_and_categorize_folders(folder_info: List[Dict]) -> Dict[str, List[Dict]]:
        """分析文件夹并生成分类"""
        # 直接使用基于文件夹名称的智能分类
        return ResourceService._smart_categorize_folders(folder_info)
    
    @staticmethod
    def _smart_categorize_folders(folder_info: List[Dict]) -> Dict[str, List[Dict]]:
        """基于文件夹名称的智能分类方法"""
        categories = {}
        
        # 动态生成分类规则，而不是使用预定义的分类
        category_rules = {}
        
        # 从文件夹名称中提取关键词
        keywords_freq = {}
        for folder in folder_info:
            folder_name = folder['name'].lower()
            # 分割文件夹名称为单词
            words = re.findall(r'[a-zA-Z\u4e00-\u9fa5]+', folder_name)
            for word in words:
                if len(word) > 2:  # 忽略太短的词
                    keywords_freq[word] = keywords_freq.get(word, 0) + 1
        
        # 选择出现频率较高的关键词作为分类依据
        top_keywords = sorted(keywords_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # 根据关键词生成分类
        for keyword, _ in top_keywords:
            # 避免重复的分类
            if any(keyword in existing_keywords for existing_keywords in category_rules.values()):
                continue
                
            # 创建新的分类
            category_name = f"{keyword}相关文件"
            category_rules[category_name] = [keyword]
            
            # 如果分类数量达到10个，停止添加
            if len(category_rules) >= 5:
                break
        
        # 如果没有足够的分类，添加一些通用分类
        if len(category_rules) < 5:
            default_categories = {
                "文档资料": ["doc", "pdf", "txt", "文档", "资料"],
                "媒体文件": ["media", "photo", "video", "music", "媒体", "照片", "视频", "音乐"],
                "开发项目": ["code", "dev", "src", "代码", "开发", "源码"],
                "系统文件": ["system", "config", "系统", "配置"],
                "其他文件": ["other", "misc", "其他", "杂项"]
            }
            
            for category, keywords in default_categories.items():
                if category not in category_rules:
                    category_rules[category] = keywords
        
        # 为每个文件夹分类
        for folder in folder_info:
            folder_name = folder['name'].lower()
            folder_path = folder['relative_path'].lower()
            
            # 寻找最佳匹配的分类
            best_category = None
            best_score = 0
            
            for category, keywords in category_rules.items():
                score = 0
                
                # 检查文件夹名称中的关键词
                for keyword in keywords:
                    if keyword in folder_name:
                        score += 3  # 文件夹名称匹配权重更高
                    if keyword in folder_path:
                        score += 1  # 路径匹配权重较低
                
                # 更新最佳匹配
                if score > best_score:
                    best_score = score
                    best_category = category
            
            # 如果没有找到匹配的分类，根据文件夹名称特征判断
            if not best_category:
                best_category = ResourceService._classify_by_name_pattern(folder_name)
            
            # 如果还是没有分类，归为"其他文件夹"
            if not best_category:
                best_category = "其他文件夹"
            
            # 添加到分类中
            if best_category not in categories:
                categories[best_category] = []
            categories[best_category].append(folder)
        
        # 限制分类数量，合并小分类
        if len(categories) > 8:
            # 按文件夹数量排序
            sorted_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
            
            # 保留前7个最大的分类
            main_categories = dict(sorted_categories[:7])
            
            # 将剩余的小分类合并为"其他文件夹"
            other_folders = []
            for category, folders in sorted_categories[7:]:
                other_folders.extend(folders)
            
            if other_folders:
                main_categories["其他文件夹"] = other_folders
            
            categories = main_categories
        
        return categories
    
    @staticmethod
    def _classify_by_name_pattern(folder_name: str) -> str:
        """根据文件夹名称模式进行分类"""
        # 数字开头的文件夹（可能是日期或版本）
        if re.match(r'^\d+', folder_name):
            return "版本或日期文件夹"
        
        # 包含日期格式的文件夹
        if re.search(r'\d{4}[-_]\d{2}[-_]\d{2}', folder_name):
            return "日期文件夹"
        
        # 全大写的文件夹（可能是缩写或系统文件夹）
        if folder_name.isupper() and len(folder_name) <= 10:
            return "系统或缩写文件夹"
        
        # 包含特殊字符的文件夹
        if re.search(r'[._-]', folder_name):
            return "特殊格式文件夹"
        
        # 很长的文件夹名（可能是自动生成的）
        if len(folder_name) > 30:
            return "自动生成文件夹"
        
        return None
    
    @staticmethod
    def _generate_color(category: str) -> str:
        """为分类生成一个稳定的颜色"""
        # 使用分类名称的哈希值生成颜色，确保同一分类总是得到相同的颜色
        hash_obj = hashlib.md5(category.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # 生成柔和的颜色
        r = (hash_int & 0xFF0000) >> 16
        g = (hash_int & 0x00FF00) >> 8
        b = hash_int & 0x0000FF
        
        # 确保颜色不会太暗
        r = max(r, 100)
        g = max(g, 100)
        b = max(b, 100)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def _select_icon(category: str) -> str:
        """为分类选择一个合适的图标"""
        # 定义分类和图标的映射
        category_icons = {
            "工作文档": "💼",
            "学习资料": "📚",
            "个人文件": "👤",
            "开发项目": "💻",
            "媒体文件": "🎬",
            "下载文件": "📥",
            "系统文件": "⚙️",
            "娱乐内容": "🎮",
            "财务资料": "💰",
            "健康医疗": "🏥",
            "版本或日期文件夹": "📅",
            "日期文件夹": "📅",
            "系统或缩写文件夹": "🔤",
            "特殊格式文件夹": "📝", 
            "自动生成文件夹": "🤖",
            "其他文件夹": "📁"
        }
        
        # 尝试精确匹配
        if category in category_icons:
            return category_icons[category]
        
        # 尝试部分匹配
        for key, icon in category_icons.items():
            if key in category or category in key:
                return icon
        
        # 默认图标
        return "📁"

    @staticmethod
    async def start_analysis_task(base_dir: str, file_list=None, options=None) -> str:
        """启动异步分析任务
        
        Args:
            base_dir: 基础目录路径
            file_list: 文件列表，如果提供则只分析这些文件
            options: 其他选项
        
        Returns:
            str: 任务ID
        """
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 如果目录为空或不存在，使用默认目录
        if not base_dir or not os.path.exists(base_dir):
            base_dir = os.path.join(os.path.expanduser("~"), "Documents")
        
        # 创建任务对象
        task = AnalysisTask(task_id)
        # 使用类变量存储任务
        ResourceService._analysis_tasks[task_id] = task
        
        # 启动异步任务
        asyncio.create_task(ResourceService._run_analysis_task(task, base_dir, file_list, options))
        
        return task_id

    @staticmethod
    async def get_task_status(task_id: str) -> Dict:
        """获取任务状态"""
        # 添加调试日志
        logger.info(f"Getting task status for task_id: {task_id}")
        logger.info(f"Available tasks: {list(ResourceService._analysis_tasks.keys())}")
        
        task = ResourceService._analysis_tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return {"status": "not_found"}
        
        result = {
            "status": task.status,
            "progress": task.progress
        }
        
        # 如果任务完成，返回结果
        if task.status == "completed":
            result["result"] = task.result
        elif task.status == "failed":
            result["error"] = str(task.error)
        
        # 计算运行时间
        result["elapsed_time"] = time.time() - task.start_time
        
        logger.info(f"Task status: {result}")
        return result

    @staticmethod
    async def _run_analysis_task(task: AnalysisTask, base_dir: str, file_list=None, options=None):
        """运行分析任务"""
        try:
            task.status = "running"
            task.progress = 5
            
            if file_list:
                logger.info(f"Using provided file list with {len(file_list)} files")
                
                # 处理文件列表，按文件夹分组
                folder_structure = {}
                for file in file_list:
                    path = file["path"]
                    # 提取文件所在的文件夹路径
                    folder_path = os.path.dirname(path)
                    
                    if not folder_path:
                        folder_path = "根目录"
                    
                    if folder_path not in folder_structure:
                        folder_structure[folder_path] = []
                    
                    folder_structure[folder_path].append(file)
                
                # 直接使用文件夹名称作为分类
                categories = {}
                for folder_path, files in folder_structure.items():
                    folder_name = os.path.basename(folder_path)
                    if not folder_name:
                        folder_name = os.path.basename(os.path.dirname(folder_path))
                    if not folder_name:
                        folder_name = "其他"
                    
                    if folder_name not in categories:
                        categories[folder_name] = []
                    
                    categories[folder_name].extend(files)
                
                task.progress = 90
            else:
                # 收集文件夹信息
                folder_info = await ResourceService._collect_folder_info(base_dir)
                task.progress = 50
                
                # 智能分析文件夹并生成分类
                categories = ResourceService._smart_categorize_folders(folder_info)
                task.progress = 90
            
            # 构建最终结果
            result = []
            for category, items in categories.items():
                result.append({
                    "id": len(result) + 1,
                    "name": category,
                    "count": len(items),
                    "icon": ResourceService._select_icon(category),
                    "color": ResourceService._generate_color(category),
                    "folders": items if not file_list else []  # 如果是文件列表分析，不返回文件夹
                })
            
            # 更新任务状态
            task.status = "completed"
            task.progress = 100
            task.result = result
            
            # 更新缓存
            ResourceService._cache = result
            ResourceService._cache_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Analysis task failed: {e}")
            task.status = "failed"
            task.error = e

    @staticmethod
    async def auto_analyze_local_directories():
        """自动分析本地文件夹"""
        print("自动分析本地文件夹",ResourceService._auto_analysis_running)
        # 防止重复运行
        if ResourceService._auto_analysis_running:
            logger.info("Auto analysis already running, skipping")
            return
        
        try:
            # 设置运行标志
            ResourceService._auto_analysis_running = True
            logger.info("Starting automatic analysis of local directories")
            
            # 获取用户主目录
            home_dir = os.path.expanduser("~")
            
            # 直接添加D盘、E盘、F盘等非C盘目录
            drive_dirs = []
            for drive_letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
                drive_path = f"{drive_letter}:\\"
                if os.path.exists(drive_path):
                    logger.info(f"Found drive: {drive_path}")
                    drive_dirs.append(drive_path)
            
            # 如果找到了其他驱动器，使用它们代替home_dir
            if drive_dirs:
                logger.info(f"Using drives: {drive_dirs} instead of home directory")
                common_dirs = []  # 初始化为空列表
                
                # 为每个驱动器收集目录
                for drive in drive_dirs:
                    try:
                        # 添加驱动器根目录
                        common_dirs.append(drive)
                        
                        # 添加第一层目录
                        with os.scandir(drive) as entries:
                            for entry in entries:
                                if entry.is_dir() and not entry.name.startswith('.'):
                                    common_dirs.append(entry.path)
                    except Exception as e:
                        logger.error(f"Error scanning drive {drive}: {e}")
            else:
                logger.info(f"No additional drives found, using home directory: {home_dir}")
                common_dirs = []  # 初始化为空列表
                
                # 不使用预定义目录，而是动态获取用户目录下的所有子目录（最大3层）
                try:
                    # 添加第一层目录，但跳过C盘路径
                    with os.scandir(home_dir) as entries:
                        for entry in entries:
                            if entry.is_dir() and not entry.name.startswith('.'):
                                # 跳过C盘路径
                                if entry.path.startswith("C:"):
                                    logger.info(f"Skipping C: drive path: {entry.path}")
                                    continue
                                common_dirs.append(entry.path)
                except Exception as e:
                    logger.error(f"Error scanning home directory: {e}")
            
            # 收集存在的目录，排除C盘路径
            existing_dirs = [d for d in common_dirs if os.path.exists(d) and os.path.isdir(d) and not d.startswith("C:")]
            logger.info(f"After filtering, {len(existing_dirs)} directories remain")
            
            # 如果没有找到任何目录，添加用户主目录（如果不在C盘）
            if not existing_dirs and not home_dir.startswith("C:"):
                existing_dirs.append(home_dir)
                logger.info(f"No directories found, using home directory: {home_dir}")
            
            # 如果仍然没有目录，创建一个空结果
            if not existing_dirs:
                logger.warning("No valid directories found for analysis")
                # 创建一个空结果
                ResourceService._auto_analysis_result = []
                ResourceService._auto_analysis_time = datetime.now()
                ResourceService._auto_analysis_running = False
                return
            
            # 创建分析任务
            task_id = str(uuid.uuid4())
            task = AnalysisTask(task_id)
            task.is_auto_analysis = True  # 明确标记为自动分析任务
            ResourceService._analysis_tasks[task_id] = task
            logger.info(f"Created auto analysis task with ID: {task_id}")
            # logger.info(f"existing_dirs: {existing_dirs}")
            # 运行分析任务
            await ResourceService._run_auto_analysis(task, existing_dirs)
            
            # 存储结果
            if task.status == "completed":
                # 缓存分析结果
                ResourceService._auto_analysis_result = task.result
                ResourceService._auto_analysis_time = datetime.now()
                
                # 将结果保存到本地文件，以便服务重启后仍能使用
                try:
                    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
                    os.makedirs(cache_dir, exist_ok=True)
                    
                    cache_file = os.path.join(cache_dir, "auto_analysis_cache.json")
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "result": task.result,
                            "timestamp": datetime.now().isoformat()
                        }, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"Cached analysis result to {cache_file}")
                except Exception as e:
                    logger.error(f"Failed to cache analysis result: {e}")
                
                logger.info(f"Automatic analysis completed with {len(task.result)} categories")
            else:
                logger.error(f"Automatic analysis failed: {task.error}")
        
        except Exception as e:
            logger.error(f"Error in automatic analysis: {e}")
        finally:
            # 确保在函数结束时重置运行标志
            ResourceService._auto_analysis_running = False
            logger.info("Auto analysis completed, reset running flag to False")

    @staticmethod
    async def _run_auto_analysis(task: AnalysisTask, directories: List[str]):
        """运行自动分析任务 - 基于文件夹进行智能分类"""
        try:
            task.status = "running"
            task.progress = 5
            
            # 检查目录列表是否为空
            if not directories:
                logger.warning("No directories to analyze")
                task.status = "completed"
                task.progress = 100
                task.result = []  # 返回空结果
                return
            
            # 收集所有目录下的文件夹信息
            all_folder_info = []
            
            for i, directory in enumerate(directories):
                try:
                    logger.info(f"Processing directory {i+1}/{len(directories)}: {directory}")
                    # 使用并行处理替代单线程收集文件夹信息
                    # 创建一个有限深度的文件夹收集函数
                    folder_info = await ResourceService._collect_folder_info_limited(directory, max_depth=2)
                    all_folder_info.extend(folder_info)
                    
                    # 更新进度
                    task.progress = 5 + int((i + 1) / len(directories) * 50)
                    logger.info(f"Collected {len(folder_info)} folders from {directory}")
                except Exception as e:
                    logger.error(f"Error processing directory {directory}: {e}")
                    continue
            
            logger.info(f"Total folders collected: {len(all_folder_info)}")
            
            # 如果没有收集到任何文件夹信息，返回空结果
            if not all_folder_info:
                logger.warning("No folder information collected")
                task.status = "completed"
                task.progress = 100
                task.result = []
                return
            
            # 优先使用大模型分析文件夹并生成分类
            try:
                # 尝试使用DeepSeek大模型分析
                categories = await ResourceService._analyze_with_deepseek(all_folder_info)
                logger.info("Successfully used DeepSeek model for folder categorization")
            except Exception as e:
                # 如果大模型分析失败，回退到原有的分析方法
                logger.warning(f"DeepSeek analysis failed: {e}, falling back to basic categorization")
                categories = ResourceService._smart_categorize_folders(all_folder_info)
            task.progress = 90
            
            # 构建最终结果
            result = []
            for category, folders in categories.items():
                result.append({
                    "id": len(result) + 1,
                    "name": category,
                    "count": len(folders),
                    "icon": ResourceService._select_icon(category),
                    "color": ResourceService._generate_color(category),
                    "folders": folders[:50]  # 限制文件夹数量，避免返回过多数据
                })
            
            logger.info(f'Auto analysis result: {len(result)} categories')
            
            # 更新任务状态
            task.status = "completed"
            task.progress = 100
            task.result = result
        except Exception as e:
            logger.error(f"Auto analysis task failed: {e}")
            task.status = "failed"
            task.error = str(e)

    @staticmethod
    async def get_auto_analysis_result():
        """获取自动分析结果"""
        # 如果内存中有结果且未过期，直接返回
        if (ResourceService._auto_analysis_result is not None and 
            ResourceService._auto_analysis_time is not None and
            datetime.now() - ResourceService._auto_analysis_time < timedelta(hours=24)):
            logger.info("Using in-memory auto analysis result")
            return ResourceService._auto_analysis_result
        
        # 如果内存中没有结果或已过期，尝试从缓存文件加载
        try:
            cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "auto_analysis_cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                
                # 修复这一行，使用正确的logger.error格式
                logger.info(f"ResourceService auto analysis result: {ResourceService._auto_analysis_result}")
                
                # 检查缓存是否过期（24小时）
                cache_time = datetime.fromisoformat(cache_data["timestamp"])
                if datetime.now() - cache_time < timedelta(hours=24):
                    logger.info("Loaded auto analysis result from cache file")
                    ResourceService._auto_analysis_result = cache_data["result"]
                    ResourceService._auto_analysis_time = cache_time
                    return ResourceService._auto_analysis_result
        except Exception as e:
            logger.error(f"Failed to load cached analysis result: {e}")
        
        # 如果没有有效的缓存，重新分析
        logger.info("No valid cache found, starting new auto analysis")
        await ResourceService.auto_analyze_local_directories()
        
        return ResourceService._auto_analysis_result

    @staticmethod
    async def get_cached_analysis_result():
        """只获取缓存的分析结果，不触发新的分析"""
        # 清空内存缓存
        ResourceService._auto_analysis_result = None
        ResourceService._auto_analysis_time = None
        
        # 检查文件缓存
        try:
            cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "auto_analysis_cache.json")
            if os.path.exists(cache_file):
                # 清空文件缓存
                os.remove(cache_file)
                logger.info(f"Removed cache file: {cache_file}")
                return None
        except Exception as e:
            logger.error(f"Failed to remove cached analysis result: {e}")
        
        # 如果没有有效的缓存，返回None
        return None

    @staticmethod
    async def _collect_folder_info_limited(base_dir: str, max_depth: int = 2) -> List[Dict]:
        """收集目录中的文件夹信息，限制深度以提高性能"""
        folder_info = []
        
        # 如果是C盘路径，直接返回空列表
        if base_dir.startswith("C:"):
            logger.info(f"Skipping C: drive path: {base_dir}")
            return folder_info
        
        # 使用异步执行以避免阻塞
        loop = asyncio.get_event_loop()
        
        def scan_directory(dir_path, current_depth=0):
            """递归扫描目录，但限制深度"""
            results = []
            
            if current_depth > max_depth:
                return results
            
            try:
                # 使用os.scandir更高效地扫描目录
                with os.scandir(dir_path) as entries:
                    for entry in entries:
                        try:
                            # 只处理目录
                            if entry.is_dir():
                                # 跳过隐藏目录和系统目录
                                if entry.name.startswith('.') or entry.name.startswith('$'):
                                    continue
                                
                                # 获取文件夹信息
                                dir_stat = entry.stat()
                                
                                # 计算文件夹深度
                                depth = current_depth + 1
                                
                                # 收集文件夹信息
                                results.append({
                                    'name': entry.name,
                                    'path': entry.path,
                                    'depth': depth,
                                    'modified': datetime.fromtimestamp(dir_stat.st_mtime).isoformat(),
                                    'relative_path': os.path.relpath(entry.path, base_dir)
                                })
                                
                                # 如果深度未达到最大值，继续递归
                                if depth < max_depth:
                                    results.extend(scan_directory(entry.path, depth))
                        except (PermissionError, FileNotFoundError) as e:
                            # 忽略权限错误和文件不存在错误
                            continue
                        except Exception as e:
                            logger.warning(f"Error processing entry {entry.path}: {e}")
            except Exception as e:
                logger.warning(f"Error scanning directory {dir_path}: {e}")
            
            return results
        
        # 在线程池中执行目录扫描
        try:
            # 使用线程池执行IO密集型操作
            with ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) * 4)) as executor:
                folder_info = await loop.run_in_executor(executor, scan_directory, base_dir)
        except Exception as e:
            logger.error(f"Error in folder collection for {base_dir}: {e}")
        
        return folder_info

    @staticmethod
    async def _analyze_with_deepseek(folder_info: List[Dict]) -> Dict[str, List[Dict]]:
        """使用DeepSeek大模型分析文件夹并生成分类"""
        try:
            # DeepSeek API配置
            api_url = "https://api.deepseek.com/v1"
            # api_key = os.environ.get("DEEPSEEK_API_KEY")
            api_key ='sk-0c98c2a93954490aab152eeec9da1601'
            if not api_key:
                logger.error("DeepSeek API key not found in environment variables")
                raise ValueError("DeepSeek API key not found")
            
            # 限制样本数量，避免请求过大
            sample_size = min(100, len(folder_info))
            sample_folders = random.sample(folder_info, sample_size) if len(folder_info) > sample_size else folder_info
            
            # 构建提示词
            prompt = f"""
            请分析以下文件夹列表，并根据文件夹名称和路径将它们分类到适当的类别中。
            请创建有意义的类别，这些类别应该反映文件夹的实际内容和用途。
            例如，"项目文档"、"学习资料"、"工作文件"等。

            文件夹列表:
            {json.dumps([{'name': f['name'], 'path': f['path']} for f in sample_folders], ensure_ascii=False, indent=2)}

            请以JSON格式返回分类结果，格式为:
            {{
                "类别1": [文件夹索引列表],
                "类别2": [文件夹索引列表],
                ...
            }}
            其中文件夹索引是文件夹在提供的列表中的位置（从0开始）。

            请确保创建的类别数量在3-7个之间，并且每个类别都有明确的主题。
            """
            
            # 准备请求数据
            request_data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的文件分类助手，擅长根据文件夹名称和路径对文件夹进行语义分类。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            
            # 创建客户端实例
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
            
            # 发送请求
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的文件分类助手，擅长根据文件夹名称和路径对文件夹进行语义分类。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    stream=False
                )
                
                # 提取模型回复
                model_response = response.choices[0].message.content
                print('model_response',model_response)
            except Exception as e:
                logger.error(f"Error in DeepSeek analysis: {e}")
                raise

            # 从回复中提取JSON部分
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', model_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = model_response
            
            # 尝试解析JSON
            try:
                # 清理JSON字符串，移除可能的非JSON内容
                json_str = re.sub(r'[^\{\}\[\]\,\:\"\d\s\w\.\-\_\u4e00-\u9fa5]', '', json_str)
                category_indices = json.loads(json_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from model response: {model_response}")
                raise Exception("Failed to parse JSON from model response")
            
            # 将索引映射回文件夹对象
            categories = {}
            for category, indices in category_indices.items():
                categories[category] = []
                for idx in indices:
                    if 0 <= idx < len(sample_folders):
                        # 找到原始文件夹对象
                        folder_name = sample_folders[idx]['name']
                        # 将所有具有相同或相似名称的文件夹添加到此类别
                        for folder in folder_info:
                            if folder['name'] == folder_name or folder['name'].lower() in folder_name.lower() or folder_name.lower() in folder['name'].lower():
                                categories[category].append(folder)
            
            # 处理未分类的文件夹
            all_categorized_folders = set()
            for folders in categories.values():
                for folder in folders:
                    all_categorized_folders.add(folder['path'])
            
            uncategorized = []
            for folder in folder_info:
                if folder['path'] not in all_categorized_folders:
                    uncategorized.append(folder)
            
            # 如果有未分类的文件夹，添加"其他文件夹"类别
            if uncategorized:
                categories["其他文件夹"] = uncategorized
            
            return categories
        except Exception as e:
            logger.error(f"Error in DeepSeek analysis: {e}")
            raise
