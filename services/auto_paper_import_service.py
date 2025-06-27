import os
from typing import List, Dict, Any
from models.paper import Paper
from datetime import datetime
from bson import ObjectId
import logging
import fitz  # PyMuPDF
from models.paper import Paper
logger = logging.getLogger(__name__)

class AutoPaperImportService:
    @staticmethod
    async def import_valid_papers_from_auto_analysis():
        """
        1. 调用 get_auto_analysis_result 获取分类数据
        2. 解析分类结果中的论文类文件，提取元数据
        3. 存入 Paper 表，type=valid
        """
        # 1. 获取自动分析分类结果
        from services.resource_service import ResourceService
        categories = await ResourceService.get_auto_analysis_result()

        if not categories:
            logger.warning("未获取到自动分析分类结果，无法导入论文。")
            return 0
            
        # 2. 找到论文类别（假设类别名为 '论文' 或 'paper'，可根据实际情况调整）
        paper_category = None
        for cat in categories:
            if cat.get("name") in ["学术论文"]:
                paper_category = cat
                break
        if not paper_category or not paper_category.get("files"):
            logger.info("未找到论文类别或无论文文件。"); return 0

        paper_files = paper_category["files"]
        
        imported_count = 0
        for file_info in paper_files:
            file_path = file_info.get("path")
            
            if not file_path or not os.path.exists(file_path) or not file_path.lower().endswith('.pdf'):
                continue
            metadata = AutoPaperImportService.parse_pdf_metadata(file_path)
            print('metadata',metadata)
            if not metadata:
                continue
            # 检查是否已存在同名论文
            exists = await Paper.find_one({"title": metadata["title"], "type": "valid"})
            if exists:
                continue
            # 构造Paper对象并保存
            paper = Paper(
                title=metadata["title"],
                authors=metadata.get("authors", []),
                abstract=metadata.get("abstract", ""),
                source=metadata.get("source", "auto_import"),
                type="valid",
                file_path=file_path,
                timestamp=datetime.now().isoformat(),
                wordCount=0,        # 你可以根据实际情况统计，否则传0
                imageCount=0,       # 同上
                formulaCount=0,     # 同上
                topics=[],          # 可以根据实际情况提取，否则传空列表
                image=None  
            )
            await paper.save()
            imported_count += 1
        logger.info(f"成功导入 {imported_count} 篇有效论文。")
        return imported_count

    @staticmethod
    def parse_pdf_metadata(file_path: str) -> Dict[str, Any]:
        """
        用 PyMuPDF 解析PDF文件，提取元数据（标题、作者、摘要）。
        """
        try:
            doc = fitz.open(file_path)
            meta = doc.metadata or {}
            # 尝试获取首页文本作为摘要
            abstract = ""
            if doc.page_count > 0:
                first_page = doc.load_page(0)
                abstract = first_page.get_text().strip().replace('\n', ' ')[:500]  # 取前500字
            return {
                "title": meta.get("title") or os.path.splitext(os.path.basename(file_path))[0],
                "authors": [meta.get("author")] if meta.get("author") else [],
                "abstract": abstract,
                "source": "auto_import"
            }
        except Exception as e:
            logger.error(f"解析PDF失败: {file_path}, 错误: {e}")
            return {
                "title": os.path.splitext(os.path.basename(file_path))[0],
                "authors": [],
                "abstract": "",
                "source": "auto_import"
            } 