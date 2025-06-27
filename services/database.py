import motor.motor_asyncio
from beanie import init_beanie, Document
from pydantic import Field, BaseModel
from typing import List, Dict, Any
from datetime import datetime
import logging
from services.alert_service import Alert
from models.paper import Paper
logger = logging.getLogger(__name__)

# --- 1. 数据模型定义 (Models) ---
# 这些模型定义了数据在MongoDB中的结构
# 使用Beanie的Document，可以直接映射到数据库的集合(Collection)

class DataSource(Document):
    """
    数据源模型，代表一个需要被分析的数据集文件夹。
    这会替代 auto_analysis_cache.json 的功能。
    """
    path: str = Field(..., description="文件夹的绝对路径", index=True, unique=True)
    name: str = Field(..., description="文件夹名称")
    category: str = Field(..., description="数据源的分类 (如: arxiv, cnki)", index=True)
    file_count: int = Field(..., description="文件夹内的文件数量")
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "data_sources" # MongoDB中集合的名称

class AnalyzedFile(BaseModel):
    """
    内嵌模型，代表一个被分析过的文件信息。
    """
    name: str
    path: str
    size: int
    type: str
    modified: datetime

class AnalyzedFolder(BaseModel):
    """
    内嵌模型，代表一个被分析过的文件夹及其包含的文件信息。
    """
    folder_name: str
    folder_path: str
    file_count: int
    files: List[AnalyzedFile]

class AnalysisResult(Document):
    """
    分析结果模型，用于持久化存储一次分析任务的完整结果。
    这将替代之前存储在内存中的 `_analysis_results` 变量。
    """
    source_type: str = Field(..., description="分析的数据源类型", index=True, unique=True)
    timestamp: datetime = Field(..., description="分析完成的时间戳")
    analyzed_folders_count: int = Field(..., description="成功分析的文件夹数量")
    results: List[AnalyzedFolder] = Field(..., description="详细分析结果列表")
    status: str = Field(default="pending", description="任务状态: pending, running, completed, failed")

    class Settings:
        name = "analysis_results"

class Task(Document):
    """
    统一任务管理模型，用于跟踪所有后台任务的状态。
    """
    task_type: str = Field(..., description="任务类型 (e.g., 'resource_analysis', 'source_analysis')", index=True)
    status: str = Field(default="pending", description="任务状态: pending, running, completed, failed", index=True)
    progress: int = Field(default=0, description="任务进度 (0-100)")
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime | None = None
    result: Dict[str, Any] | None = None
    error: str | None = None
    related_id: str | None = Field(None, description="关联的ID (e.g., source_type for analysis)", index=True)

    class Settings:
        name = "tasks"

# --- 2. 数据库客户端初始化 ---
# 数据库连接配置

# TODO: 在生产环境中，强烈建议使用环境变量来管理这些敏感信息
MONGO_USER = "user"
MONGO_PASSWORD = "password"
MONGO_HOST = "localhost"
DB_NAME = "data_factory"

# 构建数据库连接字符串
DATABASE_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:27017"

# 创建异步客户端
client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URI,
    # 设置服务器选择超时时间为5秒
    serverSelectionTimeoutMS=5000
)

# --- 3. 数据库初始化函数 ---
async def init_db():
    """
    初始化数据库连接和Beanie。
    这个函数将在FastAPI应用启动时调用。
    """
    try:
        logger.info("Connecting to MongoDB...")
        # 获取数据库实例
        database = client[DB_NAME]

        # 初始化Beanie，传入数据库实例和所有需要映射的Document模型
        await init_beanie(
            database=database,
            document_models=[
                DataSource,
                AnalysisResult,
                Task,
                Alert,
                Paper
            ]
        )
        logger.info("Successfully connected to MongoDB and initialized Beanie!")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # 在无法连接到数据库时，可以决定是否要让应用启动失败
        # 这里我们只记录错误，但也可以选择抛出异常来中断启动
        raise 