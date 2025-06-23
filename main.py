from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
import sys
from contextlib import asynccontextmanager
from services.init_services import initialize_services
from routers.data_factory_api import router as data_factory_router

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 定义应用生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("Application startup: initializing services...")
    await initialize_services()
    logger.info("Services initialized successfully")
    yield
    # 关闭时执行
    logger.info("Application shutdown: cleaning up resources...")

# 确保目录结构存在
for directory in ["routers", "services", "models"]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        with open(f"{directory}/__init__.py", "w") as f:
            f.write(f"# {directory} 包初始化文件\n")
        logger.info(f"Created directory: {directory}")

# 创建必要的文件
if not os.path.exists("routers/analysis.py"):
    from shutil import copyfile
    # 如果文件不存在，尝试从模板创建
    template_path = os.path.join(os.path.dirname(__file__), "templates/analysis.py.template")
    if os.path.exists(template_path):
        copyfile(template_path, "routers/analysis.py")
    else:
        # 如果模板不存在，创建一个基本文件
        with open("routers/analysis.py", "w") as f:
            f.write("""from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter()

class AnalysisRequest(BaseModel):
    directory: str
    options: Optional[Dict[str, Any]] = None

@router.post("/analyze")
async def start_analysis(request: AnalysisRequest):
    \"\"\"启动异步分析任务\"\"\"
    try:
        # 临时返回一个固定的任务ID
        return {"task_id": "test-task-id", "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/progress/{task_id}")
async def get_analysis_progress(task_id: str):
    \"\"\"获取分析任务进度\"\"\"
    # 临时返回一个固定的进度
    return {"status": "running", "progress": 50}

@router.get("/output")
async def get_analysis_output():
    \"\"\"获取分析结果\"\"\"
    # 临时返回一些示例数据
    return {
        "code": 200,
        "data": [
            {
                "id": 1,
                "name": "文档",
                "count": 42,
                "icon": "📄",
                "color": "#1890ff",
            },
            {
                "id": 2,
                "name": "图像",
                "count": 78,
                "icon": "🖼️",
                "color": "#52c41a",
            },
            {
                "id": 3,
                "name": "视频",
                "count": 15,
                "icon": "🎬",
                "color": "#722ed1",
            },
        ]
    }
""")
    logger.info("Created analysis.py file")

# 现在尝试导入路由
try:
    from routers import analysis
    logger.info("Successfully imported analysis router")
except ImportError as e:
    logger.error(f"Failed to import analysis router: {e}")
    # 创建一个空的路由器作为后备
    from fastapi import APIRouter
    class EmptyRouter:
        def __init__(self):
            self.router = APIRouter()
    analysis = EmptyRouter()
    logger.warning("Using empty router as fallback")

app = FastAPI(
    title="数据工厂 API",
    description="数据集生成工厂后端服务",
    version="0.1.0",
    lifespan=lifespan  # 使用lifespan上下文管理器
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
try:
    app.include_router(analysis.router, prefix="", tags=["数据分析"])
    logger.info("Registered analysis router")
except AttributeError:
    logger.error("Failed to register analysis router: router attribute not found")
    # 尝试直接使用analysis作为路由器
    try:
        app.include_router(analysis, prefix="", tags=["数据分析"])
        logger.info("Registered analysis as router")
    except Exception as e:
        logger.error(f"Failed to register analysis as router: {e}")

# 导入resource路由
try:
    from routers.resource import router as resource_router
    app.include_router(resource_router, prefix="", tags=["资源管理"])
    logger.info("Registered resource router")
except ImportError as e:
    logger.error(f"Failed to import resource router: {e}")

# 导入新的仪表盘路由
try:
    from routers.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info(f"Registered dashboard router with routes: {[route.path for route in dashboard_router.routes]}")
except ImportError as e:
    logger.error(f"Failed to import dashboard router: {e}")

app.include_router(data_factory_router, prefix="", tags=["数据工厂"])

@app.get("/")
async def root():
    return {"message": "数据工厂 API 服务已启动"}

# 删除已弃用的on_event处理器

if __name__ == "__main__":
    # 过滤掉uvicorn的一些冗余日志
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 启动服务器，只监视server目录下的变化
    current_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        reload_dirs=[current_dir]  # 只监视当前目录
    )












