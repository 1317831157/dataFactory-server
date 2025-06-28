# 数据展示模态框 API 文档

## 概述

数据展示模态框 API 为 DataDisplayModal 组件提供完整的后端支持，包括数据源配置、统计信息获取、数据更新和导出等功能。该API使用 `get_auto_analysis_result` 作为主要数据源，确保展示的是真实的分析数据。

## 基础信息

- **基础 URL**: `http://localhost:8000/api/data-sources`
- **认证方式**: 无需认证（开发环境）
- **响应格式**: JSON

## 通用响应格式

```json
{
  "code": 200,
  "message": "Success",
  "data": {}
}
```

## API 接口列表

### 1. 数据源配置

#### 1.1 获取数据源配置信息

- **URL**: `GET /config`
- **描述**: 获取所有数据源配置信息，包括数据源选项、研究领域选项、子类型选项和导出格式选项
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "dataSourceOptions": [
      {"label": "📚 学术论文", "value": "academic_papers"},
      {"label": "📊 调查报告", "value": "survey_reports"}
    ],
    "fieldOptions": ["计算机科学", "人工智能", "数据科学"],
    "subTypeOptions": {
      "academic_papers": ["期刊论文", "会议论文", "学位论文", "预印本"]
    },
    "exportOptions": ["CSV", "Excel", "PDF", "JSON"]
  }
}
```

#### 1.2 获取子类型选项

- **URL**: `GET /{data_source}/sub-types`
- **参数**:
  - `data_source`: 数据源类型（如：academic_papers）
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "subTypes": ["期刊论文", "会议论文", "学位论文", "预印本"]
  }
}
```

### 2. 数据统计

#### 2.1 获取数据统计信息

- **URL**: `GET /stats`
- **描述**: 获取完整的数据统计信息，使用 `get_auto_analysis_result` 作为数据源
- **查询参数**:
  - `dataSource` (可选): 数据源类型
  - `dateRange` (可选): 日期范围
  - `fields` (可选): 研究领域
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "metricData": [
      {"title": "文献总量", "value": "52,489", "trend": "+12.5%"},
      {"title": "图文数据集", "value": "15,932", "trend": "+8.3%"}
    ],
    "chartData": {
      "categories": ["学术论文", "调查报告", "专业书籍"],
      "values": [25000, 12000, 8000]
    },
    "latestData": [
      {
        "title": "人工智能发展白皮书",
        "type": "调查报告",
        "dataSize": 1250,
        "updateDate": "2024-01-15"
      }
    ]
  }
}
```

#### 2.2 获取指标卡数据

- **URL**: `GET /metrics`
- **描述**: 单独获取指标卡数据

#### 2.3 获取图表数据

- **URL**: `GET /chart-data`
- **描述**: 获取柱状图数据
- **查询参数**:
  - `dataSource` (可选): 数据源类型
  - `dateRange` (可选): 日期范围

#### 2.4 获取最新数据列表

- **URL**: `GET /latest`
- **描述**: 获取最新数据项列表
- **查询参数**:
  - `limit` (可选): 返回数量限制，默认5
  - `dataSource` (可选): 数据源类型
  - `type` (可选): 数据类型

### 3. 数据更新

#### 3.1 更新数据

- **URL**: `POST /update`
- **描述**: 根据选择的参数重新获取和分析数据
- **请求体**:

```json
{
  "dataSource": "academic_papers",
  "selectedSubTypes": ["期刊论文"],
  "dateRange": ["2023-01-01", "2023-12-31"],
  "selectedFields": ["计算机科学", "人工智能"]
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "数据更新请求已提交",
  "data": {
    "success": true,
    "message": "数据更新中，请稍后查看结果",
    "taskId": "task_20240115_120000_abc12345"
  }
}
```

#### 3.2 获取更新进度

- **URL**: `GET /update/progress/{task_id}`
- **参数**:
  - `task_id`: 更新任务ID
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "progress": 75,
    "status": "running",
    "message": "数据更新进度: 75%"
  }
}
```

### 4. 数据导出

#### 4.1 导出数据

- **URL**: `POST /export`
- **描述**: 根据指定格式和参数导出数据
- **请求体**:

```json
{
  "format": "CSV",
  "dataSource": "academic_papers",
  "dateRange": ["2023-01-01", "2023-12-31"],
  "fields": ["title", "type", "dataSize"]
}
```

#### 4.2 获取导出状态

- **URL**: `GET /export/status/{task_id}`
- **参数**:
  - `task_id`: 导出任务ID
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "status": "completed",
    "progress": 100,
    "downloadUrl": "/api/downloads/task_20240115_120000_abc12345.csv"
  }
}
```

### 5. 实时数据

#### 5.1 获取实时更新

- **URL**: `GET /realtime`
- **描述**: 获取实时数据更新信息
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "lastUpdate": "2024-01-15T12:00:00Z",
    "hasNewData": false,
    "newDataCount": 0,
    "metrics": [
      {"title": "文献总量", "value": "52,489", "trend": "+12.5%"}
    ]
  }
}
```

## 数据集成说明

### 自动分析结果集成

该API已经集成了 `get_auto_analysis_result` 函数，实现了真实数据的动态获取：

#### 集成方式

1. **数据统计接口** (`/stats`) 优先使用自动分析结果
2. **智能映射** 将资源名称自动映射到合适的数据类型
3. **降级处理** 当自动分析数据不可用时，使用默认数据

#### 数据流程

```
get_auto_analysis_result()
    ↓
ResourceItem[] (资源列表)
    ↓
map_resource_to_data_type() (类型映射)
    ↓
统计数据生成
    ↓
前端 DataDisplayModal 组件
```

#### 映射逻辑

资源名称到数据类型的映射规则：
- 包含"论文"、"学术"、"研究" → "学术论文"
- 包含"报告"、"调研"、"分析" → "调查报告"
- 包含"书籍"、"教材"、"专著" → "专业书籍"
- 包含"政策"、"规定"、"制度" → "政策文件"
- 包含"法规"、"标准"、"规范" → "法规标准"
- 其他情况默认为 → "学术论文"

## 任务管理

### 任务状态

- `pending`: 等待中
- `running`: 运行中
- `completed`: 已完成
- `failed`: 失败

### 任务ID格式

任务ID格式：`task_{YYYYMMDD_HHMMSS}_{8位随机字符}`

示例：`task_20240115_120000_abc12345`

## 错误处理

所有接口都包含统一的错误处理机制：

- **500 Internal Server Error**: 服务器内部错误
- **404 Not Found**: 资源不存在
- **400 Bad Request**: 请求参数错误
- **422 Unprocessable Entity**: 请求数据格式错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

## 使用示例

### Python 客户端示例

```python
import requests

# 获取数据统计
response = requests.get("http://localhost:8000/api/data-sources/stats")
data = response.json()

# 更新数据
update_params = {
    "dataSource": "academic_papers",
    "selectedSubTypes": ["期刊论文"],
    "dateRange": ["2023-01-01", "2023-12-31"],
    "selectedFields": ["计算机科学"]
}
response = requests.post("http://localhost:8000/api/data-sources/update", json=update_params)
task_id = response.json()["data"]["taskId"]

# 检查进度
progress_response = requests.get(f"http://localhost:8000/api/data-sources/update/progress/{task_id}")
progress = progress_response.json()["data"]["progress"]
```

### JavaScript 客户端示例

```javascript
// 获取数据配置
const config = await fetch('/api/data-sources/config').then(r => r.json())

// 导出数据
const exportParams = {
  format: 'CSV',
  dataSource: 'academic_papers'
}
const exportResponse = await fetch('/api/data-sources/export', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(exportParams)
})
const { taskId } = await exportResponse.json().data
```
