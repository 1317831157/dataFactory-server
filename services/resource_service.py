import sys
import os
# 使用OpenAI客户端调用DeepSeek API
from openai import OpenAI
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.resource import ResourceItem
import pathlib
from typing import List, Dict, Tuple, Any
import random
import json
import hashlib
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
import re
from bson import ObjectId
import concurrent.futures
import multiprocessing
from services.database import DataSource, Task
from pymongo import UpdateOne
# 导入配置
from config import config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_files_mp(base_dir):
    result = []
    try:
        for root, _, files in os.walk(base_dir):
            for file in files:
                # ".json"
                if file.lower().endswith((".pdf")):
                    result.append(os.path.join(root, file))
    except Exception as e:
        print(f"Error walking {base_dir}: {e}")
    print(f"Finish scanning: {base_dir}, found {len(result)} files")
    return result

def get_all_dirs(base_dirs, max_depth=1):
    # 递归收集所有子目录，限制最大深度
    all_dirs = []
    for base in base_dirs:
        for root, dirs, _ in os.walk(base):
            depth = root[len(base):].count(os.sep)
            if depth <= max_depth:
                all_dirs.append(root)
    return all_dirs

class ResourceService:
    """资源服务类 - 使用MongoDB进行任务管理"""
    
    # 缓存分类结果，避免频繁请求大模型API
    _cache = {}
    _cache_time = None
    _cache_duration = timedelta(hours=1)  # 缓存有效期1小时
    
    # 添加类变量用于存储自动分析的结果
    _auto_analysis_result = None
    _auto_analysis_time = None
    _auto_analysis_running = False

    # 添加任务跟踪字典
    _analysis_tasks = {}

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
        """
        只分析pdf和json文件的文件名（不分析文件夹名），将文件夹归入五大类。
        如果没有命中任何类别，则该文件夹被过滤掉。
        """
        categories = {"学术论文": [], "调查报告": [], "专业书籍": [], "政策文件": [], "法规标准": []}
        # 关键词映射
        keyword_map = {
            "学术论文": ["paper", "论文", "thesis", "article"],
            "调查报告": ["report", "调查", "survey"],
            "专业书籍": ["book", "专著", "教材", "manual", "handbook"],
            "政策文件": ["policy", "政策", "guideline", "规划"],
            "法规标准": ["regulation", "标准", "规范", "law", "条例"]
        }

        for folder in folder_info:
            folder_path = folder['path']
            file_type_count = {k: 0 for k in categories}
            # 遍历该文件夹下所有pdf/json文件
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if not file.lower().endswith(('.pdf', '.json')):
                        continue
                    fname = file.lower()
                    for cat, keywords in keyword_map.items():
                        if any(kw in fname for kw in keywords):
                            file_type_count[cat] += 1
                            break  # 命中一个类别就不再继续
            # 该文件夹的分类由最多的那一类决定
            total_hits = sum(file_type_count.values())
            if total_hits == 0:
                continue  # 该文件夹下没有命中任何类别的pdf/json文件，跳过
            main_cat = max(file_type_count, key=lambda k: file_type_count[k])
            categories[main_cat].append(folder)
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
        """启动异步分析任务，并将任务状态存入数据库"""
        # 如果目录为空或不存在，使用默认目录
        if not base_dir or not os.path.exists(base_dir):
            base_dir = os.path.join(os.path.expanduser("~"), "Documents")
        
        # 创建任务并存入数据库
        task = Task(
            task_type="resource_analysis",
            related_id=base_dir # 使用基础目录作为关联ID
        )
        await task.insert()
        
        # 启动异步任务, task.id 是 ObjectId, 需要转为 str
        asyncio.create_task(ResourceService._run_analysis_task(str(task.id), base_dir, file_list, options))
        
        return str(task.id)

    @staticmethod
    async def get_task_status(task_id: str) -> Dict:
        """从数据库获取任务状态"""
        try:
            # Beanie's get method uses Pydantic's ObjectId, so we must convert the string
            task = await Task.get(ObjectId(task_id))
        except Exception:
            # This can happen if the task_id is not a valid ObjectId format
            logger.warning(f"Task not found or invalid ID format: {task_id}")
            return {"status": "not_found", "error": "Invalid ID format"}
        
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return {"status": "not_found"}
        
        # 使用 model_dump 返回 Pydantic 模型兼容的字典
        return task.model_dump(by_alias=True, exclude={'id'})

    @staticmethod
    async def _run_analysis_task(task_id: str, base_dir: str, file_list=None, options=None):
        """运行分析任务，并更新数据库中的任务状态"""
        task_obj_id = ObjectId(task_id)
        try:
            await Task.find_one(Task.id == task_obj_id).update({"$set": {"status": "running", "progress": 5}})
            
            if file_list:
                logger.info(f"Using provided file list with {len(file_list)} files")
                
                folder_structure = {}
                for file in file_list:
                    path = file["path"]
                    folder_path = os.path.dirname(path)
                    
                    if not folder_path: folder_path = "根目录"
                    if folder_path not in folder_structure: folder_structure[folder_path] = []
                    folder_structure[folder_path].append(file)
                
                categories = {}
                for folder_path, files in folder_structure.items():
                    folder_name = os.path.basename(folder_path)
                    if not folder_name: folder_name = os.path.basename(os.path.dirname(folder_path))
                    if not folder_name: folder_name = "其他"
                    if folder_name not in categories: categories[folder_name] = []
                    categories[folder_name].extend(files)
                
                task_progress = 90
            else:
                folder_info = await ResourceService._collect_folder_info(base_dir)
                await Task.find_one(Task.id == task_obj_id).update({"$set": {"progress": 50}})
                
                categories = ResourceService._smart_categorize_folders(folder_info)
                task_progress = 90
            
            await Task.find_one(Task.id == task_obj_id).update({"$set": {"progress": task_progress}})

            result = []
            for category, items in categories.items():
                result.append({
                    "id": len(result) + 1, "name": category, "count": len(items),
                    "icon": ResourceService._select_icon(category), "color": ResourceService._generate_color(category),
                    "folders": items if not file_list else []
                })
            
            await Task.find_one(Task.id == task_obj_id).update({"$set": {
                "status": "completed", "progress": 100, 
                "result": {"categories": result}, "end_time": datetime.now()
            }})
            
            ResourceService._cache = result
            ResourceService._cache_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Analysis task failed: {e}", exc_info=True)
            await Task.find_one(Task.id == task_obj_id).update({"$set": {
                "status": "failed", "error": str(e), "end_time": datetime.now()
            }})

    @staticmethod
    async def auto_analyze_local_directories(base_dir=None):
        """递归遍历指定目录，只收集 pdf 和 json 文件，LLM 分类，结果入库（分块递归+多进程优化+动态进度日志）"""
        if ResourceService._auto_analysis_running:
            logger.info("Auto analysis already running, skipping")
            return
        try:
            ResourceService._auto_analysis_running = True
            logger.info("Starting automatic analysis of local directories (recursive, pdf/json only, multiprocess, fine-grained)")

            # 创建任务对象并添加到任务跟踪字典
            task_id = str(uuid.uuid4())
            task_obj = type('AnalysisTask', (), {
                'id': task_id,
                'is_auto_analysis': True,
                'progress': 0,
                'status': 'running',
                'start_time': datetime.now()
            })()
            ResourceService._analysis_tasks[task_id] = task_obj

            import multiprocessing
            # 新增：如果传入 base_dir，则只扫描该目录，否则使用配置中的默认目录
            if base_dir and os.path.exists(base_dir):
                scan_dirs = [base_dir]
            else:
                # 使用配置中的基础目录列表
                config_dirs = config.BASE_PDF_DIRS
                # 过滤出存在的目录
                scan_dirs = [d for d in config_dirs if os.path.exists(d)]

                # 如果配置的目录都不存在，则使用原有逻辑
                if not scan_dirs:
                    home_dir = os.path.expanduser("~")
                    drive_dirs = [f"{d}:\\" for d in "DEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
                    scan_dirs = drive_dirs if drive_dirs else [home_dir]
            common_dirs = [d for d in scan_dirs if not d.startswith("C:")]
            # 递归收集所有子目录（如到2级）
            all_start_dirs = get_all_dirs(common_dirs, max_depth=2)
            logger.info(f"Total start dirs to scan: {len(all_start_dirs)}")
            # 用多进程池动态收集，主进程持续输出进度
            all_files = []
            if all_start_dirs:
                with multiprocessing.get_context("spawn").Pool(processes=min(16, os.cpu_count() or 1)) as pool:
                    total = len(all_start_dirs)
                    for idx, files in enumerate(pool.imap_unordered(collect_files_mp, all_start_dirs), 1):
                        all_files.extend(files)
                        if idx % 10 == 0 or idx == total:
                            logger.info(f"已完成 {idx}/{total} 个目录，累计收集文件数: {len(all_files)}")
            logger.info(f"Total pdf/json files collected文件数量: {len(all_files)}")

            # 更新任务进度：文件收集完成
            if 'task_obj' in locals():
                task_obj.progress = 30
                task_obj.status = 'analyzing'

            # 2. LLM 分类（失败则本地规则）
            try:
                file_dicts = [{'name': os.path.basename(f), 'path': f} for f in all_files]
                categories = await ResourceService._analyze_with_deepseek(file_dicts)

                # 更新任务进度：分析完成
                if 'task_obj' in locals():
                    task_obj.progress = 70
            except Exception as e:
                logger.warning(f"DeepSeek analysis failed: {e}, falling back to basic categorization")
                from services.alert_service import AlertService
                await AlertService.add_alert(
                    message=f"DeepSeek LLM 分类失败: {str(e)}，已切换为本地规则",
                    level="warning",
                    extra={"task_type": "auto_resource_analysis"}
                )
                categories = ResourceService._smart_categorize_folders(
                    [{'name': os.path.basename(f), 'path': f} for f in all_files]
                )

            # 3. 整理分类结果
            result = [
                {"id": i + 1, "name": cat, "count": len(files),
                 "icon": ResourceService._select_icon(cat), "color": ResourceService._generate_color(cat),
                 "files": files[:50]}
                for i, (cat, files) in enumerate(categories.items())
            ]
            # 4. 写入数据库
            from services.alert_service import AlertService
            existing_task = await Task.find_one(Task.task_type == "auto_resource_analysis")
            if existing_task:
                await Task.find_one(Task.id == existing_task.id).update({
                    "$set": {
                        "status": "completed",
                        "progress": 100,
                        "result": {"categories": result},
                        "end_time": datetime.now()
                    }
                })
            else:
                new_task = Task(task_type="auto_resource_analysis", status="completed", start_time=datetime.now(), end_time=datetime.now(), result={"categories": result})
                await new_task.insert()
            logger.info("Auto analysis completed and categories saved to DB.")

            # 更新任务进度：数据保存完成
            if 'task_obj' in locals():
                task_obj.progress = 90

            # 动态导入，避免循环依赖
            try:
                from services.auto_paper_import_service import AutoPaperImportService
                imported_count = await AutoPaperImportService.import_valid_papers_from_auto_analysis()
                logger.info(f"自动分析后已导入 {imported_count} 篇有效论文。")

                # 更新任务进度：全部完成
                if 'task_obj' in locals():
                    task_obj.progress = 100
                    task_obj.status = 'completed'

            except Exception as e:
                logger.error(f"自动导入有效论文失败: {e}")

        except Exception as e:
            logger.error(f"Error in automatic analysis: {e}")
            from services.alert_service import AlertService
            await AlertService.add_alert(
                message=f"自动分析任务异常: {str(e)}",
                level="error",
                extra={"task_type": "auto_resource_analysis"}
            )
        finally:
            ResourceService._auto_analysis_running = False
            # 清理任务跟踪
            if 'task_id' in locals():
                if task_id in ResourceService._analysis_tasks:
                    ResourceService._analysis_tasks[task_id].status = 'completed'
                    # 可以选择保留任务一段时间或立即删除
                    # del ResourceService._analysis_tasks[task_id]
            logger.info("Auto analysis completed, reset running flag.")

    @staticmethod
    async def get_auto_analysis_result():
        """获取自动分析结果（每次都查数据库，不用内存缓存）"""
        try:
            # 直接从数据库任务中获取最新成功的结果
            task = await Task.find_one(
                Task.task_type == "auto_resource_analysis",
                Task.status == "completed",
                sort=[("end_time", -1)]
            )
            if task and task.end_time and (datetime.now() - task.end_time < timedelta(hours=24)):
                logger.info("Loaded auto analysis result from completed DB task")
                result = task.result.get("categories") if task.result else None
                return result
        except Exception as e:
            logger.error(f"Failed to load analysis result from DB task: {e}")
        
        logger.info("No valid recent task found, starting new auto analysis")
        await ResourceService.auto_analyze_local_directories()
        # 新任务刚启动时还没有结果，这里返回 None 或空
        return None

    @staticmethod
    async def get_cached_analysis_result():
        """只获取缓存的分析结果，不触发新的分析"""
        ResourceService._auto_analysis_result = None
        ResourceService._auto_analysis_time = None
        
        try:
            cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "auto_analysis_cache.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logger.info(f"Removed cache file: {cache_file}")
        except Exception as e:
            logger.error(f"Failed to remove cached analysis result: {e}")
        
        return None

    @staticmethod
    async def _analyze_with_ollama(folder_info: List[Dict]) -> Dict[str, List[Dict]]:
        """使用Ollama本地大模型分析文件夹并生成五大固定分类"""
        try:
            ollama_base_url = config.OLLAMA_BASE_URL
            ollama_model = config.OLLAMA_MODEL

            logger.info(f"Starting Ollama analysis with model: {ollama_model}, URL: {ollama_base_url}")

            # 保持完整的样本数量，不减少
            sample_size = min(100, len(folder_info))
            sample_folders = random.sample(folder_info, sample_size)
            logger.info(f"Processing {sample_size} sample files")

            # 分批处理以提高性能，但保持完整分析
            batch_size = 25  # 每批处理25个文件，减少单次请求的复杂度
            all_categories = {"学术论文": [], "调查报告": [], "专业书籍": [], "政策文件": [], "法规标准": []}

            for batch_start in range(0, len(sample_folders), batch_size):
                batch_end = min(batch_start + batch_size, len(sample_folders))
                batch_folders = sample_folders[batch_start:batch_end]

                logger.info(f"Processing batch {batch_start//batch_size + 1}/{(len(sample_folders) + batch_size - 1)//batch_size}, files {batch_start}-{batch_end-1}")

                # 保持完整的prompt，不简化
                prompt = f"""
你是一个文件分类专家。请根据下列文件的文件名（和路径），将它们严格分类到以下五个类别之一：
1. 学术论文 (Academic Paper)
2. 调查报告 (Survey Report)
3. 专业书籍 (Professional Book)
4. 政策文件 (Policy Document)
5. 法规标准 (Regulation/Standard)

只能用这五个类别，不能有其他类别。请用如下JSON格式返回：
{{
  "学术论文": [文件索引列表],
  "调查报告": [文件索引列表],
  "专业书籍": [文件索引列表],
  "政策文件": [文件索引列表],
  "法规标准": [文件索引列表]
}}
文件列表如下：
{json.dumps([{'index': i, 'name': f['name'], 'path': f['path']} for i, f in enumerate(batch_folders)], ensure_ascii=False, indent=2)}
"""

                # 优化Ollama性能的连接设置
                connector = aiohttp.TCPConnector(
                    limit=5,  # 减少并发连接数
                    limit_per_host=5,
                    keepalive_timeout=600,
                    enable_cleanup_closed=True,
                    use_dns_cache=True,
                    ttl_dns_cache=300
                )

                # 针对Ollama优化的超时设置
                timeout = aiohttp.ClientTimeout(
                    total=1800,      # 30分钟总超时
                    connect=60,      # 1分钟连接超时
                    sock_read=1200   # 20分钟读取超时，给模型充足处理时间
                )

                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    # 优化Ollama性能的payload设置 - 启用流式处理
                    payload = {
                        "model": ollama_model,
                        "messages": [
                            {"role": "system", "content": "你是一个文件分类专家，只能用五个类别分类。请严格按照JSON格式返回结果，不要添加额外说明。"},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": True,  # 启用流式处理
                        "options": {
                            "temperature": 0.1,      # 降低随机性，提高一致性和速度
                            "top_p": 0.8,           # 减少候选token，提高速度
                            "top_k": 20,            # 限制候选数量，提高速度
                            "repeat_penalty": 1.1,  # 避免重复，提高效率
                            "num_predict": -1,      # 不限制输出长度，保证完整分析
                            "num_ctx": 4096,        # 设置合适的上下文长度
                            "num_thread": -1,       # 使用所有可用CPU线程
                            "num_gpu": -1,          # 使用所有可用GPU
                            "low_vram": False       # 如果显存充足，不启用低显存模式
                        }
                    }

                    logger.info(f"Sending streaming batch request to Ollama: {ollama_base_url}/api/chat")

                    try:
                        async with session.post(
                            f"{ollama_base_url}/api/chat",
                            json=payload,
                            headers={'Content-Type': 'application/json'}
                        ) as response:
                            logger.info(f"Ollama streaming batch response status: {response.status}")

                            if response.status != 200:
                                response_text = await response.text()
                                logger.error(f"Ollama API error response: {response_text}")
                                raise Exception(f"Ollama API request failed with status {response.status}: {response_text}")

                            # 异步流式处理响应
                            model_response = ""
                            chunk_count = 0

                            async for line in response.content:
                                if line:
                                    try:
                                        line_str = line.decode('utf-8').strip()
                                        if line_str:
                                            # 解析每个流式响应块
                                            chunk_data = json.loads(line_str)
                                            if "message" in chunk_data and "content" in chunk_data["message"]:
                                                content_chunk = chunk_data["message"]["content"]
                                                model_response += content_chunk
                                                chunk_count += 1

                                                # 每收到10个chunk记录一次进度
                                                if chunk_count % 10 == 0:
                                                    logger.debug(f"Batch {batch_start//batch_size + 1} received {chunk_count} chunks, current length: {len(model_response)}")

                                            # 检查是否完成
                                            if chunk_data.get("done", False):
                                                logger.info(f"Batch {batch_start//batch_size + 1} streaming completed, total chunks: {chunk_count}, final length: {len(model_response)}")
                                                break

                                    except json.JSONDecodeError:
                                        # 跳过无效的JSON行
                                        continue
                                    except Exception as parse_error:
                                        logger.warning(f"Error parsing stream chunk: {parse_error}")
                                        continue

                    except asyncio.TimeoutError:
                        logger.error(f"Ollama streaming batch request timed out for batch {batch_start//batch_size + 1}")
                        raise Exception(f"Ollama batch request timed out")
                    except aiohttp.ClientError as client_error:
                        logger.error(f"Ollama client error in batch {batch_start//batch_size + 1}: {client_error}")
                        raise Exception(f"Ollama client error: {client_error}")
                    except Exception as req_error:
                        logger.error(f"Ollama request error in batch {batch_start//batch_size + 1}: {req_error}")
                        raise

                # 解析批次响应
                if not model_response.strip():
                    logger.warning(f"Empty response from Ollama for batch {batch_start//batch_size + 1}")
                    continue

                # 更强健的JSON提取
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', model_response)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试提取大括号内容
                    json_match = re.search(r'\{[\s\S]*\}', model_response)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = model_response.strip()

                logger.info(f"Batch {batch_start//batch_size + 1} extracted JSON string length: {len(json_str)}")

                try:
                    batch_category_indices = json.loads(json_str)
                    logger.info(f"Batch {batch_start//batch_size + 1} successfully parsed categories")
                except json.JSONDecodeError as json_error:
                    logger.error(f"Batch {batch_start//batch_size + 1} JSON parsing failed: {json_error}")
                    # 尝试修正JSON格式
                    try:
                        # 清理可能的格式问题
                        cleaned_json = re.sub(r'[^\{\}\[\]\,\:\"\d\s\w\.\-\_\u4e00-\u9fa5]', '', json_str)
                        batch_category_indices = json.loads(cleaned_json)
                        logger.info(f"Batch {batch_start//batch_size + 1} successfully parsed cleaned JSON")
                    except:
                        logger.error(f"Batch {batch_start//batch_size + 1} failed to parse even cleaned JSON, skipping batch")
                        continue

                # 将批次结果合并到总结果中
                fixed_categories = ["学术论文", "调查报告", "专业书籍", "政策文件", "法规标准"]

                for cat in fixed_categories:
                    indices = batch_category_indices.get(cat, [])
                    for idx in indices:
                        try:
                            idx_int = int(idx)
                            if 0 <= idx_int < len(batch_folders):
                                all_categories[cat].append(batch_folders[idx_int])
                        except (ValueError, TypeError):
                            continue

                logger.info(f"Batch {batch_start//batch_size + 1} completed, processed {len(batch_folders)} files")

                # 添加批次间的短暂延迟，避免过载Ollama
                if batch_end < len(sample_folders):
                    await asyncio.sleep(1)

            # 统计最终结果
            total_assigned = sum(len(files) for files in all_categories.values())
            logger.info(f"Ollama analysis completed successfully, processed {len(sample_folders)} files in {(len(sample_folders) + batch_size - 1)//batch_size} batches, assigned {total_assigned} files")

            return all_categories

        except Exception as e:
            logger.error(f"Error in Ollama analysis: {e}", exc_info=True)
            raise

    @staticmethod
    async def _analyze_with_deepseek(folder_info: List[Dict]) -> Dict[str, List[Dict]]:
        """使用DeepSeek大模型分析文件夹并生成五大固定分类，优先使用Ollama本地模型"""
        # 首先尝试使用Ollama本地模型
        try:
            logger.info("Attempting to use Ollama local model for analysis")
            return await ResourceService._analyze_with_ollama(folder_info)
        except Exception as ollama_error:
            logger.warning(f"Ollama analysis failed: {ollama_error}, falling back to DeepSeek API")

        # 如果Ollama失败，则使用DeepSeek API
        try:
            api_key = config.DEEPSEEK_API_KEY
            if not api_key:
                raise ValueError("DeepSeek API key not found")
            sample_size = min(100, len(folder_info))
            sample_folders = random.sample(folder_info, sample_size)
            # 明确要求只能用五个类别
            prompt = f"""
你是一个文件分类专家。请根据下列文件的文件名（和路径），将它们严格分类到以下五个类别之一：
1. 学术论文 (Academic Paper)
2. 调查报告 (Survey Report)
3. 专业书籍 (Professional Book)
4. 政策文件 (Policy Document)
5. 法规标准 (Regulation/Standard)

只能用这五个类别，不能有其他类别。请用如下JSON格式返回：
{{
  "学术论文": [文件索引列表],
  "调查报告": [文件索引列表],
  "专业书籍": [文件索引列表],
  "政策文件": [文件索引列表],
  "法规标准": [文件索引列表]
}}
文件列表如下：
{json.dumps([{'name': f['name'], 'path': f['path']} for f in sample_folders], ensure_ascii=False, indent=2)}
"""
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

            # 使用线程池执行器来避免事件循环问题
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    client.chat.completions.create,
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个文件分类专家，只能用五个类别分类。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                response = await asyncio.wrap_future(future)
            model_response = response.choices[0].message.content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', model_response)
            json_str = json_match.group(1) if json_match else model_response
            try:
                category_indices = json.loads(json_str)
            except Exception:
                # 尝试修正格式
                json_str = re.sub(r'[^\{\}\[\]\,\:\"\d\s\w\.\-\_\u4e00-\u9fa5]', '', json_str)
                category_indices = json.loads(json_str)
            # 保证五大类都存在
            fixed_categories = ["学术论文", "调查报告", "专业书籍", "政策文件", "法规标准"]
            categories = {cat: [] for cat in fixed_categories}
            assigned_indices = set()
            for cat in fixed_categories:
                indices = category_indices.get(cat, [])
                for idx in indices:
                    try:
                        idx_int = int(idx)
                    except Exception:
                        continue
                    if 0 <= idx_int < len(sample_folders):
                        categories[cat].append(sample_folders[idx_int])
                        assigned_indices.add(idx_int)
            # 只保留五大类中被分配的文件，未分配的文件直接丢弃
            logger.info("DeepSeek API analysis completed successfully")
            return categories
        except Exception as e:
            logger.error(f"Error in DeepSeek analysis: {e}", exc_info=True)
            raise


