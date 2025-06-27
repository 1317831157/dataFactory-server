"""
数据分析模态框后端接口
支持 DataAnalysisModal 组件的所有功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
import uuid
import time
import random
from datetime import datetime, timedelta
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["数据分析模态框"])

# ==================== 数据模型定义 ====================

class DataSourceType(str, Enum):
    LAW = "law"
    PAPER = "paper"
    REPORT = "report"
    POLICY = "policy"
    BOOK = "book"

class CategoryType(str, Enum):
    ROBOT = "robot"
    AGRICULTURE = "agriculture"
    LANDSLIDE = "landslide"
    VISION = "vision"
    MICROSCOPE = "microscope"
    SATELLITE = "satellite"
    STAR = "star"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PREPROCESSING = "preprocessing"
    TRAINING = "training"
    CLASSIFYING = "classifying"
    COMPLETED = "completed"
    FAILED = "failed"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# 请求模型
class KeywordExtractionRequest(BaseModel):
    sourceType: str = Field(..., description="数据源类型")
    sampleSize: Optional[int] = Field(1000, description="样本大小")

class PreprocessingRequest(BaseModel):
    sourceType: str = Field(..., description="数据源类型")
    steps: List[str] = Field(..., description="预处理步骤")
    parameters: Optional[Dict[str, Any]] = Field(None, description="预处理参数")

class ClassificationRequest(BaseModel):
    sourceType: str = Field(..., description="数据源类型")
    modelId: Optional[str] = Field(None, description="模型ID")
    categories: Optional[List[str]] = Field(None, description="分类类别")
    parameters: Optional[Dict[str, Any]] = Field(None, description="分类参数")

class CategoryStatsUpdateRequest(BaseModel):
    taskId: str = Field(..., description="任务ID")
    sourceType: str = Field(..., description="数据源类型")
    categories: List[str] = Field(..., description="分类类别")

class ExportRequest(BaseModel):
    taskId: str = Field(..., description="任务ID")
    format: str = Field(..., description="导出格式")
    includeMetrics: bool = Field(True, description="包含指标")
    includeCategoryStats: bool = Field(True, description="包含分类统计")
    includeConfusionMatrix: bool = Field(True, description="包含混淆矩阵")
    includeRawData: bool = Field(False, description="包含原始数据")

# 响应模型
class DataSource(BaseModel):
    id: str
    name: str
    type: str
    description: str
    count: int
    lastUpdated: str
    categories: List[str]

class Category(BaseModel):
    id: str
    name: str
    type: str
    description: str
    icon: str
    color: str

class PreprocessStep(BaseModel):
    id: str
    name: str
    description: str
    status: StepStatus
    progress: int
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    duration: Optional[int] = None

class KeywordExtractionResult(BaseModel):
    keywords: List[str]
    totalKeywords: int
    extractedCount: int
    progress: int
    confidence: float

class PreprocessResult(BaseModel):
    taskId: str
    status: TaskStatus
    progress: int
    steps: List[PreprocessStep]
    totalSteps: int
    completedSteps: int
    startTime: str
    endTime: Optional[str] = None
    duration: Optional[int] = None
    result: Optional[Dict[str, Any]] = None

class ClassificationMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1Score: float
    support: int
    confusionMatrix: List[List[int]]
    classificationReport: Dict[str, Dict[str, float]]

class CategoryStats(BaseModel):
    robot: Dict[str, Union[int, float]]
    agriculture: Dict[str, Union[int, float]]
    landslide: Dict[str, Union[int, float]]
    vision: Dict[str, Union[int, float]]
    microscope: Dict[str, Union[int, float]]
    satellite: Dict[str, Union[int, float]]
    star: Dict[str, Union[int, float]]

class ConfusionMatrixData(BaseModel):
    categories: List[str]
    matrix: List[List[int]]
    labels: List[str]
    totalSamples: int

class ClassificationTask(BaseModel):
    taskId: str
    sourceType: str
    status: TaskStatus
    progress: int
    startTime: str
    endTime: Optional[str] = None
    duration: Optional[int] = None
    modelType: str
    parameters: Dict[str, Any]
    metrics: Optional[ClassificationMetrics] = None
    categoryStats: Optional[CategoryStats] = None
    error: Optional[str] = None

class ModelInfo(BaseModel):
    id: str
    name: str
    type: str
    version: str
    description: str
    accuracy: float
    trainedOn: str
    supportedCategories: List[str]
    parameters: Dict[str, Any]

class RealTimeAnalysisStatus(BaseModel):
    isRunning: bool
    currentTask: Optional[str] = None
    progress: int
    estimatedTimeRemaining: Optional[int] = None
    processedSamples: int
    totalSamples: int
    currentStep: str
    queueLength: int

class AnalysisHistory(BaseModel):
    id: str
    sourceType: str
    modelType: str
    startTime: str
    endTime: str
    duration: int
    status: str
    metrics: ClassificationMetrics
    categoryStats: CategoryStats
    samplesProcessed: int

class DataFlowStatus(BaseModel):
    currentStep: str
    steps: List[Dict[str, Any]]

# ==================== 全局状态管理 ====================

# 任务存储
tasks: Dict[str, Dict[str, Any]] = {}
keyword_extraction_tasks: Dict[str, Dict[str, Any]] = {}
preprocessing_tasks: Dict[str, Dict[str, Any]] = {}
classification_tasks: Dict[str, Dict[str, Any]] = {}

# 数据源到分类类别的映射
SOURCE_CATEGORY_MAPPING = {
    "law": ["robot", "vision"],
    "paper": ["microscope", "satellite"],
    "report": ["agriculture", "landslide"],
    "policy": ["robot", "agriculture"],
    "book": ["star", "satellite"]
}

# 可用的数据源
AVAILABLE_DATA_SOURCES = [
    DataSource(
        id="law-001",
        name="法律文档数据集",
        type="law",
        description="包含各类法律条文和判决书的数据集",
        count=15420,
        lastUpdated="2024-01-15T10:30:00Z",
        categories=["robot", "vision"]
    ),
    DataSource(
        id="paper-001",
        name="学术论文数据集",
        type="paper",
        description="来自各大期刊的学术论文集合",
        count=28750,
        lastUpdated="2024-01-14T16:45:00Z",
        categories=["microscope", "satellite"]
    ),
    DataSource(
        id="report-001",
        name="研究报告数据集",
        type="report",
        description="政府和机构发布的研究报告",
        count=8930,
        lastUpdated="2024-01-13T09:20:00Z",
        categories=["agriculture", "landslide"]
    ),
    DataSource(
        id="policy-001",
        name="政策文件数据集",
        type="policy",
        description="各级政府发布的政策文件",
        count=12340,
        lastUpdated="2024-01-12T14:15:00Z",
        categories=["robot", "agriculture"]
    ),
    DataSource(
        id="book-001",
        name="图书文献数据集",
        type="book",
        description="各类专业图书和文献资料",
        count=19680,
        lastUpdated="2024-01-11T11:30:00Z",
        categories=["star", "satellite"]
    )
]

# 可用的分类类别
AVAILABLE_CATEGORIES = [
    Category(
        id="robot-001",
        name="机器人技术",
        type="robot",
        description="机器人相关的技术和应用",
        icon="robot",
        color="#1890ff"
    ),
    Category(
        id="agriculture-001",
        name="农业科技",
        type="agriculture",
        description="农业技术和智慧农业",
        icon="agriculture",
        color="#52c41a"
    ),
    Category(
        id="landslide-001",
        name="地质灾害",
        type="landslide",
        description="滑坡等地质灾害研究",
        icon="landslide",
        color="#fa8c16"
    ),
    Category(
        id="vision-001",
        name="计算机视觉",
        type="vision",
        description="图像识别和计算机视觉",
        icon="vision",
        color="#722ed1"
    ),
    Category(
        id="microscope-001",
        name="显微镜技术",
        type="microscope",
        description="显微镜和微观分析技术",
        icon="microscope",
        color="#eb2f96"
    ),
    Category(
        id="satellite-001",
        name="卫星遥感",
        type="satellite",
        description="卫星技术和遥感应用",
        icon="satellite",
        color="#13c2c2"
    ),
    Category(
        id="star-001",
        name="天文观测",
        type="star",
        description="天文学和星体观测",
        icon="star",
        color="#faad14"
    )
]

# 可用的模型
AVAILABLE_MODELS = [
    ModelInfo(
        id="bert-base-001",
        name="BERT Base 分类器",
        type="transformer",
        version="1.0.0",
        description="基于BERT的文本分类模型",
        accuracy=0.92,
        trainedOn="2024-01-01",
        supportedCategories=["robot", "agriculture", "landslide", "vision"],
        parameters={"max_length": 512, "batch_size": 32}
    ),
    ModelInfo(
        id="roberta-large-001",
        name="RoBERTa Large 分类器",
        type="transformer",
        version="1.2.0",
        description="基于RoBERTa的高精度文本分类模型",
        accuracy=0.95,
        trainedOn="2024-01-10",
        supportedCategories=["microscope", "satellite", "star", "vision"],
        parameters={"max_length": 1024, "batch_size": 16}
    )
]

# ==================== 工具函数 ====================

def generate_task_id() -> str:
    """生成唯一的任务ID"""
    return f"task_{uuid.uuid4().hex[:8]}_{int(time.time())}"

def generate_mock_keywords(source_type: str, count: int = 50) -> List[str]:
    """生成模拟关键词"""
    base_keywords = {
        "law": ["法律", "条文", "判决", "诉讼", "合同", "权利", "义务", "责任"],
        "paper": ["研究", "方法", "实验", "结果", "分析", "理论", "模型", "算法"],
        "report": ["报告", "调研", "数据", "统计", "趋势", "建议", "政策", "发展"],
        "policy": ["政策", "规定", "措施", "实施", "管理", "监督", "评估", "改革"],
        "book": ["知识", "理论", "概念", "原理", "应用", "技术", "方法", "系统"]
    }

    keywords = base_keywords.get(source_type, base_keywords["paper"])
    # 扩展关键词列表
    extended_keywords = []
    for i in range(count):
        base_word = keywords[i % len(keywords)]
        extended_keywords.append(f"{base_word}{i//len(keywords) + 1}" if i >= len(keywords) else base_word)

    return extended_keywords[:count]

def generate_mock_confusion_matrix(categories: List[str]) -> List[List[int]]:
    """生成模拟混淆矩阵"""
    size = len(categories)
    matrix = []

    for i in range(size):
        row = []
        for j in range(size):
            if i == j:
                # 对角线元素（正确分类）应该较大
                value = random.randint(80, 95)
            else:
                # 非对角线元素（错误分类）应该较小
                value = random.randint(1, 8)
            row.append(value)
        matrix.append(row)

    return matrix

def generate_mock_category_stats(categories: List[str]) -> Dict[str, Dict[str, Union[int, float]]]:
    """生成模拟分类统计"""
    stats = {}
    total_samples = 1000

    for category in categories:
        count = random.randint(80, 150)
        confidence = round(random.uniform(0.75, 0.95), 3)
        percentage = round((count / total_samples) * 100, 1)

        stats[category] = {
            "count": count,
            "confidence": confidence,
            "percentage": percentage,
            "samples": count
        }

    return stats

def map_resource_to_source_type(resource_name: str) -> str:
    """将资源名称映射到数据源类型"""
    resource_name_lower = resource_name.lower()

    # 定义映射规则
    mapping_rules = {
        "文档": "paper",
        "论文": "paper",
        "学术": "paper",
        "研究": "paper",
        "法律": "law",
        "法规": "law",
        "条文": "law",
        "政策": "policy",
        "规定": "policy",
        "制度": "policy",
        "报告": "report",
        "分析": "report",
        "统计": "report",
        "图书": "book",
        "书籍": "book",
        "文献": "book",
        "资料": "book"
    }

    # 检查资源名称是否包含映射关键词
    for keyword, source_type in mapping_rules.items():
        if keyword in resource_name_lower:
            return source_type

    # 默认返回 paper 类型
    return "paper"

async def simulate_progress_update(task_id: str, task_dict: Dict[str, Dict[str, Any]],
                                 duration: int = 5, steps: Optional[List[str]] = None):
    """模拟进度更新"""
    if task_id not in task_dict:
        return

    task = task_dict[task_id]
    task["status"] = "running"
    task["startTime"] = datetime.now().isoformat()

    if steps:
        task["steps"] = [
            PreprocessStep(
                id=f"step_{i}",
                name=step,
                description=f"执行{step}",
                status=StepStatus.PENDING,
                progress=0
            ).model_dump() for i, step in enumerate(steps)
        ]
        task["totalSteps"] = len(steps)
        task["completedSteps"] = 0

    # 模拟进度更新
    for i in range(101):
        if task_id not in task_dict:
            break

        task["progress"] = i

        # 更新步骤状态
        if steps and i > 0:
            current_step_index = min(int(i / (100 / len(steps))), len(steps) - 1)

            for j, step in enumerate(task["steps"]):
                if j < current_step_index:
                    step["status"] = StepStatus.COMPLETED
                    step["progress"] = 100
                elif j == current_step_index:
                    step["status"] = StepStatus.RUNNING
                    step["progress"] = (i % (100 // len(steps))) * len(steps)
                else:
                    step["status"] = StepStatus.PENDING
                    step["progress"] = 0

            task["completedSteps"] = current_step_index + (1 if i == 100 else 0)

        await asyncio.sleep(duration / 100)

    # 完成任务
    if task_id in task_dict:
        task["status"] = "completed"
        task["progress"] = 100
        task["endTime"] = datetime.now().isoformat()
        task["duration"] = duration * 1000  # 转换为毫秒

        if steps:
            for step in task["steps"]:
                step["status"] = StepStatus.COMPLETED
                step["progress"] = 100
            task["completedSteps"] = len(steps)

# ==================== 数据源管理接口 ====================

@router.get("/data-sources")
async def get_data_sources():
    """获取可用的数据源列表"""
    try:
        # 首先尝试从 get_auto_analysis_result 获取真实数据
        try:
            from services.resource_service import ResourceService
            auto_analysis_result = await ResourceService.get_auto_analysis_result()

            if auto_analysis_result:
                # 将自动分析结果转换为数据源格式
                data_sources = []
                for resource_item in auto_analysis_result:
                    # 根据资源类型映射到数据源类型
                    source_type = map_resource_to_source_type(resource_item.name)

                    data_source = DataSource(
                        id=f"auto-{resource_item.id}",
                        name=resource_item.name,
                        type=source_type,
                        description=f"自动分析发现的{resource_item.name}资源",
                        count=resource_item.count,
                        lastUpdated=datetime.now().isoformat(),
                        categories=SOURCE_CATEGORY_MAPPING.get(source_type, ["robot", "vision"])
                    )
                    data_sources.append(data_source)

                logger.info(f"Successfully loaded {len(data_sources)} data sources from auto analysis")
                return {
                    "code": 200,
                    "message": "Success",
                    "data": [source.model_dump() for source in data_sources]
                }
        except Exception as e:
            logger.warning(f"Failed to load auto analysis result: {e}")

        # 如果自动分析结果不可用，使用默认数据源
        logger.info("Using default data sources")
        return {
            "code": 200,
            "message": "Success",
            "data": [source.model_dump() for source in AVAILABLE_DATA_SOURCES]
        }
    except Exception as e:
        logger.error(f"Error getting data sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-sources/{source_id}")
async def get_data_source_detail(source_id: str):
    """获取数据源详情"""
    try:
        source = next((s for s in AVAILABLE_DATA_SOURCES if s.id == source_id), None)
        if not source:
            raise HTTPException(status_code=404, detail="Data source not found")

        return {
            "code": 200,
            "message": "Success",
            "data": source.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data source detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source-category-mapping")
async def get_source_category_mapping():
    """获取数据源到分类类别的映射关系"""
    try:
        return {
            "code": 200,
            "message": "Success",
            "data": SOURCE_CATEGORY_MAPPING
        }
    except Exception as e:
        logger.error(f"Error getting source category mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 分类类别管理接口 ====================

@router.get("/categories")
async def get_categories():
    """获取所有分类类别"""
    try:
        return {
            "code": 200,
            "message": "Success",
            "data": [category.model_dump() for category in AVAILABLE_CATEGORIES]
        }
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/{category_id}")
async def get_category_detail(category_id: str):
    """获取分类类别详情"""
    try:
        category = next((c for c in AVAILABLE_CATEGORIES if c.id == category_id), None)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        return {
            "code": 200,
            "message": "Success",
            "data": category.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 关键词提取接口 ====================

@router.post("/keyword-extraction/start")
async def start_keyword_extraction(request: KeywordExtractionRequest, background_tasks: BackgroundTasks):
    """开始关键词提取"""
    try:
        task_id = generate_task_id()

        # 创建任务
        task = {
            "taskId": task_id,
            "sourceType": request.sourceType,
            "sampleSize": request.sampleSize,
            "status": "pending",
            "progress": 0,
            "startTime": datetime.now().isoformat(),
            "keywords": [],
            "totalKeywords": 0,
            "extractedCount": 0,
            "confidence": 0.0
        }

        keyword_extraction_tasks[task_id] = task

        # 启动后台任务
        background_tasks.add_task(simulate_keyword_extraction, task_id, request.sourceType, request.sampleSize)

        return {
            "code": 200,
            "message": "Keyword extraction task started",
            "data": {"taskId": task_id}
        }
    except Exception as e:
        logger.error(f"Error starting keyword extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keyword-extraction/progress/{task_id}")
async def get_keyword_extraction_progress(task_id: str):
    """获取关键词提取进度"""
    try:
        if task_id not in keyword_extraction_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = keyword_extraction_tasks[task_id]

        result = KeywordExtractionResult(
            keywords=task["keywords"],
            totalKeywords=task["totalKeywords"],
            extractedCount=task["extractedCount"],
            progress=task["progress"],
            confidence=task["confidence"]
        )

        return {
            "code": 200,
            "message": "Success",
            "data": result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting keyword extraction progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keyword-extraction/result/{task_id}")
async def get_extracted_keywords(task_id: str):
    """获取提取的关键词结果"""
    try:
        if task_id not in keyword_extraction_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = keyword_extraction_tasks[task_id]

        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "keywords": task["keywords"],
                "confidence": task["confidence"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extracted keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def simulate_keyword_extraction(task_id: str, source_type: str, sample_size: int):
    """模拟关键词提取过程"""
    if task_id not in keyword_extraction_tasks:
        return

    task = keyword_extraction_tasks[task_id]
    task["status"] = "running"

    # 生成关键词
    all_keywords = generate_mock_keywords(source_type, sample_size // 10)
    task["totalKeywords"] = len(all_keywords)

    # 模拟提取过程
    for i in range(len(all_keywords)):
        if task_id not in keyword_extraction_tasks:
            break

        task["keywords"].append(all_keywords[i])
        task["extractedCount"] = i + 1
        task["progress"] = int((i + 1) / len(all_keywords) * 100)
        task["confidence"] = round(random.uniform(0.8, 0.95), 3)

        await asyncio.sleep(0.1)  # 模拟处理时间

    # 完成任务
    if task_id in keyword_extraction_tasks:
        task["status"] = "completed"
        task["progress"] = 100
        task["endTime"] = datetime.now().isoformat()

# ==================== 数据预处理接口 ====================

@router.post("/preprocessing/start")
async def start_preprocessing(request: PreprocessingRequest, background_tasks: BackgroundTasks):
    """开始数据预处理"""
    try:
        task_id = generate_task_id()

        # 创建任务
        task = {
            "taskId": task_id,
            "sourceType": request.sourceType,
            "status": "pending",
            "progress": 0,
            "steps": [],
            "totalSteps": len(request.steps),
            "completedSteps": 0,
            "startTime": datetime.now().isoformat(),
            "parameters": request.parameters or {}
        }

        preprocessing_tasks[task_id] = task

        # 启动后台任务
        background_tasks.add_task(simulate_progress_update, task_id, preprocessing_tasks, 8, request.steps)

        return {
            "code": 200,
            "message": "Preprocessing task started",
            "data": {"taskId": task_id}
        }
    except Exception as e:
        logger.error(f"Error starting preprocessing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preprocessing/progress/{task_id}")
async def get_preprocessing_progress(task_id: str):
    """获取预处理进度"""
    try:
        if task_id not in preprocessing_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = preprocessing_tasks[task_id]

        result = PreprocessResult(
            taskId=task["taskId"],
            status=TaskStatus(task["status"]),
            progress=task["progress"],
            steps=[PreprocessStep(**step) for step in task.get("steps", [])],
            totalSteps=task["totalSteps"],
            completedSteps=task["completedSteps"],
            startTime=task["startTime"],
            endTime=task.get("endTime"),
            duration=task.get("duration"),
            result=task.get("result")
        )

        return {
            "code": 200,
            "message": "Success",
            "data": result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preprocessing progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preprocessing/result/{task_id}")
async def get_preprocessing_result(task_id: str):
    """获取预处理结果"""
    try:
        if task_id not in preprocessing_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = preprocessing_tasks[task_id]

        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")

        # 生成模拟结果
        if "result" not in task:
            task["result"] = {
                "cleanedDataCount": random.randint(800, 1000),
                "standardizedDataCount": random.randint(750, 950),
                "extractedFeatures": random.randint(50, 200),
                "qualityScore": round(random.uniform(0.85, 0.98), 3)
            }

        result = PreprocessResult(
            taskId=task["taskId"],
            status=TaskStatus(task["status"]),
            progress=task["progress"],
            steps=[PreprocessStep(**step) for step in task.get("steps", [])],
            totalSteps=task["totalSteps"],
            completedSteps=task["completedSteps"],
            startTime=task["startTime"],
            endTime=task.get("endTime"),
            duration=task.get("duration"),
            result=task["result"]
        )

        return {
            "code": 200,
            "message": "Success",
            "data": result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preprocessing result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 模型管理接口 ====================

@router.get("/models")
async def get_available_models():
    """获取可用的分类模型"""
    try:
        return {
            "code": 200,
            "message": "Success",
            "data": [model.model_dump() for model in AVAILABLE_MODELS]
        }
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 智能分类接口 ====================

@router.post("/classification/start")
async def start_classification(request: ClassificationRequest, background_tasks: BackgroundTasks):
    """开始智能分类任务"""
    try:
        task_id = generate_task_id()

        # 获取数据源对应的分类类别
        categories = SOURCE_CATEGORY_MAPPING.get(request.sourceType, ["robot", "vision"])

        # 创建任务
        task = {
            "taskId": task_id,
            "sourceType": request.sourceType,
            "status": "pending",
            "progress": 0,
            "startTime": datetime.now().isoformat(),
            "modelType": request.modelId or "bert-base-001",
            "parameters": request.parameters or {"batchSize": 32, "threshold": 0.8},
            "categories": categories,
            "metrics": None,
            "categoryStats": None
        }

        classification_tasks[task_id] = task

        # 启动后台任务
        background_tasks.add_task(simulate_classification_task, task_id, categories)

        return {
            "code": 200,
            "message": "Classification task started",
            "data": {"taskId": task_id}
        }
    except Exception as e:
        logger.error(f"Error starting classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classification/progress/{task_id}")
async def get_classification_progress(task_id: str):
    """获取分类任务进度"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]

        result = ClassificationTask(
            taskId=task["taskId"],
            sourceType=task["sourceType"],
            status=TaskStatus(task["status"]),
            progress=task["progress"],
            startTime=task["startTime"],
            endTime=task.get("endTime"),
            duration=task.get("duration"),
            modelType=task["modelType"],
            parameters=task["parameters"],
            metrics=task.get("metrics"),
            categoryStats=task.get("categoryStats"),
            error=task.get("error")
        )

        return {
            "code": 200,
            "message": "Success",
            "data": result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classification/result/{task_id}")
async def get_classification_result(task_id: str):
    """获取分类结果"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]

        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "metrics": task["metrics"],
                "categoryStats": task["categoryStats"],
                "confusionMatrix": task.get("confusionMatrix")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classification/metrics/{task_id}")
async def get_classification_metrics(task_id: str):
    """获取分类指标"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]

        if not task.get("metrics"):
            raise HTTPException(status_code=400, detail="Metrics not available yet")

        return {
            "code": 200,
            "message": "Success",
            "data": task["metrics"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def simulate_classification_task(task_id: str, categories: List[str]):
    """模拟分类任务过程"""
    if task_id not in classification_tasks:
        return

    task = classification_tasks[task_id]
    task["status"] = "classifying"

    # 模拟分类过程，逐步更新指标
    for i in range(101):
        if task_id not in classification_tasks:
            break

        task["progress"] = i

        # 逐步更新指标
        if i > 20:
            progress_factor = i / 100
            task["metrics"] = {
                "accuracy": round(0.7 + progress_factor * 0.25, 3),
                "precision": round(0.65 + progress_factor * 0.27, 3),
                "recall": round(0.68 + progress_factor * 0.20, 3),
                "f1Score": round(0.66 + progress_factor * 0.24, 3),
                "support": 1000,
                "confusionMatrix": generate_mock_confusion_matrix(categories),
                "classificationReport": {
                    cat: {
                        "precision": round(random.uniform(0.8, 0.95), 3),
                        "recall": round(random.uniform(0.75, 0.92), 3),
                        "f1Score": round(random.uniform(0.78, 0.93), 3),
                        "support": random.randint(80, 150)
                    } for cat in categories
                }
            }

        # 更新分类统计
        if i > 50:
            task["categoryStats"] = generate_mock_category_stats(categories)

        await asyncio.sleep(0.05)  # 更快的更新频率以实现平滑效果

    # 完成任务
    if task_id in classification_tasks:
        task["status"] = "completed"
        task["progress"] = 100
        task["endTime"] = datetime.now().isoformat()
        task["duration"] = 5000  # 5秒

        # 生成最终的混淆矩阵
        matrix = generate_mock_confusion_matrix(categories)
        task["confusionMatrix"] = {
            "categories": categories,
            "matrix": matrix,
            "labels": categories,
            "totalSamples": sum(sum(row) for row in matrix)
        }

# ==================== 混淆矩阵接口 ====================

@router.get("/confusion-matrix/{task_id}")
async def get_confusion_matrix_data(task_id: str):
    """获取混淆矩阵数据"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]

        if not task.get("confusionMatrix"):
            raise HTTPException(status_code=400, detail="Confusion matrix not available yet")

        return {
            "code": 200,
            "message": "Success",
            "data": task["confusionMatrix"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting confusion matrix data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/confusion-matrix/chart/{task_id}")
async def generate_confusion_matrix_chart(task_id: str):
    """生成混淆矩阵图表配置"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]
        confusion_matrix = task.get("confusionMatrix")

        if not confusion_matrix:
            raise HTTPException(status_code=400, detail="Confusion matrix not available yet")

        # 生成ECharts配置
        chart_config = {
            "title": {
                "text": "混淆矩阵",
                "left": "center",
                "textStyle": {"color": "#c9d1d9", "fontSize": 16}
            },
            "tooltip": {
                "position": "top",
                "formatter": "实际: {b}<br/>预测: {a}<br/>数量: {c}"
            },
            "grid": {"height": "50%", "top": "10%"},
            "xAxis": {
                "type": "category",
                "data": confusion_matrix["categories"],
                "splitArea": {"show": True},
                "axisLabel": {"color": "#c9d1d9"}
            },
            "yAxis": {
                "type": "category",
                "data": confusion_matrix["categories"],
                "splitArea": {"show": True},
                "axisLabel": {"color": "#c9d1d9"}
            },
            "visualMap": {
                "min": 0,
                "max": max(max(row) for row in confusion_matrix["matrix"]),
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "15%",
                "textStyle": {"color": "#c9d1d9"}
            },
            "series": [{
                "name": "混淆矩阵",
                "type": "heatmap",
                "data": [
                    [j, i, confusion_matrix["matrix"][i][j]]
                    for i in range(len(confusion_matrix["matrix"]))
                    for j in range(len(confusion_matrix["matrix"][i]))
                ],
                "label": {"show": True, "color": "#c9d1d9"},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }

        return {
            "code": 200,
            "message": "Success",
            "data": chart_config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating confusion matrix chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 分类结果统计接口 ====================

@router.get("/category-stats/{task_id}")
async def get_category_stats(task_id: str):
    """获取分类结果统计"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]

        if not task.get("categoryStats"):
            raise HTTPException(status_code=400, detail="Category stats not available yet")

        return {
            "code": 200,
            "message": "Success",
            "data": task["categoryStats"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/category-stats/update")
async def update_category_stats(request: CategoryStatsUpdateRequest):
    """实时更新分类结果统计"""
    try:
        if request.taskId not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[request.taskId]

        # 重新生成统计数据
        updated_stats = generate_mock_category_stats(request.categories)
        task["categoryStats"] = updated_stats

        return {
            "code": 200,
            "message": "Category stats updated successfully",
            "data": updated_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 实时分析状态接口 ====================

@router.get("/status/realtime")
async def get_real_time_analysis_status():
    """获取实时分析状态"""
    try:
        # 检查是否有正在运行的任务
        running_tasks = []
        total_samples = 0
        processed_samples = 0

        for task_dict in [keyword_extraction_tasks, preprocessing_tasks, classification_tasks]:
            for task in task_dict.values():
                if task["status"] in ["running", "classifying", "preprocessing"]:
                    running_tasks.append(task)
                    total_samples += 1000  # 假设每个任务处理1000个样本
                    processed_samples += int(task["progress"] * 10)

        current_task = None
        current_step = "待机中"
        is_running = len(running_tasks) > 0
        progress = 0

        if running_tasks:
            latest_task = max(running_tasks, key=lambda x: x["startTime"])
            current_task = latest_task["taskId"]
            progress = latest_task["progress"]

            if latest_task["status"] == "running":
                current_step = "关键词提取中"
            elif latest_task["status"] == "preprocessing":
                current_step = "数据预处理中"
            elif latest_task["status"] == "classifying":
                current_step = "智能分类中"

        status = RealTimeAnalysisStatus(
            isRunning=is_running,
            currentTask=current_task,
            progress=progress,
            estimatedTimeRemaining=max(0, int((100 - progress) * 0.1)) if is_running else None,
            processedSamples=processed_samples,
            totalSamples=total_samples,
            currentStep=current_step,
            queueLength=len(running_tasks)
        )

        return {
            "code": 200,
            "message": "Success",
            "data": status.model_dump()
        }
    except Exception as e:
        logger.error(f"Error getting real time analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/stop")
async def stop_analysis_task(task_id: str):
    """停止当前分析任务"""
    try:
        # 查找并停止任务
        task_found = False

        for task_dict in [keyword_extraction_tasks, preprocessing_tasks, classification_tasks]:
            if task_id in task_dict:
                task = task_dict[task_id]
                task["status"] = "failed"
                task["error"] = "Task stopped by user"
                task["endTime"] = datetime.now().isoformat()
                task_found = True
                break

        if not task_found:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "code": 200,
            "message": "Task stopped successfully",
            "data": {"success": True, "message": "任务已停止"}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping analysis task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/restart")
async def restart_analysis_task(task_id: str, background_tasks: BackgroundTasks):
    """重启分析任务"""
    try:
        # 查找任务
        task_found = False
        task_dict = None
        task = None

        for td in [keyword_extraction_tasks, preprocessing_tasks, classification_tasks]:
            if task_id in td:
                task_dict = td
                task = td[task_id]
                task_found = True
                break

        if not task_found:
            raise HTTPException(status_code=404, detail="Task not found")

        # 重置任务状态
        new_task_id = generate_task_id()
        new_task = task.copy()
        new_task["taskId"] = new_task_id
        new_task["status"] = "pending"
        new_task["progress"] = 0
        new_task["startTime"] = datetime.now().isoformat()
        new_task.pop("endTime", None)
        new_task.pop("error", None)

        task_dict[new_task_id] = new_task

        # 根据任务类型重启相应的后台任务
        if task_dict == keyword_extraction_tasks:
            background_tasks.add_task(
                simulate_keyword_extraction,
                new_task_id,
                task["sourceType"],
                task.get("sampleSize", 1000)
            )
        elif task_dict == preprocessing_tasks:
            steps = [step["name"] for step in task.get("steps", [])]
            background_tasks.add_task(simulate_progress_update, new_task_id, task_dict, 8, steps)
        elif task_dict == classification_tasks:
            categories = task.get("categories", ["robot", "vision"])
            background_tasks.add_task(simulate_classification_task, new_task_id, categories)

        return {
            "code": 200,
            "message": "Task restarted successfully",
            "data": {"taskId": new_task_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting analysis task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 历史记录和报告接口 ====================

@router.get("/history")
async def get_analysis_history(page: int = 1, pageSize: int = 10, sourceType: str = None, status: str = None):
    """获取分析历史记录"""
    try:
        # 生成模拟历史记录
        all_history = []

        for i in range(50):  # 生成50条历史记录
            start_time = datetime.now() - timedelta(days=random.randint(1, 30))
            end_time = start_time + timedelta(minutes=random.randint(5, 30))

            source_type = random.choice(list(SOURCE_CATEGORY_MAPPING.keys()))
            categories = SOURCE_CATEGORY_MAPPING[source_type]

            history = AnalysisHistory(
                id=f"history_{i+1}",
                sourceType=source_type,
                modelType=random.choice(["bert-base-001", "roberta-large-001"]),
                startTime=start_time.isoformat(),
                endTime=end_time.isoformat(),
                duration=int((end_time - start_time).total_seconds() * 1000),
                status=random.choice(["completed", "failed"]),
                metrics=ClassificationMetrics(
                    accuracy=round(random.uniform(0.8, 0.95), 3),
                    precision=round(random.uniform(0.75, 0.92), 3),
                    recall=round(random.uniform(0.78, 0.90), 3),
                    f1Score=round(random.uniform(0.76, 0.91), 3),
                    support=random.randint(800, 1200),
                    confusionMatrix=generate_mock_confusion_matrix(categories),
                    classificationReport={
                        cat: {
                            "precision": round(random.uniform(0.8, 0.95), 3),
                            "recall": round(random.uniform(0.75, 0.92), 3),
                            "f1Score": round(random.uniform(0.78, 0.93), 3),
                            "support": random.randint(80, 150)
                        } for cat in categories
                    }
                ),
                categoryStats=generate_mock_category_stats(categories),
                samplesProcessed=random.randint(800, 1200)
            )
            all_history.append(history)

        # 过滤
        filtered_history = all_history
        if sourceType:
            filtered_history = [h for h in filtered_history if h.sourceType == sourceType]
        if status:
            filtered_history = [h for h in filtered_history if h.status == status]

        # 分页
        total = len(filtered_history)
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        page_data = filtered_history[start_idx:end_idx]

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "data": [h.model_dump() for h in page_data],
                "total": total,
                "page": page,
                "pageSize": pageSize
            }
        }
    except Exception as e:
        logger.error(f"Error getting analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/generate/{task_id}")
async def generate_analysis_report(task_id: str):
    """生成分析报告"""
    try:
        if task_id not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[task_id]

        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")

        report_id = f"report_{uuid.uuid4().hex[:8]}"

        return {
            "code": 200,
            "message": "Report generated successfully",
            "data": {"reportId": report_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analysis report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}")
async def get_analysis_report(report_id: str):
    """获取分析报告"""
    try:
        # 生成模拟报告数据
        categories = ["robot", "agriculture", "landslide", "vision"]

        report = {
            "id": report_id,
            "title": f"数据分析报告 - {report_id}",
            "sourceType": "paper",
            "generatedAt": datetime.now().isoformat(),
            "summary": {
                "totalSamples": 1000,
                "categoriesFound": len(categories),
                "averageConfidence": round(random.uniform(0.85, 0.95), 3),
                "processingTime": random.randint(5000, 15000)
            },
            "metrics": {
                "accuracy": round(random.uniform(0.85, 0.95), 3),
                "precision": round(random.uniform(0.82, 0.93), 3),
                "recall": round(random.uniform(0.80, 0.91), 3),
                "f1Score": round(random.uniform(0.81, 0.92), 3),
                "support": 1000,
                "confusionMatrix": generate_mock_confusion_matrix(categories),
                "classificationReport": {
                    cat: {
                        "precision": round(random.uniform(0.8, 0.95), 3),
                        "recall": round(random.uniform(0.75, 0.92), 3),
                        "f1Score": round(random.uniform(0.78, 0.93), 3),
                        "support": random.randint(80, 150)
                    } for cat in categories
                }
            },
            "categoryStats": generate_mock_category_stats(categories),
            "recommendations": [
                "建议增加训练数据以提高模型准确性",
                "考虑使用更复杂的模型架构",
                "对数据进行更深入的预处理",
                "增加特征工程步骤"
            ],
            "charts": {
                "confusionMatrix": {
                    "categories": categories,
                    "matrix": generate_mock_confusion_matrix(categories),
                    "labels": categories,
                    "totalSamples": 1000
                },
                "categoryDistribution": [
                    {"category": cat, "count": random.randint(80, 150), "percentage": round(random.uniform(8, 15), 1)}
                    for cat in categories
                ],
                "confidenceDistribution": [
                    {"range": "0.9-1.0", "count": random.randint(400, 500)},
                    {"range": "0.8-0.9", "count": random.randint(300, 400)},
                    {"range": "0.7-0.8", "count": random.randint(100, 200)},
                    {"range": "0.6-0.7", "count": random.randint(50, 100)}
                ]
            }
        }

        return {
            "code": 200,
            "message": "Success",
            "data": report
        }
    except Exception as e:
        logger.error(f"Error getting analysis report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 导出接口 ====================

@router.post("/export")
async def export_analysis_result(request: ExportRequest):
    """导出分析结果"""
    try:
        if request.taskId not in classification_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = classification_tasks[request.taskId]

        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")

        # 生成导出数据
        export_data = {}

        if request.includeMetrics and task.get("metrics"):
            export_data["metrics"] = task["metrics"]

        if request.includeCategoryStats and task.get("categoryStats"):
            export_data["categoryStats"] = task["categoryStats"]

        if request.includeConfusionMatrix and task.get("confusionMatrix"):
            export_data["confusionMatrix"] = task["confusionMatrix"]

        if request.includeRawData:
            export_data["rawData"] = {
                "taskId": task["taskId"],
                "sourceType": task["sourceType"],
                "modelType": task["modelType"],
                "parameters": task["parameters"],
                "startTime": task["startTime"],
                "endTime": task.get("endTime"),
                "duration": task.get("duration")
            }

        # 根据格式生成不同的响应
        if request.format == "json":
            import json
            content = json.dumps(export_data, ensure_ascii=False, indent=2)
            media_type = "application/json"
            filename = f"analysis_result_{request.taskId}.json"
        elif request.format == "csv":
            # 简化的CSV导出
            content = "category,count,confidence,percentage\n"
            if export_data.get("categoryStats"):
                for cat, stats in export_data["categoryStats"].items():
                    content += f"{cat},{stats['count']},{stats['confidence']},{stats.get('percentage', 0)}\n"
            media_type = "text/csv"
            filename = f"analysis_result_{request.taskId}.csv"
        else:
            # 默认JSON格式
            import json
            content = json.dumps(export_data, ensure_ascii=False, indent=2)
            media_type = "application/json"
            filename = f"analysis_result_{request.taskId}.json"

        from fastapi.responses import Response
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting analysis result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/status/{task_id}")
async def get_export_task_status(task_id: str):
    """获取导出任务状态"""
    try:
        # 模拟导出任务状态
        status = {
            "status": "completed",
            "progress": 100,
            "downloadUrl": f"/api/analysis/export/download/{task_id}",
            "error": None
        }

        return {
            "code": 200,
            "message": "Success",
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting export task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 配置接口 ====================

@router.get("/config")
async def get_analysis_config():
    """获取分析配置"""
    try:
        config = {
            "defaultModel": "bert-base-001",
            "batchSize": 32,
            "threshold": 0.8,
            "enableAutoPreprocessing": True,
            "maxConcurrentTasks": 3
        }

        return {
            "code": 200,
            "message": "Success",
            "data": config
        }
    except Exception as e:
        logger.error(f"Error getting analysis config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/config")
async def update_analysis_config(config: Dict[str, Any]):
    """更新分析配置"""
    try:
        # 这里应该保存配置到数据库或配置文件
        # 目前只是模拟更新
        logger.info(f"Updating analysis config: {config}")

        return {
            "code": 200,
            "message": "Configuration updated successfully",
            "data": {"success": True, "message": "配置更新成功"}
        }
    except Exception as e:
        logger.error(f"Error updating analysis config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 数据流动画接口 ====================

@router.get("/data-flow/status")
async def get_data_flow_status():
    """获取数据流状态"""
    try:
        # 检查当前运行的任务来确定数据流状态
        current_step = "数据源选择"
        steps = [
            {"name": "数据源选择", "status": "completed", "progress": 100},
            {"name": "关键词提取", "status": "pending", "progress": 0},
            {"name": "数据预处理", "status": "pending", "progress": 0},
            {"name": "智能分类", "status": "pending", "progress": 0},
            {"name": "结果展示", "status": "pending", "progress": 0}
        ]

        # 根据运行中的任务更新步骤状态
        for task_dict, step_name in [
            (keyword_extraction_tasks, "关键词提取"),
            (preprocessing_tasks, "数据预处理"),
            (classification_tasks, "智能分类")
        ]:
            for task in task_dict.values():
                if task["status"] in ["running", "classifying", "preprocessing"]:
                    current_step = step_name
                    for step in steps:
                        if step["name"] == step_name:
                            step["status"] = "active"
                            step["progress"] = task["progress"]
                        elif step["name"] in ["数据源选择"]:
                            step["status"] = "completed"
                            step["progress"] = 100
                elif task["status"] == "completed":
                    for step in steps:
                        if step["name"] == step_name:
                            step["status"] = "completed"
                            step["progress"] = 100
                        elif step["name"] == "结果展示":
                            step["status"] = "active"
                            step["progress"] = 100
                            current_step = "结果展示"

        status = DataFlowStatus(
            currentStep=current_step,
            steps=steps
        )

        return {
            "code": 200,
            "message": "Success",
            "data": status.model_dump()
        }
    except Exception as e:
        logger.error(f"Error getting data flow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data-flow/update")
async def update_data_flow_status(request: Dict[str, str]):
    """更新数据流状态"""
    try:
        step = request.get("step")

        if not step:
            raise HTTPException(status_code=400, detail="Step parameter is required")

        # 这里可以更新数据流状态
        # 目前只是返回成功响应

        return {
            "code": 200,
            "message": "Data flow status updated successfully",
            "data": {"success": True}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data flow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 健康检查接口 ====================

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "code": 200,
        "message": "Data Analysis Modal API is healthy",
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "activeTasks": {
                "keywordExtraction": len(keyword_extraction_tasks),
                "preprocessing": len(preprocessing_tasks),
                "classification": len(classification_tasks)
            }
        }
    }
