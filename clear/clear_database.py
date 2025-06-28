#!/usr/bin/env python3
"""
数据库清理脚本
清除数据库中的所有数据
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
from services.database import Task, DataSource, AnalysisResult
from models.paper import Paper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def clear_all_collections():
    """清除所有集合中的数据"""
    try:
        # 初始化数据库连接
        await init_db()
        logger.info("数据库连接已建立")
        
        # 获取数据库实例
        db = client[DB_NAME]
        
        # 获取所有集合名称
        collection_names = await db.list_collection_names()
        logger.info(f"发现 {len(collection_names)} 个集合: {collection_names}")
        
        if not collection_names:
            logger.info("数据库中没有集合，无需清理")
            return
        
        # 清除每个集合的数据
        cleared_collections = []
        for collection_name in collection_names:
            try:
                collection = db[collection_name]
                
                # 获取清理前的文档数量
                count_before = await collection.count_documents({})
                
                if count_before > 0:
                    # 删除所有文档
                    result = await collection.delete_many({})
                    logger.info(f"集合 '{collection_name}': 删除了 {result.deleted_count} 个文档")
                    cleared_collections.append({
                        'name': collection_name,
                        'deleted_count': result.deleted_count
                    })
                else:
                    logger.info(f"集合 '{collection_name}': 已经是空的")
                    
            except Exception as e:
                logger.error(f"清理集合 '{collection_name}' 时出错: {e}")
        
        # 输出清理结果
        if cleared_collections:
            logger.info("=" * 50)
            logger.info("数据库清理完成！")
            logger.info("清理结果:")
            total_deleted = 0
            for item in cleared_collections:
                logger.info(f"  - {item['name']}: {item['deleted_count']} 个文档")
                total_deleted += item['deleted_count']
            logger.info(f"总计删除: {total_deleted} 个文档")
        else:
            logger.info("数据库已经是空的，无需清理")
            
    except Exception as e:
        logger.error(f"清理数据库时发生错误: {e}")
        raise


async def clear_specific_collections():
    """清除特定的已知集合"""
    try:
        # 初始化数据库连接
        await init_db()
        logger.info("数据库连接已建立")
        
        # 定义要清理的集合和对应的模型
        collections_to_clear = [
            ("tasks", Task),
            ("data_sources", DataSource), 
            ("analysis_results", AnalysisResult),
            ("papers", Paper)
        ]
        
        cleared_count = 0
        
        for collection_name, model_class in collections_to_clear:
            try:
                # 获取清理前的文档数量
                count_before = await model_class.count()
                
                if count_before > 0:
                    # 删除所有文档
                    await model_class.delete_all()
                    logger.info(f"集合 '{collection_name}': 删除了 {count_before} 个文档")
                    cleared_count += count_before
                else:
                    logger.info(f"集合 '{collection_name}': 已经是空的")
                    
            except Exception as e:
                logger.error(f"清理集合 '{collection_name}' 时出错: {e}")
        
        logger.info("=" * 50)
        logger.info("特定集合清理完成！")
        logger.info(f"总计删除: {cleared_count} 个文档")
            
    except Exception as e:
        logger.error(f"清理特定集合时发生错误: {e}")
        raise


async def confirm_and_clear():
    """确认后清理数据库"""
    print("=" * 60)
    print("🗑️  数据库清理脚本")
    print("=" * 60)
    print("⚠️  警告: 此操作将删除数据库中的所有数据！")
    print("📋 将要清理的数据包括:")
    print("   - 所有任务记录 (tasks)")
    print("   - 所有数据源记录 (data_sources)")
    print("   - 所有分析结果 (analysis_results)")
    print("   - 所有论文记录 (papers)")
    print("   - 其他所有集合中的数据")
    print("")
    
    # 用户确认
    while True:
        confirm = input("确定要继续吗？输入 'YES' 确认，'no' 取消: ").strip()
        if confirm == "YES":
            print("开始清理数据库...")
            break
        elif confirm.lower() in ['no', 'n']:
            print("操作已取消")
            return False
        else:
            print("请输入 'YES' 或 'no'")
    
    try:
        # 执行清理
        await clear_all_collections()
        
        print("=" * 60)
        print("✅ 数据库清理完成！")
        print("💡 提示: 重启应用程序以重新初始化数据")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False


async def main():
    """主函数"""
    try:
        success = await confirm_and_clear()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        return 1
    finally:
        # 关闭数据库连接
        if client:
            client.close()
            logger.info("数据库连接已关闭")


if __name__ == "__main__":
    # 运行脚本
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
