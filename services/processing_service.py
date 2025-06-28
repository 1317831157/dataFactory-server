from models.paper import Paper
from models.formula import Formula
from models.trash import Trash
from typing import List, Optional, Tuple, Dict, Any
from bson import ObjectId

# ==================== 论文相关 ====================

async def list_valid_papers(page: int, page_size: int, sort_by: str = "timestamp", sort_order: str = "desc", filters: Dict[str, Any] = None) -> Tuple[List[dict], int]:
    """
    分页获取所有有效论文（type=valid），支持排序和过滤。
    :param page: 页码，从1开始
    :param page_size: 每页数量
    :param sort_by: 排序字段
    :param sort_order: 排序方式 desc/asc
    :param filters: 额外的MongoDB查询条件（如 {"source": "arxiv"}）
    :return: (论文列表, 总数)
    """
    query_dict = {"type": "valid"}
    if filters:
        query_dict.update(filters)
    query = Paper.find(query_dict)
    total = await query.count()
    sort = [(sort_by, -1 if sort_order == "desc" else 1)] if sort_by else None
    papers = await query.sort(*sort).skip((page-1)*page_size).limit(page_size).to_list()

    # 清理数据，确保必要字段存在
    cleaned_papers = []
    for p in papers:
        paper_dict = p.model_dump()
        # 确保 topics 字段存在且为列表
        if 'topics' not in paper_dict or paper_dict['topics'] is None:
            paper_dict['topics'] = []
        # 确保 authors 字段存在且为列表
        if 'authors' not in paper_dict or paper_dict['authors'] is None:
            paper_dict['authors'] = []
        cleaned_papers.append(paper_dict)

    return cleaned_papers, total

async def detail_paper(paper_id: str) -> Optional[dict]:
    """
    获取单个论文详情。
    :param paper_id: 论文ID
    :return: 论文字典或None
    """
    try:
        paper = await Paper.get(ObjectId(paper_id))
        return paper.model_dump() if paper else None
    except Exception:
        return None

# ==================== 公式图片相关 ====================

async def list_formula_images(page: int, page_size: int, filters: Dict[str, Any] = None) -> Tuple[List[dict], int]:
    """
    分页获取所有公式图片，支持过滤。
    :param filters: MongoDB查询条件
    """
    query_dict = {}
    if filters:
        query_dict.update(filters)
    query = Formula.find(query_dict)
    total = await query.count()
    formulas = await query.skip((page-1)*page_size).limit(page_size).to_list()
    return [f.model_dump() for f in formulas], total

async def detail_formula(formula_id: str) -> Optional[dict]:
    """
    获取单个公式图片详情。
    :param formula_id: 公式ID
    :return: 公式图片字典或None
    """
    try:
        formula = await Formula.get(ObjectId(formula_id))
        return formula.model_dump() if formula else None
    except Exception:
        return None

# ==================== 垃圾数据相关 ====================

async def list_trash_data(page: int, page_size: int, filters: Dict[str, Any] = None) -> Tuple[List[dict], int]:
    """
    分页获取所有垃圾数据，支持过滤。
    :param filters: MongoDB查询条件
    """
    query_dict = {}
    if filters:
        query_dict.update(filters)
    query = Trash.find(query_dict)
    total = await query.count()
    trash = await query.skip((page-1)*page_size).limit(page_size).to_list()
    return [t.model_dump() for t in trash], total

async def detail_trash(trash_id: str) -> Optional[dict]:
    """
    获取单个垃圾数据详情。
    :param trash_id: 垃圾数据ID
    :return: 垃圾数据字典或None
    """
    try:
        trash = await Trash.get(ObjectId(trash_id))
        return trash.model_dump() if trash else None
    except Exception:
        return None

# TODO: 可继续扩展批量操作、删除、恢复等函数，结合项目业务。 