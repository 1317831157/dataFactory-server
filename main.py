from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
import sys
from contextlib import asynccontextmanager
from services.init_services import initialize_services, cleanup_services
from services.database import init_db
from routers.data_factory_api import router as data_factory_router
from routers import processing_db
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
    await init_db()
    await initialize_services()
    logger.info("Services initialized successfully")
    yield
    # 关闭时执行
    logger.info("Application shutdown: cleaning up resources...")
    await cleanup_services()

# 导入路由
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
    # 注册数据工厂API路由
    app.include_router(data_factory_router, prefix="", tags=["数据工厂"])
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

# 注册 processing_db 路由
try:
    app.include_router(processing_db.router)
    logger.info("Registered processing_db router with download functionality")
except Exception as e:
    logger.error(f"Failed to register processing_db router: {e}")

# 导入新的仪表盘路由
try:
    from routers.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info(f"Registered dashboard router with routes: {[route.path for route in dashboard_router.routes]}")
except ImportError as e:
    logger.error(f"Failed to import dashboard router: {e}")

# 导入数据分析模态框路由
try:
    from routers.data_analysis_modal import router as data_analysis_modal_router
    app.include_router(data_analysis_modal_router, prefix="", tags=["数据分析模态框"])
    logger.info("Registered data analysis modal router")
except ImportError as e:
    logger.error(f"Failed to import data analysis modal router: {e}")

# 导入数据展示模态框API路由
try:
    from routers.data_display_modal_api import router as data_display_modal_api_router
    app.include_router(data_display_modal_api_router, prefix="", tags=["数据展示模态框API"])
    logger.info("Registered data display modal API router")
except ImportError as e:
    logger.error(f"Failed to import data display modal API router: {e}")



@app.get("/")
async def root():
    return {"message": "数据工厂 API 服务已启动"}

if __name__ == "__main__":
    # 过滤掉uvicorn的一些冗余日志
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 启动服务器，只监视server目录下的变化
    current_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get('SERVER_PORT', 8001)),
        reload=True,
        reload_dirs=[current_dir]  # 只监视当前目录
    )

