#!/usr/bin/env python3
"""
数据库强制清理脚本
直接清除数据库中的所有数据，无需确认
"""

import asyncio
import logging
import sys
import os

# 添加server目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(current_dir)
sys.path.insert(0, server_dir)

# 导入数据库相关模块
from services.database import init_db, client, DB_NAME

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def force_clear_database():
    """强制清除数据库所有数据"""
    try:
        logger.info("开始清理数据库...")
        
        # 初始化数据库连接
        await init_db()
        logger.info("数据库连接已建立")
        
        # 获取数据库实例
        db = client[DB_NAME]
        
        # 获取所有集合名称
        collection_names = await db.list_collection_names()
        logger.info(f"发现 {len(collection_names)} 个集合")
        
        if not collection_names:
            logger.info("数据库中没有集合，无需清理")
            return True
        
        # 清除每个集合的数据
        total_deleted = 0
        for collection_name in collection_names:
            try:
                collection = db[collection_name]
                
                # 获取清理前的文档数量
                count_before = await collection.count_documents({})
                
                if count_before > 0:
                    # 删除所有文档
                    result = await collection.delete_many({})
                    logger.info(f"集合 '{collection_name}': 删除 {result.deleted_count} 个文档")
                    total_deleted += result.deleted_count
                else:
                    logger.info(f"集合 '{collection_name}': 空集合")
                    
            except Exception as e:
                logger.error(f"清理集合 '{collection_name}' 失败: {e}")
        
        logger.info(f"数据库清理完成！总计删除 {total_deleted} 个文档")
        return True
        
    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        return False


async def main():
    """主函数"""
    try:
        success = await force_clear_database()
        
        if success:
            print("✅ 数据库清理成功完成")
            return 0
        else:
            print("❌ 数据库清理失败")
            return 1
            
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        return 1
    finally:
        # 关闭数据库连接
        if client:
            client.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
