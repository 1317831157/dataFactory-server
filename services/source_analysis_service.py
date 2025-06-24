import os
import json
import logging
import asyncio
from typing import Dict, List, Any
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

class SourceAnalysisService:
    """数据源分析服务 - 专门用于数据工厂的分析需求"""
    
    # 类变量，用于存储分析状态
    _analysis_running = False
    _analysis_results = {}
    
    @staticmethod
    async def analyze_source_by_type(source_type: str, limit: int = 100) -> str:
        """根据数据源类型分析文件
        
        Args:
            source_type: 数据源类型
            limit: 限制分析的文件数量
            
        Returns:
            str: 任务ID
        """
        try:
            # 防止重复运行
            if SourceAnalysisService._analysis_running:
                logger.info(f"Source analysis for {source_type} already running, skipping")
                return "already_running"
            
            SourceAnalysisService._analysis_running = True
            logger.info(f"Starting analysis for source type: {source_type}")
            
            # 读取缓存文件获取文件夹信息
            cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "auto_analysis_cache.json")
            if not os.path.exists(cache_file):
                logger.error("Cache file not found, cannot analyze source")
                SourceAnalysisService._analysis_running = False
                return "cache_not_found"
            
            # 加载缓存数据
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # 查找匹配的分类
            matching_folders = []
            source_type_lower = source_type.lower()
            
            for category in cache_data.get("result", []):
                category_name = category.get("name", "").lower()
                
                # 检查类别名称是否匹配源类型
                if source_type_lower in category_name:
                    # 收集该类别下的所有文件夹
                    if "folders" in category:
                        matching_folders.extend(category["folders"])
            
            # 如果没有找到匹配的文件夹，尝试部分匹配
            if not matching_folders:
                for category in cache_data.get("result", []):
                    if "folders" in category:
                        for folder in category["folders"]:
                            folder_name = folder.get("name", "").lower()
                            if source_type_lower in folder_name:
                                matching_folders.append(folder)
            
            # 限制文件夹数量
            if limit and len(matching_folders) > limit:
                matching_folders = matching_folders[:limit]
            
            # 分析匹配的文件夹
            logger.info(f"Analyzing {len(matching_folders)} matching folders")
            if not matching_folders:
                logger.warning("No matching folders found for analysis")
                SourceAnalysisService._analysis_running = False
                return "no_matching_folders"

            analysis_result = await SourceAnalysisService._analyze_folders(matching_folders)
            logger.info(f"分析结果: {len(analysis_result)}")
            if not analysis_result:
                logger.warning("Analysis completed but returned empty result")
            # 存储分析结果
            SourceAnalysisService._analysis_results[source_type] = {
                "timestamp": datetime.now().isoformat(),
                "count": len(matching_folders),
                "result": analysis_result
            }
            
            logger.info(f"Completed analysis for source type: {source_type}, found {len(matching_folders)} folders")
            SourceAnalysisService._analysis_running = False
            
            return "completed"
            
        except Exception as e:
            logger.error(f"Error analyzing source type {source_type}: {e}")
            SourceAnalysisService._analysis_running = False
            return f"error: {str(e)}"
    
    @staticmethod
    async def _analyze_folders(folders: List[Dict]) -> List[Dict]:
        """分析文件夹内容
        
        Args:
            folders: 文件夹列表
        
        Returns:
            List[Dict]: 分析结果
        """
        results = []
        
        logger.info(f"Starting to analyze {len(folders)} folders")
        for i, folder in enumerate(folders):
            folder_path = folder.get("path")
            folder_name = folder.get("name", "未知文件夹")
            
            logger.info(f"Processing folder {i+1}/{len(folders)}: {folder_name}")
            
            if not folder_path:
                logger.warning(f"Folder path is empty for {folder_name}")
                continue
                
            if not os.path.exists(folder_path):
                logger.warning(f"Folder path does not exist: {folder_path}")
                continue
            
            try:
                # 收集文件夹中的文件信息
                files = []
                file_count = 0
                
                for root, _, filenames in os.walk(folder_path):
                    for filename in filenames:
                        file_count += 1
                        file_path = os.path.join(root, filename)
                        _, ext = os.path.splitext(filename)
                        
                        # 只收集常见文件类型
                        if ext.lower() in ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx']:
                            try:
                                file_size = os.path.getsize(file_path)
                                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                                
                                files.append({
                                    "name": filename,
                                    "path": file_path,
                                    "size": file_size,
                                    "type": ext.lower(),
                                    "modified": file_modified
                                })
                            except Exception as e:
                                logger.warning(f"Error processing file {file_path}: {e}")
            
                logger.info(f"Found {file_count} total files, {len(files)} matching files in {folder_name}")
                
                # 添加到结果中
                results.append({
                    "folder_name": folder_name,
                    "folder_path": folder_path,
                    "file_count": len(files),
                    "files": files[:10]  # 只返回前10个文件，避免数据过大
                })
                logger.info(f"Added folder {folder_name} to results, current results count: {len(results)}")
            except Exception as e:
                logger.error(f"Error analyzing folder {folder_path}: {e}")
                continue
        
        logger.info(f"Analysis completed, returning {len(results)} folder results")
        return results
    
    @staticmethod
    async def get_analysis_result(source_type: str) -> Dict:
        """获取指定类型的分析结果
        
        Args:
            source_type: 数据源类型
            
        Returns:
            Dict: 分析结果
        """
        # 如果没有结果，返回空对象
        if source_type not in SourceAnalysisService._analysis_results:
            return {}
        
        return SourceAnalysisService._analysis_results[source_type]



