"""
数据源接口使用示例
演示如何使用集成了 get_auto_analysis_result 的数据源接口
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any

class DataSourcesExample:
    """数据源接口使用示例类"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_data_sources(self) -> List[Dict[str, Any]]:
        """获取数据源列表"""
        url = f"{self.base_url}/api/analysis/data-sources"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            else:
                print(f"Error getting data sources: {response.status}")
                return []
    
    async def get_source_category_mapping(self) -> Dict[str, List[str]]:
        """获取数据源分类映射"""
        url = f"{self.base_url}/api/analysis/source-category-mapping"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {})
            else:
                print(f"Error getting source category mapping: {response.status}")
                return {}
    
    async def analyze_data_sources(self):
        """分析数据源信息"""
        print("🔍 开始分析数据源...")
        
        # 获取数据源列表
        data_sources = await self.get_data_sources()
        print(f"\n📊 发现 {len(data_sources)} 个数据源:")
        
        # 统计信息
        total_count = 0
        source_types = {}
        auto_sources = 0
        default_sources = 0
        
        for source in data_sources:
            print(f"\n📁 {source['name']}")
            print(f"   类型: {source['type']}")
            print(f"   数量: {source['count']:,}")
            print(f"   描述: {source['description']}")
            print(f"   分类: {', '.join(source['categories'])}")
            print(f"   更新时间: {source['lastUpdated']}")
            
            # 统计
            total_count += source['count']
            source_type = source['type']
            source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # 检查数据来源
            if source['id'].startswith('auto-'):
                auto_sources += 1
                print(f"   🤖 来源: 自动分析结果")
            else:
                default_sources += 1
                print(f"   📋 来源: 默认数据源")
        
        # 显示统计信息
        print(f"\n📈 统计信息:")
        print(f"   总数据量: {total_count:,}")
        print(f"   自动分析数据源: {auto_sources}")
        print(f"   默认数据源: {default_sources}")
        print(f"   数据源类型分布:")
        for source_type, count in source_types.items():
            print(f"     - {source_type}: {count} 个")
        
        return data_sources
    
    async def analyze_category_mapping(self):
        """分析分类映射"""
        print("\n🗂️ 分析数据源分类映射...")
        
        mapping = await self.get_source_category_mapping()
        
        print(f"\n📋 分类映射关系:")
        for source_type, categories in mapping.items():
            print(f"   {source_type} → {', '.join(categories)}")
        
        # 统计分类使用情况
        category_usage = {}
        for categories in mapping.values():
            for category in categories:
                category_usage[category] = category_usage.get(category, 0) + 1
        
        print(f"\n📊 分类使用统计:")
        sorted_categories = sorted(category_usage.items(), key=lambda x: x[1], reverse=True)
        for category, usage_count in sorted_categories:
            print(f"   {category}: 被 {usage_count} 个数据源类型使用")
        
        return mapping
    
    async def validate_data_consistency(self):
        """验证数据一致性"""
        print("\n✅ 验证数据一致性...")
        
        data_sources = await self.get_data_sources()
        mapping = await self.get_source_category_mapping()
        
        issues = []
        
        for source in data_sources:
            source_type = source['type']
            source_categories = source['categories']
            
            # 检查数据源类型是否在映射中
            if source_type not in mapping:
                issues.append(f"数据源类型 '{source_type}' 不在映射中")
                continue
            
            # 检查分类是否一致
            expected_categories = mapping[source_type]
            if source_categories != expected_categories:
                issues.append(f"数据源 '{source['name']}' 的分类不一致: "
                            f"期望 {expected_categories}, 实际 {source_categories}")
        
        if issues:
            print("❌ 发现数据一致性问题:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ 数据一致性验证通过")
        
        return len(issues) == 0
    
    async def simulate_frontend_workflow(self):
        """模拟前端工作流程"""
        print("\n🎭 模拟前端工作流程...")
        
        # 1. 获取数据源列表（前端组件初始化时）
        print("1. 获取数据源列表...")
        data_sources = await self.get_data_sources()
        
        # 2. 获取分类映射（确定每个数据源支持的分类）
        print("2. 获取分类映射...")
        mapping = await self.get_source_category_mapping()
        
        # 3. 模拟用户点击数据源卡片
        if data_sources:
            selected_source = data_sources[0]
            print(f"3. 用户选择数据源: {selected_source['name']}")
            print(f"   支持的分类: {', '.join(selected_source['categories'])}")
            
            # 4. 开始分析流程（这里只是模拟，实际会调用其他接口）
            print("4. 开始数据分析流程...")
            print("   - 关键词提取")
            print("   - 数据预处理") 
            print("   - 智能分类")
            print("   - 结果展示")
        
        print("✅ 前端工作流程模拟完成")

async def main():
    """主函数"""
    print("🚀 数据源接口集成示例")
    print("=" * 50)
    
    async with DataSourcesExample() as example:
        try:
            # 分析数据源
            await example.analyze_data_sources()
            
            # 分析分类映射
            await example.analyze_category_mapping()
            
            # 验证数据一致性
            await example.validate_data_consistency()
            
            # 模拟前端工作流程
            await example.simulate_frontend_workflow()
            
            print("\n🎉 示例运行完成!")
            
        except Exception as e:
            print(f"❌ 运行出错: {e}")

def test_resource_mapping():
    """测试资源名称映射功能"""
    print("\n🧪 测试资源名称映射...")
    
    # 导入映射函数
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    try:
        from routers.data_analysis_modal import map_resource_to_source_type
        
        test_cases = [
            ("学术论文", "paper"),
            ("法律条文", "law"),
            ("政策文件", "policy"),
            ("研究报告", "report"),
            ("技术文档", "paper"),
            ("图书资料", "book"),
            ("未知资源", "paper")  # 默认类型
        ]
        
        print("测试用例:")
        for resource_name, expected_type in test_cases:
            actual_type = map_resource_to_source_type(resource_name)
            status = "✅" if actual_type == expected_type else "❌"
            print(f"   {status} '{resource_name}' → {actual_type} (期望: {expected_type})")
        
    except ImportError as e:
        print(f"❌ 无法导入映射函数: {e}")

if __name__ == "__main__":
    # 测试映射函数
    test_resource_mapping()
    
    # 运行异步示例
    asyncio.run(main())
