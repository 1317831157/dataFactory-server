"""
数据展示模态框API测试
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestDataDisplayModalAPI:
    """数据展示模态框API测试类"""

    def test_get_data_source_config(self):
        """测试获取数据源配置"""
        response = client.get("/api/data-sources/config")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        
        config_data = data["data"]
        assert "dataSourceOptions" in config_data
        assert "fieldOptions" in config_data
        assert "subTypeOptions" in config_data
        assert "exportOptions" in config_data
        
        # 验证数据源选项
        assert len(config_data["dataSourceOptions"]) > 0
        for option in config_data["dataSourceOptions"]:
            assert "label" in option
            assert "value" in option

    def test_get_sub_type_options(self):
        """测试获取子类型选项"""
        response = client.get("/api/data-sources/academic_papers/sub-types")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "subTypes" in data["data"]
        assert len(data["data"]["subTypes"]) > 0

    def test_get_sub_type_options_invalid(self):
        """测试获取不存在的数据源子类型选项"""
        response = client.get("/api/data-sources/invalid_source/sub-types")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["subTypes"] == []

    def test_get_data_stats(self):
        """测试获取数据统计信息"""
        response = client.get("/api/data-sources/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        
        stats_data = data["data"]
        assert "metricData" in stats_data
        assert "chartData" in stats_data
        assert "latestData" in stats_data
        
        # 验证指标数据
        assert len(stats_data["metricData"]) > 0
        for metric in stats_data["metricData"]:
            assert "title" in metric
            assert "value" in metric
            assert "trend" in metric
        
        # 验证图表数据
        chart_data = stats_data["chartData"]
        assert "categories" in chart_data
        assert "values" in chart_data
        assert len(chart_data["categories"]) == len(chart_data["values"])

    def test_get_data_stats_with_params(self):
        """测试带参数获取数据统计信息"""
        response = client.get("/api/data-sources/stats?dataSource=academic_papers&fields=计算机科学")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200

    def test_get_metric_data(self):
        """测试获取指标卡数据"""
        response = client.get("/api/data-sources/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "metrics" in data["data"]
        assert len(data["data"]["metrics"]) > 0

    def test_get_chart_data(self):
        """测试获取图表数据"""
        response = client.get("/api/data-sources/chart-data")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        
        chart_data = data["data"]
        assert "categories" in chart_data
        assert "values" in chart_data

    def test_get_chart_data_with_params(self):
        """测试带参数获取图表数据"""
        response = client.get("/api/data-sources/chart-data?dataSource=academic_papers")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200

    def test_get_latest_data(self):
        """测试获取最新数据列表"""
        response = client.get("/api/data-sources/latest?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "data" in data["data"]
        
        latest_data = data["data"]["data"]
        assert len(latest_data) <= 3
        
        for item in latest_data:
            assert "title" in item
            assert "type" in item
            assert "dataSize" in item
            assert "updateDate" in item

    def test_get_latest_data_with_params(self):
        """测试带参数获取最新数据列表"""
        response = client.get("/api/data-sources/latest?limit=2&dataSource=academic_papers&type=学术论文")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200

    def test_update_data(self):
        """测试更新数据"""
        update_params = {
            "dataSource": "academic_papers",
            "selectedSubTypes": ["期刊论文"],
            "dateRange": ["2023-01-01", "2023-12-31"],
            "selectedFields": ["计算机科学", "人工智能"]
        }
        
        response = client.post("/api/data-sources/update", json=update_params)
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        
        result_data = data["data"]
        assert result_data["success"] is True
        assert "taskId" in result_data

    def test_get_update_progress(self):
        """测试获取更新进度"""
        # 先创建一个更新任务
        update_params = {
            "dataSource": "academic_papers",
            "selectedSubTypes": ["期刊论文"],
            "dateRange": ["2023-01-01", "2023-12-31"],
            "selectedFields": ["计算机科学"]
        }
        
        response = client.post("/api/data-sources/update", json=update_params)
        assert response.status_code == 200
        
        task_id = response.json()["data"]["taskId"]
        
        # 获取进度
        progress_response = client.get(f"/api/data-sources/update/progress/{task_id}")
        assert progress_response.status_code == 200
        
        data = progress_response.json()
        assert data["code"] == 200
        assert "data" in data
        
        progress_data = data["data"]
        assert "progress" in progress_data
        assert "status" in progress_data

    def test_get_update_progress_not_found(self):
        """测试获取不存在任务的进度"""
        response = client.get("/api/data-sources/update/progress/invalid_task_id")
        assert response.status_code == 404

    def test_export_data(self):
        """测试导出数据"""
        export_params = {
            "format": "CSV",
            "dataSource": "academic_papers",
            "dateRange": ["2023-01-01", "2023-12-31"],
            "fields": ["title", "type", "dataSize"]
        }
        
        response = client.post("/api/data-sources/export", json=export_params)
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "taskId" in data["data"]

    def test_get_export_status(self):
        """测试获取导出状态"""
        # 先创建一个导出任务
        export_params = {
            "format": "CSV",
            "dataSource": "academic_papers"
        }
        
        response = client.post("/api/data-sources/export", json=export_params)
        assert response.status_code == 200
        
        task_id = response.json()["data"]["taskId"]
        
        # 获取状态
        status_response = client.get(f"/api/data-sources/export/status/{task_id}")
        assert status_response.status_code == 200
        
        data = status_response.json()
        assert data["code"] == 200
        assert "data" in data
        
        status_data = data["data"]
        assert "status" in status_data
        assert "progress" in status_data

    def test_get_export_status_not_found(self):
        """测试获取不存在导出任务的状态"""
        response = client.get("/api/data-sources/export/status/invalid_task_id")
        assert response.status_code == 404

    def test_get_realtime_updates(self):
        """测试获取实时更新"""
        response = client.get("/api/data-sources/realtime")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        
        realtime_data = data["data"]
        assert "lastUpdate" in realtime_data
        assert "hasNewData" in realtime_data
        assert "newDataCount" in realtime_data
        assert "metrics" in realtime_data

    def test_api_error_handling(self):
        """测试API错误处理"""
        # 测试无效的JSON数据
        response = client.post("/api/data-sources/update", data="invalid json")
        assert response.status_code == 422  # Unprocessable Entity

if __name__ == "__main__":
    pytest.main([__file__])
