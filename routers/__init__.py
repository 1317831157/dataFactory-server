# 路由模块初始化文件# 导入所有路由模块，使它们可以从包中直接导入
try:    from .analysis import router as analysis_router
    # 为了向后兼容，保留原始导入名称    analysis = analysis_router
except ImportError:    # 如果模块不存在，创建一个空的路由器
    from fastapi import APIRouter




# 路由包初始化文件
