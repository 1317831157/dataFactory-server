import os
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from services.database import DataSource, AnalysisResult, AnalyzedFolder, AnalyzedFile, Task
from bson import ObjectId
from beanie.odm.operators.update.general import Set

logger = logging.getLogger(__name__)

class SourceAnalysisService:
    """
    数据源分析服务 - 使用MongoDB进行持久化和统一任务管理。
    """
    
    # @staticmethod
    # async def analyze_source_by_type(source_type: str, limit: int = 100, task_id: str | None = None) -> str:
    #     """
    #     根据数据源类型分析文件，并将结果存入数据库。任务状态通过Task模型统一管理。
    #     返回 task_id。
    #     """
    #     # 1. 创建或获取 Task
    #     if not task_id:
    #         task = Task(
    #             task_type="source_analysis",
    #             related_id=source_type,
    #             status="pending",
    #             progress=0
    #         )
    #         await task.insert()
    #         task_id = str(task.id)
    #     else:
    #         task = await Task.get(ObjectId(task_id))
    #         if not task:
    #             raise Exception(f"Task {task_id} not found")
        
    #     try:
    #         await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"status": "running", "progress": 5}})
    #         logger.info(f"Starting analysis for source type: '{source_type}' (task_id={task_id})")

    #         # 2. 查找Task表中同类型的已完成任务，提取所有文件数据
    #         same_type_tasks = await Task.find({
    #             "task_type": "auto_resource_analysis",
    #         }).sort("-end_time").limit(limit).to_list()
    #         logger.info(f"Found {len(same_type_tasks)} tasks in DB for source_type '{source_type}'.")

    #         analysis_result_list = []
    #         for task in same_type_tasks:
    #             if hasattr(task, "result") and task.result:
    #                 categories = task.result.get("categories", []) if isinstance(task.result, dict) else []
    #                 for category in categories:
    #                     files = category.get("files", [])
    #                     if files:
    #                         folder_name = category.get("name", "")
    #                         folder_path = os.path.dirname(files[0]["path"]) if files and "path" in files[0] else ""
    #                         file_count = len(files)
    #                         analysis_result_list.append({
    #                             "folder_name": folder_name,
    #                             "folder_path": folder_path,
    #                             "file_count": file_count,
    #                             "files": [{"name": f["name"], "path": f["path"], "status": "analyzed"} for f in files]
    #                         })
    #         print('analysis_result_list', analysis_result_list)
    #         # 4. 写入分析结果
    #         await AnalysisResult.find_one(AnalysisResult.source_type == source_type).upsert(
    #             Set({
    #                 AnalysisResult.status: "completed",
    #                 AnalysisResult.timestamp: datetime.now(),
    #                 AnalysisResult.results: analysis_result_list,
    #                 AnalysisResult.analyzed_folders_count: len(analysis_result_list)
    #             }),
    #             on_insert=AnalysisResult(
    #                 source_type=source_type,
    #                 timestamp=datetime.now(),
    #                 analyzed_folders_count=len(analysis_result_list),
    #                 results=analysis_result_list,
    #                 status="completed"
    #             )
    #         )
    #         await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"status": "completed", "progress": 100, "result": {"files": [f.get('path') for f in analysis_result_list]}, "end_time": datetime.now()}})
    #         logger.info(f"Successfully completed analysis for '{source_type}' (task_id={task_id}).")
    #         return task_id
    #     except Exception as e:
    #         logger.error(f"Error during analysis for '{source_type}': {e}", exc_info=True)
    #         await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"status": "failed", "error": str(e), "end_time": datetime.now()}})
    #         return task_id
    
    @staticmethod
    async def _analyze_folders(sources: List[DataSource], task_id: str = None) -> List[AnalyzedFolder]:
        """
        分析文件夹内容。输入的是DataSource模型列表。支持进度更新。
        """
        results = []
        total = len(sources)
        for idx, source in enumerate(sources):
            if not source.path or not os.path.exists(source.path):
                logger.warning(f"Path does not exist or is invalid, skipping: {source.path}")
                continue
            try:
                files_info: List[AnalyzedFile] = []
                for root, _, filenames in os.walk(source.path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        _, ext = os.path.splitext(filename)
                        if ext.lower() in ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.json']:
                            try:
                                files_info.append(AnalyzedFile(
                                    name=filename,
                                    path=file_path,
                                    size=os.path.getsize(file_path),
                                    type=ext.lower(),
                                    modified=datetime.fromtimestamp(os.path.getmtime(file_path))
                                ))
                            except Exception as file_e:
                                logger.warning(f"Could not process file {file_path}: {file_e}")
                results.append(AnalyzedFolder(
                    folder_name=source.name,
                    folder_path=source.path,
                    file_count=len(files_info),
                    files=files_info[:20]
                ))
                # 进度更新
                if task_id:
                    progress = 30 + int(50 * (idx + 1) / total)
                    await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"progress": progress}})
            except Exception as e:
                logger.error(f"Error analyzing folder {source.path}: {e}")
                continue
        return results
    
    @staticmethod
    async def get_analysis_result(source_type: str) -> AnalysisResult | None:
        """
        从数据库获取指定类型的最新分析结果。
        """
        # await AnalysisResult.find_all().delete()
        return await AnalysisResult.find_one(AnalysisResult.source_type == source_type)

    @staticmethod
    async def get_task_status(task_id: str) -> Dict:
        """
        查询分析任务的状态和进度。
        """
        try:
            task = await Task.get(ObjectId(task_id))
            if not task:
                return {"status": "not_found"}
            return task.model_dump(by_alias=True, exclude={'id'})
        except Exception:
            return {"status": "not_found", "error": "Invalid ID format"}

    @staticmethod
    async def analyze_source_by_type(source_type: str, limit: int = 100, task_id: str | None = None) -> str:
        """
        根据数据源类型分析文件，并将结果存入数据库。任务状态通过Task模型统一管理。
        返回 task_id。
        """
        # 1. 创建或获取 Task
        if not task_id:
            task = Task(
                task_type="source_analysis",
                related_id=source_type,
                status="pending",
                progress=0
            )
            await task.insert()
            task_id = str(task.id)
        else:
            task = await Task.get(ObjectId(task_id))
            if not task:
                raise Exception(f"Task {task_id} not found")
        
        try:
            await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"status": "running", "progress": 5}})
            logger.info(f"Starting analysis for source type: '{source_type}' (task_id={task_id})")

            # 2. 查找Task表中同类型的已完成任务，提取所有文件数据
            same_type_tasks = await Task.find({
                "task_type": "auto_resource_analysis",
            }).sort("-end_time").limit(limit).to_list()
            logger.info(f"Found {len(same_type_tasks)} tasks in DB for source_type '{source_type}'.")

            analysis_result_list = []
            for task in same_type_tasks:
                if hasattr(task, "result") and task.result:
                    categories = task.result.get("categories", []) if isinstance(task.result, dict) else []
                    for category in categories:
                        files = category.get("files", [])
                        if files:
                            folder_name = category.get("name", "")
                            folder_path = os.path.dirname(files[0]["path"]) if files and "path" in files[0] else ""
                            file_count = len(files)

                            # 构建符合 AnalyzedFile 模型要求的文件列表
                            analyzed_files = []
                            for f in files:
                                file_path = f.get("path", "")
                                file_name = f.get("name", "")

                                # 获取文件信息，如果文件不存在则使用默认值
                                try:
                                    if os.path.exists(file_path):
                                        file_size = os.path.getsize(file_path)
                                        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                                    else:
                                        file_size = 0
                                        file_modified = datetime.now()

                                    # 从文件名获取文件类型
                                    _, ext = os.path.splitext(file_name)
                                    file_type = ext.lower() if ext else ".unknown"

                                    analyzed_files.append({
                                        "name": file_name,
                                        "path": file_path,
                                        "size": file_size,
                                        "type": file_type,
                                        "modified": file_modified
                                    })
                                except Exception as file_e:
                                    logger.warning(f"Could not get file info for {file_path}: {file_e}")
                                    # 使用默认值
                                    analyzed_files.append({
                                        "name": file_name,
                                        "path": file_path,
                                        "size": 0,
                                        "type": ".unknown",
                                        "modified": datetime.now()
                                    })

                            analysis_result_list.append({
                                "folder_name": folder_name,
                                "folder_path": folder_path,
                                "file_count": file_count,
                                "files": analyzed_files
                            })
            # print('analysis_result_list', analysis_result_list)
            # 4. 写入分析结果
            await AnalysisResult.find_one(AnalysisResult.source_type == source_type).upsert(
                Set({
                    AnalysisResult.status: "completed",
                    AnalysisResult.timestamp: datetime.now(),
                    AnalysisResult.results: analysis_result_list,
                    AnalysisResult.analyzed_folders_count: len(analysis_result_list)
                }),
                on_insert=AnalysisResult(
                    source_type=source_type,
                    timestamp=datetime.now(),
                    analyzed_folders_count=len(analysis_result_list),
                    results=analysis_result_list,
                    status="completed"
                )
            )
            await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"status": "completed", "progress": 100, "result": {"files": [f.get('path') for f in analysis_result_list]}, "end_time": datetime.now()}})
            logger.info(f"Successfully completed analysis for '{source_type}' (task_id={task_id}).")
            return task_id
        except Exception as e:
            logger.error(f"Error during analysis for '{source_type}': {e}", exc_info=True)
            await Task.find_one(Task.id == ObjectId(task_id)).update({"$set": {"status": "failed", "error": str(e), "end_time": datetime.now()}})
            return task_id



