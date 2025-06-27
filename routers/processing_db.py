from fastapi import APIRouter, Query
from services import processing_service
from routers.processing import success, fail
# from typing import List, Tuple, Dict, Any
from typing import List, Optional, Dict, Any
from models.paper import Paper
from datetime import datetime,timedelta

router = APIRouter(prefix="/processing", tags=["数据处理-DB"])

@router.get("/papers/valid")
async def api_list_valid_papers(page: int = 1, pageSize: int = 10, sortBy: str = "timestamp", sortOrder: str = "desc"):
    """
    分页获取有效论文列表。
    - page: 页码，从1开始
    - pageSize: 每页数量
    - sortBy: 排序字段
    - sortOrder: 排序方式 desc/asc
    """
    try:
        papers, total = await processing_service.list_valid_papers(page, pageSize, sortBy, sortOrder)
        return success({"data": papers, "page": page, "pageSize": pageSize, "total": total})
    except Exception as e:
        return fail(str(e))

@router.get("/papers/{paper_id}")
async def api_detail_paper(paper_id: str):
    """
    获取单个论文详情。
    - paper_id: 论文ID
    """
    try:
        paper = await processing_service.detail_paper(paper_id)
        if paper:
            return success(paper)
        else:
            return fail("未找到论文", code=404)
    except Exception as e:
        return fail(str(e))

@router.get("/formulas")
async def api_list_formula_images(page: int = 1, pageSize: int = 20):
    """
    分页获取公式图片列表。
    - page: 页码
    - pageSize: 每页数量
    """
    try:
        formulas, total = await processing_service.list_formula_images(page, pageSize)
        return success({"data": formulas, "page": page, "pageSize": pageSize, "total": total})
    except Exception as e:
        return fail(str(e))

@router.get("/formulas/{formula_id}")
async def api_detail_formula(formula_id: str):
    """
    获取单个公式图片详情。
    - formula_id: 公式ID
    """
    try:
        formula = await processing_service.detail_formula(formula_id)
        if formula:
            return success(formula)
        else:
            return fail("未找到公式图片", code=404)
    except Exception as e:
        return fail(str(e))

@router.get("/trash")
async def api_list_trash_data(page: int = 1, pageSize: int = 10):
    """
    分页获取垃圾数据列表。
    - page: 页码
    - pageSize: 每页数量
    """
    try:
        trash, total = await processing_service.list_trash_data(page, pageSize)
        return success({"data": trash, "page": page, "pageSize": pageSize, "total": total})
    except Exception as e:
        return fail(str(e))

@router.get("/trash/{trash_id}")
async def api_detail_trash(trash_id: str):
    """
    获取单个垃圾数据详情。
    - trash_id: 垃圾数据ID
    """
    try:
        trash = await processing_service.detail_trash(trash_id)
        if trash:
            return success(trash)
        else:
            return fail("未找到垃圾数据", code=404)
    except Exception as e:
        return fail(str(e)) 


# 统计数量
@router.get("/realtime-stats")
async def get_realtime_stats():
    try:
        # 总论文量
        total_count = await Paper.count()
        # 统计最近1分钟的处理速度
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        process_speed = await Paper.find(Paper.timestamp >= one_minute_ago.isoformat()).count()
        data = {
            "processSpeed": process_speed,
            "totalCount": total_count
        }
        return success(data)
    except Exception as e:
        return fail(str(e))

@router.get("/trend-data")
def get_trend_data(timeRange: Optional[str] = Query(None)):
    try:
        data = {"hourlyData": [10]*24}
        return success(data)
    except Exception as e:
        return fail(str(e))