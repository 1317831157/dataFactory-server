"""
数据分析模态框API测试
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestDataAnalysisModalAPI:
    """数据分析模态框API测试类"""
    
    def test_health_check(self):
        """测试健康检查接口"""
        response = client.get("/api/analysis/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "healthy"
    
    def test_get_data_sources(self):
        """测试获取数据源列表"""
        response = client.get("/api/analysis/data-sources")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        # 验证数据源结构
        source = data["data"][0]
        required_fields = ["id", "name", "type", "description", "count", "lastUpdated", "categories"]
        for field in required_fields:
            assert field in source

        # 验证数据源是否来自自动分析结果
        print(f"Data sources found: {len(data['data'])}")
        for src in data["data"]:
            print(f"- {src['name']} ({src['type']}): {src['count']} items")
            # 检查是否是自动分析结果（ID以auto-开头）
            if src["id"].startswith("auto-"):
                print(f"  ✓ Source from auto analysis: {src['id']}")
            else:
                print(f"  ✓ Source from default data: {src['id']}")

    def test_data_source_mapping_integration(self):
        """测试数据源映射集成"""
        # 获取数据源列表
        sources_response = client.get("/api/analysis/data-sources")
        assert sources_response.status_code == 200
        sources_data = sources_response.json()

        # 获取数据源分类映射
        mapping_response = client.get("/api/analysis/source-category-mapping")
        assert mapping_response.status_code == 200
        mapping_data = mapping_response.json()

        # 验证数据源类型在映射中存在
        for source in sources_data["data"]:
            source_type = source["type"]
            assert source_type in mapping_data["data"], f"Source type {source_type} not found in mapping"

            # 验证数据源的categories与映射一致
            expected_categories = mapping_data["data"][source_type]
            assert source["categories"] == expected_categories, f"Categories mismatch for {source_type}"
    
    def test_get_source_category_mapping(self):
        """测试获取数据源分类映射"""
        response = client.get("/api/analysis/source-category-mapping")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], dict)
        
        # 验证映射结构
        mapping = data["data"]
        expected_sources = ["law", "paper", "report", "policy", "book"]
        for source in expected_sources:
            assert source in mapping
            assert isinstance(mapping[source], list)
    
    def test_get_categories(self):
        """测试获取分类类别"""
        response = client.get("/api/analysis/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        
        # 验证类别结构
        category = data["data"][0]
        required_fields = ["id", "name", "type", "description", "icon", "color"]
        for field in required_fields:
            assert field in category
    
    def test_get_available_models(self):
        """测试获取可用模型"""
        response = client.get("/api/analysis/models")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        
        # 验证模型结构
        model = data["data"][0]
        required_fields = ["id", "name", "type", "version", "description", "accuracy", "trainedOn", "supportedCategories", "parameters"]
        for field in required_fields:
            assert field in model
    
    def test_start_keyword_extraction(self):
        """测试开始关键词提取"""
        request_data = {
            "sourceType": "paper",
            "sampleSize": 100
        }
        response = client.post("/api/analysis/keyword-extraction/start", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "taskId" in data["data"]
        
        return data["data"]["taskId"]
    
    def test_get_keyword_extraction_progress(self):
        """测试获取关键词提取进度"""
        # 先启动一个任务
        task_id = self.test_start_keyword_extraction()
        
        # 获取进度
        response = client.get(f"/api/analysis/keyword-extraction/progress/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证进度结构
        progress = data["data"]
        required_fields = ["keywords", "totalKeywords", "extractedCount", "progress", "confidence"]
        for field in required_fields:
            assert field in progress
    
    def test_start_preprocessing(self):
        """测试开始数据预处理"""
        request_data = {
            "sourceType": "paper",
            "steps": ["数据清洗", "格式标准化", "特征提取"],
            "parameters": {"cleaningThreshold": 0.8}
        }
        response = client.post("/api/analysis/preprocessing/start", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "taskId" in data["data"]
        
        return data["data"]["taskId"]
    
    def test_get_preprocessing_progress(self):
        """测试获取预处理进度"""
        # 先启动一个任务
        task_id = self.test_start_preprocessing()
        
        # 获取进度
        response = client.get(f"/api/analysis/preprocessing/progress/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证进度结构
        progress = data["data"]
        required_fields = ["taskId", "status", "progress", "steps", "totalSteps", "completedSteps", "startTime"]
        for field in required_fields:
            assert field in progress
    
    def test_start_classification(self):
        """测试开始智能分类"""
        request_data = {
            "sourceType": "paper",
            "parameters": {"batchSize": 32, "threshold": 0.8}
        }
        response = client.post("/api/analysis/classification/start", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "taskId" in data["data"]
        
        return data["data"]["taskId"]
    
    def test_get_classification_progress(self):
        """测试获取分类进度"""
        # 先启动一个任务
        task_id = self.test_start_classification()
        
        # 获取进度
        response = client.get(f"/api/analysis/classification/progress/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证进度结构
        progress = data["data"]
        required_fields = ["taskId", "sourceType", "status", "progress", "startTime", "modelType", "parameters"]
        for field in required_fields:
            assert field in progress
    
    def test_get_real_time_analysis_status(self):
        """测试获取实时分析状态"""
        response = client.get("/api/analysis/status/realtime")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证状态结构
        status = data["data"]
        required_fields = ["isRunning", "progress", "processedSamples", "totalSamples", "currentStep", "queueLength"]
        for field in required_fields:
            assert field in status
    
    def test_get_analysis_history(self):
        """测试获取分析历史"""
        response = client.get("/api/analysis/history?page=1&pageSize=10")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证历史结构
        history = data["data"]
        required_fields = ["data", "total", "page", "pageSize"]
        for field in required_fields:
            assert field in history
    
    def test_get_analysis_config(self):
        """测试获取分析配置"""
        response = client.get("/api/analysis/config")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证配置结构
        config = data["data"]
        required_fields = ["defaultModel", "batchSize", "threshold", "enableAutoPreprocessing", "maxConcurrentTasks"]
        for field in required_fields:
            assert field in config
    
    def test_update_analysis_config(self):
        """测试更新分析配置"""
        config_data = {
            "defaultModel": "roberta-large-001",
            "batchSize": 64,
            "threshold": 0.9
        }
        response = client.put("/api/analysis/config", json=config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["success"] is True
    
    def test_get_data_flow_status(self):
        """测试获取数据流状态"""
        response = client.get("/api/analysis/data-flow/status")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        # 验证数据流状态结构
        flow_status = data["data"]
        required_fields = ["currentStep", "steps"]
        for field in required_fields:
            assert field in flow_status
        
        # 验证步骤结构
        assert isinstance(flow_status["steps"], list)
        if flow_status["steps"]:
            step = flow_status["steps"][0]
            step_fields = ["name", "status", "progress"]
            for field in step_fields:
                assert field in step
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试不存在的任务ID
        response = client.get("/api/analysis/keyword-extraction/progress/nonexistent-task")
        assert response.status_code == 404
        
        # 测试不存在的数据源
        response = client.get("/api/analysis/data-sources/nonexistent-source")
        assert response.status_code == 404
        
        # 测试不存在的分类类别
        response = client.get("/api/analysis/categories/nonexistent-category")
        assert response.status_code == 404

# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    test_instance = TestDataAnalysisModalAPI()
    
    print("开始运行数据分析模态框API测试...")
    
    try:
        test_instance.test_health_check()
        print("✅ 健康检查测试通过")
        
        test_instance.test_get_data_sources()
        print("✅ 数据源列表测试通过")

        test_instance.test_data_source_mapping_integration()
        print("✅ 数据源映射集成测试通过")
        
        test_instance.test_get_source_category_mapping()
        print("✅ 数据源分类映射测试通过")
        
        test_instance.test_get_categories()
        print("✅ 分类类别测试通过")
        
        test_instance.test_get_available_models()
        print("✅ 可用模型测试通过")
        
        test_instance.test_get_real_time_analysis_status()
        print("✅ 实时分析状态测试通过")
        
        test_instance.test_get_analysis_history()
        print("✅ 分析历史测试通过")
        
        test_instance.test_get_analysis_config()
        print("✅ 分析配置获取测试通过")
        
        test_instance.test_update_analysis_config()
        print("✅ 分析配置更新测试通过")
        
        test_instance.test_get_data_flow_status()
        print("✅ 数据流状态测试通过")
        
        test_instance.test_error_handling()
        print("✅ 错误处理测试通过")
        
        print("\n🎉 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    run_tests()
