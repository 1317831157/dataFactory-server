import asyncio
import json
import os
import logging
import sys
from typing import List, Dict

# 将项目根目录添加到Python的模块搜索路径中
# 这能确保脚本在任何位置都能正确导入 'services' 模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 配置日志，方便看到执行过程
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 导入我们的数据库初始化函数和数据源模型
# 延迟导入，确保在asyncio事件循环中进行
from services.database import init_db, DataSource

# 定义缓存文件的路径
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cache", "auto_analysis_cache.json")

async def main():
    """
    主迁移函数
    """
    logging.info("Starting data migration script...")
    
    # 1. 初始化数据库连接
    # 我们复用已有的init_db函数，确保连接方式和主应用完全一致
    try:
        await init_db()
    except Exception as e:
        logging.error(f"Failed to connect to the database. Aborting migration. Error: {e}")
        return

    # 2. 检查并读取JSON缓存文件
    if not os.path.exists(CACHE_FILE_PATH):
        logging.error(f"Cache file not found at: {CACHE_FILE_PATH}. Aborting migration.")
        return
        
    logging.info(f"Reading data from {CACHE_FILE_PATH}...")
    with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            cache_data = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON file. Error: {e}. Aborting migration.")
            return

    # 3. 解析数据并准备插入
    all_sources_from_file: List[DataSource] = []
    # 缓存文件的结构是 {"result": [...]}
    categories = cache_data.get("result", [])
    
    for category in categories:
        category_name = category.get("name", "uncategorized")
        folders: List[Dict] = category.get("folders", [])
        
        for folder in folders:
            # 确保必要字段存在
            if "path" in folder and "name" in folder and "file_count" in folder:
                # 创建一个DataSource对象
                source = DataSource(
                    path=folder["path"],
                    name=folder["name"],
                    category=category_name,
                    file_count=folder["file_count"],
                )
                all_sources_from_file.append(source)
            else:
                logging.warning(f"Skipping folder due to missing data: {folder}")
    
    if not all_sources_from_file:
        logging.warning("No valid data sources found in the cache file. Nothing to migrate.")
        return
        
    logging.info(f"Found {len(all_sources_from_file)} total records in the cache file.")

    # 4. 避免重复插入，只迁移新数据
    # 获取数据库中所有已存在的路径
    existing_paths = {source.path async for source in DataSource.find_all()}
    logging.info(f"Found {len(existing_paths)} records already in the database.")
    
    # 筛选出数据库中不存在的新数据
    new_sources_to_insert = [
        source for source in all_sources_from_file if source.path not in existing_paths
    ]

    # 5. 执行插入操作
    if not new_sources_to_insert:
        logging.info("No new data to migrate. The database is already up-to-date.")
    else:
        logging.info(f"Migrating {len(new_sources_to_insert)} new data sources to MongoDB...")
        try:
            # Beanie的insert_many可以高效地批量插入
            await DataSource.insert_many(new_sources_to_insert)
            logging.info("Successfully migrated new data!")
        except Exception as e:
            logging.error(f"An error occurred during database insertion: {e}")

    logging.info("Data migration script finished.")


if __name__ == "__main__":
    # 使用 asyncio.run() 来执行异步的 main 函数
    asyncio.run(main()) 