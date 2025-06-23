from models.resource import ResourceItem
import os
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

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 存储任务状态的字典
# _analysis_tasks = {}

class AnalysisTask:
    def __init__(self, task_id):
        self.task_id = task_id
        self.status = "pending"  # pending, running, completed, failed
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = time.time()

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
        
        # 收集文件信息
        file_info = await ResourceService._collect_file_info(base_dir)
        
        # 使用大模型分析文件并生成分类
        categories = await ResourceService._analyze_and_categorize(file_info)
        
        # 统计各类资源数量
        result = []
        for i, (category, files) in enumerate(categories.items(), 1):
            # 为每个分类生成一个稳定的颜色
            color = ResourceService._generate_color(category)
            # 为每个分类选择一个合适的图标
            icon = ResourceService._select_icon(category)
            
            result.append(
                ResourceItem(
                    id=i,
                    name=category,
                    count=len(files),
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
    async def _collect_file_info(base_dir: str) -> List[Dict]:
        """收集目录中的文件信息"""
        file_info = []
        
        # 定义要收集的文件扩展名
        valid_extensions = {
            # 文档
            '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md', '.tex',
            # 表格和演示文稿
            '.xls', '.xlsx', '.ppt', '.pptx', '.csv',
            # 图像
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff',
            # 音频
            '.mp3', '.wav', '.ogg', '.flac', '.aac',
            # 视频
            '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv',
            # 数据和代码
            '.json', '.xml', '.yaml', '.py', '.js', '.html', '.css', '.java', '.cpp'
        }
        
        try:
            # 遍历目录
            for root, _, files in os.walk(base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    # 只处理有效扩展名的文件
                    if file_ext in valid_extensions:
                        try:
                            # 获取文件大小和修改时间
                            file_stat = os.stat(file_path)
                            
                            # 收集文件信息
                            file_info.append({
                                'name': file,
                                'path': file_path,
                                'extension': file_ext,
                                'size': file_stat.st_size,
                                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                                'relative_path': os.path.relpath(file_path, base_dir)
                            })
                        except (PermissionError, FileNotFoundError) as e:
                            logger.warning(f"Error accessing file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error scanning directory {base_dir}: {e}")
        
        return file_info
    
    @staticmethod
    async def _analyze_and_categorize(file_info: List[Dict]) -> Dict[str, List[Dict]]:
        """分析文件并生成分类"""
        # 如果文件太多，只取样本进行分析
        sample_size = min(100, len(file_info))
        sample_files = random.sample(file_info, sample_size) if len(file_info) > sample_size else file_info
        
        # 基于文件扩展名的简单分类
        extension_categories = {
            "文档": ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md', '.tex'],
            "表格": ['.xls', '.xlsx', '.csv'],
            "演示文稿": ['.ppt', '.pptx'],
            "图像": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff'],
            "音频": ['.mp3', '.wav', '.ogg', '.flac', '.aac'],
            "视频": ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv'],
            "数据": ['.json', '.xml', '.yaml', '.csv'],
            "代码": ['.py', '.js', '.html', '.css', '.java', '.cpp']
        }
        
        # 尝试使用大模型API进行更智能的分类
        try:
            # 准备发送给大模型的数据
            prompt_data = {
                "file_sample": sample_files[:20],  # 只发送前20个样本
                "current_categories": list(extension_categories.keys())
            }
            
            # 调用大模型API进行分类
            categories = await ResourceService._call_llm_api({
                "file_sample": sample_files[:20],  # 只发送前20个样本
                "current_categories": list(extension_categories.keys()),
                "file_info": file_info  # 传递完整的文件信息
            })
            
            # 如果API调用失败或返回空结果，使用基本分类
            if not categories:
                categories = ResourceService._basic_categorize(file_info, extension_categories)
            
            # 确保分类不超过10个
            if len(categories) > 5:
                # 合并小分类
                sorted_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
                top_categories = dict(sorted_categories[:9])  # 取前9个最大的分类
                
                # 将剩余的分类合并为"其他"
                other_files = []
                for cat, files in sorted_categories[9:]:
                    other_files.extend(files)
                
                if other_files:
                    top_categories["其他"] = other_files
                
                categories = top_categories
            
            return categories
            
        except Exception as e:
            logger.error(f"Error analyzing files: {e}")
            # 出错时使用基本分类
            return ResourceService._basic_categorize(file_info, extension_categories)
    
    @staticmethod
    def _basic_categorize(file_info: List[Dict], extension_categories: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        """基本的文件分类方法"""
        categories = {}
        
        for file in file_info:
            category = None
            # 根据扩展名分类
            for cat, exts in extension_categories.items():
                if file['extension'] in exts:
                    category = cat
                    break
            
            # 如果没有找到分类，归为"其他"
            if not category:
                category = "其他"
            
            # 添加到分类中
            if category not in categories:
                categories[category] = []
            categories[category].append(file)
        
        return categories
    
    @staticmethod
    async def _call_llm_api(data: Dict) -> Dict[str, List[Dict]]:
        """调用大模型API进行文件分类"""
        try:
            # DeepSeek API配置
            api_url = "https://api.deepseek.com/v1/chat/completions"  # 替换为实际的DeepSeek API地址
            api_key = os.environ.get("DEEPSEEK_API_KEY")  # 从环境变量获取API密钥
            
            if not api_key:
                logger.error("DeepSeek API key not found in environment variables")
                return {}
                
            # 构建提示词
            prompt = f"""
            请分析以下文件列表，并根据文件名内容（而非文件类型）将它们分类到适当的类别中。
            请创建有意义的类别，这些类别应该反映文件的实际内容和用途，而不仅仅是文件格式。
            例如，"财务报表"、"项目文档"、"学习资料"等。

            文件列表:
            {json.dumps(data['file_sample'], ensure_ascii=False, indent=2)}

            请以JSON格式返回分类结果，格式为:
            {{
                "类别1": [文件索引列表],
                "类别2": [文件索引列表],
                ...
            }}
            其中文件索引是文件在提供的列表中的位置（从0开始）。

            请确保创建的类别数量在3-7个之间，并且每个类别都有明确的主题。
            """
            
            # 准备请求数据
            request_data = {
                "model": "deepseek-chat",  # 替换为实际的DeepSeek模型名称
                "messages": [
                    {"role": "system", "content": "你是一个专业的文件分类助手，擅长根据文件名内容对文件进行语义分类，而不仅仅是根据文件扩展名。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2  # 低温度以获得更确定性的结果
            }
            
            # 发送请求到DeepSeek API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    },
                    json=request_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                        return {}
                    
                    result = await response.json()
                    
                    # 解析API返回的结果
                    try:
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        # 提取JSON部分
                        json_str = content.strip()
                        if "```json" in json_str:
                            json_str = json_str.split("```json")[1].split("```")[0].strip()
                        elif "```" in json_str:
                            json_str = json_str.split("```")[1].split("```")[0].strip()
                        
                        category_indices = json.loads(json_str)
                        
                        # 将索引转换为实际文件
                        categories = {}
                        for category, indices in category_indices.items():
                            categories[category] = []
                            for idx in indices:
                                if 0 <= idx < len(data['file_sample']):
                                    file_info = data['file_sample'][idx]
                                    # 找到原始文件信息
                                    for full_file in data.get('file_info', []):
                                        if full_file['path'] == file_info['path']:
                                            categories[category].append(full_file)
                                            break
                        
                        return categories
                    except Exception as e:
                        logger.error(f"Error parsing DeepSeek API response: {e}")
                        logger.debug(f"Raw response: {content}")
                        return {}
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return {}
    
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
            "文档": "📄",
            "表格": "📊",
            "演示文稿": "📑",
            "图像": "🖼️",
            "音频": "🎵",
            "视频": "🎬",
            "数据": "📊",
            "代码": "💻",
            "其他": "📁"
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
            
            # 如果提供了文件列表，则直接使用
            if file_list:
                logger.info(f"Using provided file list with {len(file_list)} files")
                
                # 收集文件夹信息
                folder_structure = {}
                
                # 处理文件列表，按文件夹分组
                for file in file_list:
                    path = file["path"]
                    # 提取文件所在的文件夹路径
                    folder_path = os.path.dirname(path)
                    
                    # 如果是根目录，使用特殊标记
                    if not folder_path:
                        folder_path = "根目录"
                    
                    # 将文件添加到对应的文件夹
                    if folder_path not in folder_structure:
                        folder_structure[folder_path] = []
                    
                    # 提取文件扩展名
                    file_ext = os.path.splitext(file["name"])[1].lower()
                    
                    folder_structure[folder_path].append({
                        'name': file["name"],
                        'path': path,
                        'extension': file_ext,
                        'size': 0,  # 前端无法获取文件大小
                        'modified': datetime.now().isoformat(),
                        'relative_path': path
                    })
                
                # 直接使用文件夹名称作为分类
                categories = {}
                for folder_path, files in folder_structure.items():
                    # 获取文件夹名称（最后一级目录名）
                    folder_name = os.path.basename(folder_path)
                    if not folder_name:
                        folder_name = os.path.basename(os.path.dirname(folder_path))
                    if not folder_name:
                        folder_name = "其他"
                    
                    # 使用文件夹名称作为分类
                    if folder_name not in categories:
                        categories[folder_name] = []
                    
                    categories[folder_name].extend(files)
                
                task.progress = 90
            
            else:
                # 使用线程池执行文件系统扫描
                with ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) * 4)) as executor:
                    # 首先获取顶层目录列表
                    try:
                        top_dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) 
                                   if os.path.isdir(os.path.join(base_dir, d))]
                        # 添加基目录本身
                        top_dirs.append(base_dir)
                    except Exception as e:
                        logger.error(f"Error listing directory {base_dir}: {e}")
                        top_dirs = [base_dir]
                    
                    # 为每个顶层目录创建一个扫描任务
                    scan_tasks = []
                    for directory in top_dirs:
                        scan_tasks.append(
                            asyncio.get_event_loop().run_in_executor(
                                executor,
                                ResourceService._scan_directory,
                                directory,
                                base_dir
                            )
                        )
                    
                    # 使用asyncio.as_completed处理结果，更新进度
                    file_info = []
                    completed = 0
                    for future in asyncio.as_completed(scan_tasks):
                        chunk_result = await future
                        file_info.extend(chunk_result)
                        
                        # 更新进度（从5%到50%）
                        completed += 1
                        progress = 5 + int((completed / len(scan_tasks)) * 45)
                        task.progress = progress
                    
                    # 按文件夹分组
                    folder_structure = {}
                    for file in file_info:
                        # 提取文件所在的文件夹路径
                        folder_path = os.path.dirname(file['path'])
                        
                        # 将文件添加到对应的文件夹
                        if folder_path not in folder_structure:
                            folder_structure[folder_path] = []
                        
                        folder_structure[folder_path].append(file)
                    
                    # 直接使用文件夹名称作为分类
                    categories = {}
                    for folder_path, files in folder_structure.items():
                        # 获取文件夹名称（最后一级目录名）
                        folder_name = os.path.basename(folder_path)
                        if not folder_name:
                            folder_name = "其他"
                        
                        # 使用文件夹名称作为分类
                        if folder_name not in categories:
                            categories[folder_name] = []
                        
                        categories[folder_name].extend(files)
                
                task.progress = 90
            
            # 5. 构建最终结果
            result = []
            for category, files in categories.items():
                result.append({
                    "id": len(result) + 1,
                    "name": category,
                    "count": len(files),
                    "icon": ResourceService._select_icon(category),
                    "color": ResourceService._generate_color(category),
                    "files": files
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
    def _scan_directory(directory: str, base_dir: str) -> List[Dict]:
        """扫描单个目录及其子目录中的文件（用于线程池并行执行）"""
        file_info = []
        
        # 定义要收集的文件扩展名
        valid_extensions = {
            # 文档
            '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md', '.tex',
            # 表格和演示文稿
            '.xls', '.xlsx', '.ppt', '.pptx', '.csv',
            # 图像
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff',
            # 音频
            '.mp3', '.wav', '.ogg', '.flac', '.aac',
            # 视频
            '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv',
            # 数据和代码
            '.json', '.xml', '.yaml', '.py', '.js', '.html', '.css', '.java', '.cpp'
        }
        
        try:
            # 使用os.scandir代替os.walk以获得更好的性能
            for entry in os.scandir(directory):
                try:
                    if entry.is_file():
                        file_ext = os.path.splitext(entry.name)[1].lower()
                        
                        # 只处理有效扩展名的文件
                        if file_ext in valid_extensions:
                            try:
                                # 获取文件大小和修改时间
                                file_stat = entry.stat()
                                
                                # 收集文件信息
                                file_path = entry.path
                                file_info.append({
                                    'name': entry.name,
                                    'path': file_path,
                                    'extension': file_ext,
                                    'size': file_stat.st_size,
                                    'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                                    'relative_path': os.path.relpath(file_path, base_dir)
                                })
                            except (PermissionError, FileNotFoundError) as e:
                                logger.warning(f"Error accessing file {entry.path}: {e}")
                    
                    # 递归处理子目录
                    elif entry.is_dir():
                        # 跳过隐藏目录
                        if entry.name.startswith('.'):
                            continue
                        
                        # 递归扫描子目录
                        sub_files = ResourceService._scan_directory(entry.path, base_dir)
                        file_info.extend(sub_files)
                        
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"Error accessing entry {entry.path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
        
        return file_info

    @staticmethod
    def _get_extension_categories() -> Dict[str, List[str]]:
        """获取文件扩展名分组（仅用于内部处理，不作为最终分类名称）"""
        # 注意：这里只是将扩展名分组，不是最终的分类名称
        # 最终分类名称将由文件夹名称和内容智能生成
        return {
            "text_files": ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md', '.tex'],
            "spreadsheets": ['.xls', '.xlsx', '.csv'],
            "presentations": ['.ppt', '.pptx'],
            "images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff'],
            "audio": ['.mp3', '.wav', '.ogg', '.flac', '.aac'],
            "video": ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv'],
            "data": ['.json', '.xml', '.yaml', '.csv'],
            "code": ['.py', '.js', '.html', '.css', '.java', '.cpp']
        }

    @staticmethod
    def _basic_categorize(file_info: List[Dict], extension_categories: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        """基于文件夹组织的分类方法（当API调用失败时使用）"""
        # 按文件夹分组
        folder_structure = {}
        for file in file_info:
            # 提取文件所在的文件夹路径
            folder_path = os.path.dirname(file['path'])
            
            # 将文件添加到对应的文件夹
            if folder_path not in folder_structure:
                folder_structure[folder_path] = []
            
            folder_structure[folder_path].append(file)
        
        # 直接使用文件夹名称作为分类
        categories = {}
        for folder_path, files in folder_structure.items():
            # 获取文件夹名称（最后一级目录名）
            folder_name = os.path.basename(folder_path)
            if not folder_name:
                folder_name = os.path.basename(os.path.dirname(folder_path))
            if not folder_name:
                folder_name = "未分类文件"
            
            # 使用文件夹名称作为分类
            if folder_name not in categories:
                categories[folder_name] = []
            
            categories[folder_name].extend(files)
        
        return categories

    @staticmethod
    async def auto_analyze_local_directories():
        """自动分析本地文件夹"""
        # 防止重复运行
        if ResourceService._auto_analysis_running:
            logger.info("Auto analysis already running, skipping")
            return
        
        try:
            ResourceService._auto_analysis_running = True
            logger.info("Starting automatic analysis of local directories")
            
            # 获取用户主目录
            home_dir = os.path.expanduser("~")
            common_dirs = [
                os.path.join(home_dir, "Documents"),
                os.path.join(home_dir, "Downloads"),
                os.path.join(home_dir, "Pictures"),
                os.path.join(home_dir, "Music"),
                os.path.join(home_dir, "Videos"),
                os.path.join(home_dir, "Desktop")
            ]
            
            # 收集存在的目录
            existing_dirs = [d for d in common_dirs if os.path.exists(d) and os.path.isdir(d)]
            print('existing_dirs',existing_dirs)
            # 创建分析任务
            task_id = str(uuid.uuid4())
            task = AnalysisTask(task_id)
            ResourceService._analysis_tasks[task_id] = task
            
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
            ResourceService._auto_analysis_running = False

    @staticmethod
    async def _run_auto_analysis(task: AnalysisTask, directories: List[str]):
        """运行自动分析任务 - 完全基于文件夹内容和名称进行智能分类"""
        try:
            task.status = "running"
            task.progress = 5
            
            # 完全基于文件夹内容和名称进行智能分类
            result = []
            
            for i, directory in enumerate(directories):
                try:
                    # 获取目录名称
                    dir_name = os.path.basename(directory)
                    
                    # 计算目录中的文件数量和类型
                    total_files = 0
                    file_list = []
                    extensions = {}
                    file_names = []
                    
                    # 遍历目录中的文件
                    for root, _, files in os.walk(directory):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                # 获取文件扩展名
                                ext = os.path.splitext(file)[1].lower()
                                
                                # 统计扩展名
                                if ext:
                                    extensions[ext] = extensions.get(ext, 0) + 1
                                
                                # 收集文件名用于后续分析
                                file_names.append(file.lower())
                                
                                # 获取相对路径
                                rel_path = os.path.relpath(file_path, directory)
                                
                                # 添加文件信息
                                file_list.append({
                                    'name': file,
                                    'path': file_path,
                                    'extension': ext,
                                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if os.path.exists(file_path) else "",
                                    'relative_path': rel_path
                                })
                                
                                total_files += 1
                            except Exception as e:
                                logger.warning(f"Error processing file {file}: {e}")
                                continue
                    
                    # 智能分析文件夹内容，生成描述性分类名称
                    category_name = ResourceService._analyze_folder_content(dir_name, file_names, extensions)
                    
                    # 添加目录作为一个分类
                    result.append({
                        "id": i + 1,
                        "name": category_name,
                        "count": total_files,
                        "icon": "📁",  # 使用通用图标
                        "color": ResourceService._generate_color(category_name),
                        "files": file_list[:100]  # 限制文件数量，避免返回过多数据
                    })
                    
                    # 更新进度
                    task.progress = 5 + int((i + 1) / len(directories) * 85)
                except Exception as e:
                    logger.error(f"Error processing directory {directory}: {e}")
                    continue
            print('result',result)
            # 更新任务状态
            task.status = "completed"
            task.progress = 100
            task.result = result
        except Exception as e:
            logger.error(f"Auto analysis task failed: {e}")
            task.status = "failed"
            task.error = str(e)

    @staticmethod
    def _analyze_folder_content(folder_name, file_names, extensions):
        """智能分析文件夹内容，生成描述性分类名称"""
        # 清理文件夹名称，移除特殊字符并转换为更可读的格式
        clean_name = folder_name.replace("_", " ").replace("-", " ").strip()
        
        # 如果文件夹名称已经很有描述性，直接使用
        if len(clean_name) > 3 and not clean_name.lower() in ["documents", "downloads", "pictures", "music", "videos", "desktop", "文档", "下载", "图片", "音乐", "视频", "桌面"]:
            return clean_name
        
        # 分析文件扩展名分布
        total_files = sum(extensions.values())
        if total_files == 0:
            return clean_name
        
        # 分析文件名中的常见词汇
        common_words = {}
        for name in file_names:
            # 分割文件名为单词
            words = re.findall(r'[a-zA-Z\u4e00-\u9fa5]+', name)
            for word in words:
                if len(word) > 1:  # 忽略单个字符
                    word = word.lower()
                    common_words[word] = common_words.get(word, 0) + 1
        
        # 移除常见的无意义词汇
        stop_words = ["the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "at", "from", "by", "about", "as", "file", "doc", "document", "image", "photo", "picture", "video", "audio", "music", "data", "code", "program", "script", "text", "pdf", "word", "excel", "powerpoint", "ppt", "xls", "doc", "docx", "xlsx", "pptx", "txt", "jpg", "png", "mp3", "mp4", "avi", "mov", "wav", "ogg", "flac", "zip", "rar", "7z", "tar", "gz", "的", "了", "和", "与", "或", "在", "是", "有", "文件", "图片", "视频", "音频", "数据", "代码", "文本"]
        for word in stop_words:
            if word in common_words:
                del common_words[word]
        
        # 找出最常见的词汇
        if common_words:
            sorted_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)
            top_words = [word for word, count in sorted_words[:3] if count > 2]
            
            if top_words:
                # 根据最常见的词汇生成分类名称
                if len(top_words) == 1:
                    return top_words[0].capitalize() + "相关文件"
                else:
                    return "与" + "、".join(top_words) + "相关的文件"
        
        # 分析文件类型分布
        doc_exts = ['.pdf', '.doc', '.docx', '.txt', '.md']
        img_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        code_exts = ['.py', '.js', '.html', '.css', '.java', '.cpp']
        data_exts = ['.csv', '.json', '.xml', '.xlsx']
        audio_exts = ['.mp3', '.wav', '.ogg', '.flac', '.aac']
        video_exts = ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv']
        
        # 计算各类型文件的比例
        doc_ratio = sum(extensions.get(ext, 0) for ext in doc_exts) / total_files
        img_ratio = sum(extensions.get(ext, 0) for ext in img_exts) / total_files
        code_ratio = sum(extensions.get(ext, 0) for ext in code_exts) / total_files
        data_ratio = sum(extensions.get(ext, 0) for ext in data_exts) / total_files
        audio_ratio = sum(extensions.get(ext, 0) for ext in audio_exts) / total_files
        video_ratio = sum(extensions.get(ext, 0) for ext in video_exts) / total_files
        
        # 根据文件类型分布生成更具描述性的名称
        if doc_ratio > 0.7:
            return folder_name + "文档集合"
        elif img_ratio > 0.7:
            return folder_name + "图像集合"
        elif code_ratio > 0.7:
            return folder_name + "代码项目"
        elif data_ratio > 0.7:
            return folder_name + "数据集合"
        elif audio_ratio > 0.7:
            return folder_name + "音频集合"
        elif video_ratio > 0.7:
            return folder_name + "视频集合"
        elif doc_ratio + img_ratio > 0.7:
            return folder_name + "文档与图像集合"
        elif code_ratio + data_ratio > 0.7:
            return folder_name + "代码与数据项目"
        
        # 如果无法确定明确的分类，使用原始文件夹名称
        return clean_name

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






