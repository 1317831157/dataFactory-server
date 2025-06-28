from fastapi import APIRouter, Query, HTTPException, Path
from fastapi.responses import FileResponse, StreamingResponse
from services import processing_service
from typing import List, Optional, Dict, Any
from models.paper import Paper
from datetime import datetime, timedelta
import os
import json
import logging

logger = logging.getLogger(__name__)

# 定义响应函数
def success(data, message="success"):
    """成功响应"""
    return {"code": 200, "message": message, "data": data}

def fail(message, code=500):
    """失败响应"""
    return {"code": code, "message": message, "data": None}

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
        return success({"papers": papers, "total": total, "page": page, "pageSize": pageSize})
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
            return fail("论文不存在", code=404)
    except Exception as e:
        return fail(str(e))

@router.get("/statistics")
async def api_get_processing_statistics():
    """
    获取数据处理统计信息。
    """
    try:
        stats = await processing_service.get_processing_statistics()
        return success(stats)
    except Exception as e:
        return fail(str(e))

@router.get("/formulas")
async def api_list_formulas(page: int = 1, pageSize: int = 10):
    """
    分页获取公式列表。
    - page: 页码，从1开始
    - pageSize: 每页数量
    """
    try:
        formulas, total = await processing_service.list_formulas(page, pageSize)
        return success({"data": formulas, "total": total, "page": page, "pageSize": pageSize})
    except Exception as e:
        return fail(str(e))

@router.get("/trend-data")
def get_trend_data(timeRange: Optional[str] = Query(None)):
    try:
        data = {"hourlyData": [10]*24}
        return success(data)
    except Exception as e:
        return fail(str(e))

# 统计数量Add commentMore actions
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
@router.get("/papers/{paper_id}/download")
async def download_paper(paper_id: str = Path(...), format: Optional[str] = Query("pdf")):
    """
    下载论文文件
    - paper_id: 论文ID
    - format: 文件格式 (pdf, txt, json)
    """
    try:
        logger.info(f"开始下载论文: {paper_id}, 格式: {format}")

        # 从数据库获取论文信息
        paper = await Paper.get(paper_id)
        if not paper:
            logger.error(f"论文不存在: {paper_id}")
            raise HTTPException(status_code=404, detail="论文不存在")

        logger.info(f"找到论文: {paper.title}, 文件路径: {paper.file_path}")

        # 检查文件路径是否存在
        if not paper.file_path or not os.path.exists(paper.file_path):
            logger.error(f"论文文件不存在: {paper.file_path}")
            raise HTTPException(status_code=404, detail="论文文件不存在")

        file_path = paper.file_path
        
        if format == "pdf":
            # 直接返回PDF文件
            if not file_path.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail="原文件不是PDF格式")
            
            # 清理文件名，移除特殊字符
            safe_filename = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename[:50] if len(safe_filename) > 50 else safe_filename  # 限制长度
            if not safe_filename:
                safe_filename = f"paper_{paper_id}"
            
            return FileResponse(
                path=file_path,
                media_type="application/pdf",
                filename=f"{safe_filename}.pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{safe_filename}.pdf\"",
                    "Content-Type": "application/pdf"
                }
            )
        
        elif format == "txt":
            # 提取PDF文本内容
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text_content = ""
                for page in doc:
                    text_content += page.get_text()
                doc.close()
                
                # 清理文件名
                safe_filename = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_filename = safe_filename[:50] if len(safe_filename) > 50 else safe_filename
                if not safe_filename:
                    safe_filename = f"paper_{paper_id}"
                
                # 返回文本内容
                return StreamingResponse(
                    iter([text_content.encode('utf-8')]),
                    media_type="text/plain",
                    headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}.txt\""}
                )
            except Exception as e:
                logger.error(f"提取PDF文本失败: {e}")
                raise HTTPException(status_code=500, detail="文本提取失败")
        
        elif format == "json":
            # 返回论文元数据JSON
            paper_data = {
                "id": str(paper.id),
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "source": paper.source,
                "timestamp": paper.timestamp,
                "wordCount": paper.wordCount,
                "imageCount": paper.imageCount,
                "formulaCount": paper.formulaCount,
                "topics": paper.topics,
                "type": paper.type,
                "file_path": paper.file_path
            }
            
            # 清理文件名
            safe_filename = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename[:50] if len(safe_filename) > 50 else safe_filename
            if not safe_filename:
                safe_filename = f"paper_{paper_id}"
            
            json_content = json.dumps(paper_data, ensure_ascii=False, indent=2)
            return StreamingResponse(
                iter([json_content.encode('utf-8')]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}.json\""}
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载论文失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")
