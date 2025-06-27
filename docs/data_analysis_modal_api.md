# 数据分析模态框 API 文档

## 概述

数据分析模态框 API 提供了完整的数据分析功能，支持从数据源选择到智能分类的全流程操作。

## 基础信息

- **基础 URL**: `http://localhost:8001/api/analysis`
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

### 1. 数据源管理

#### 1.1 获取数据源列表

- **URL**: `GET /data-sources`
- **描述**: 获取所有可用的数据源，优先使用 `get_auto_analysis_result` 的真实数据
- **数据来源**:
  1. 首先尝试从 `get_auto_analysis_result` 获取自动分析的资源数据
  2. 如果自动分析数据不可用，则使用默认的数据源配置
- **资源映射规则**:
  - 包含"文档"、"论文"、"学术"、"研究" → `paper`
  - 包含"法律"、"法规"、"条文" → `law`
  - 包含"政策"、"规定"、"制度" → `policy`
  - 包含"报告"、"分析"、"统计" → `report`
  - 包含"图书"、"书籍"、"文献" → `book`
  - 其他情况默认为 → `paper`
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "id": "auto-123",
      "name": "学术论文资源",
      "type": "paper",
      "description": "自动分析发现的学术论文资源资源",
      "count": 2847,
      "lastUpdated": "2024-01-15T10:30:00Z",
      "categories": ["microscope", "satellite"]
    },
    {
      "id": "auto-456",
      "name": "法律文档资源",
      "type": "law",
      "description": "自动分析发现的法律文档资源资源",
      "count": 1523,
      "lastUpdated": "2024-01-15T10:30:00Z",
      "categories": ["robot", "vision"]
    }
  ]
}
```

#### 1.2 获取数据源详情

- **URL**: `GET /data-sources/{source_id}`
- **参数**:
  - `source_id`: 数据源 ID
- **响应**: 单个数据源详细信息

#### 1.3 获取数据源分类映射

- **URL**: `GET /source-category-mapping`
- **描述**: 获取数据源到分类类别的映射关系
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "law": ["robot", "vision"],
    "paper": ["microscope", "satellite"],
    "report": ["agriculture", "landslide"],
    "policy": ["robot", "agriculture"],
    "book": ["star", "satellite"]
  }
}
```

### 2. 分类类别管理

#### 2.1 获取所有分类类别

- **URL**: `GET /categories`
- **描述**: 获取系统支持的所有分类类别

#### 2.2 获取分类类别详情

- **URL**: `GET /categories/{category_id}`
- **参数**:
  - `category_id`: 分类类别 ID

### 3. 关键词提取

#### 3.1 开始关键词提取

- **URL**: `POST /keyword-extraction/start`
- **请求体**:

```json
{
  "sourceType": "paper",
  "sampleSize": 1000
}
```

- **响应**: 返回任务 ID

#### 3.2 获取关键词提取进度

- **URL**: `GET /keyword-extraction/progress/{task_id}`
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "keywords": ["机器学习", "深度学习", "神经网络"],
    "totalKeywords": 100,
    "extractedCount": 50,
    "progress": 50,
    "confidence": 0.85
  }
}
```

#### 3.3 获取提取结果

- **URL**: `GET /keyword-extraction/result/{task_id}`
- **描述**: 获取完成的关键词提取结果

### 4. 数据预处理

#### 4.1 开始数据预处理

- **URL**: `POST /preprocessing/start`
- **请求体**:

```json
{
  "sourceType": "paper",
  "steps": ["数据清洗", "格式标准化", "特征提取"],
  "parameters": {
    "cleaningThreshold": 0.8,
    "standardFormat": "json",
    "featureCount": 100
  }
}
```

#### 4.2 获取预处理进度

- **URL**: `GET /preprocessing/progress/{task_id}`
- **响应**: 包含步骤状态和整体进度

#### 4.3 获取预处理结果

- **URL**: `GET /preprocessing/result/{task_id}`
- **描述**: 获取完成的预处理结果

### 5. 智能分类

#### 5.1 获取可用模型

- **URL**: `GET /models`
- **描述**: 获取所有可用的分类模型

#### 5.2 开始智能分类

- **URL**: `POST /classification/start`
- **请求体**:

```json
{
  "sourceType": "paper",
  "modelId": "bert-base-001",
  "parameters": {
    "batchSize": 32,
    "threshold": 0.8,
    "enablePreprocessing": false
  }
}
```

#### 5.3 获取分类进度

- **URL**: `GET /classification/progress/{task_id}`
- **响应**: 包含分类进度和实时指标

#### 5.4 获取分类结果

- **URL**: `GET /classification/result/{task_id}`
- **描述**: 获取完整的分类结果

#### 5.5 获取分类指标

- **URL**: `GET /classification/metrics/{task_id}`
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "accuracy": 0.95,
    "precision": 0.92,
    "recall": 0.88,
    "f1Score": 0.9,
    "support": 1000,
    "confusionMatrix": [
      [85, 5, 3],
      [3, 88, 2],
      [2, 1, 90]
    ],
    "classificationReport": {
      "robot": {
        "precision": 0.95,
        "recall": 0.85,
        "f1Score": 0.9,
        "support": 100
      }
    }
  }
}
```

### 6. 混淆矩阵

#### 6.1 获取混淆矩阵数据

- **URL**: `GET /confusion-matrix/{task_id}`
- **描述**: 获取混淆矩阵原始数据

#### 6.2 生成混淆矩阵图表配置

- **URL**: `GET /confusion-matrix/chart/{task_id}`
- **描述**: 获取 ECharts 图表配置

### 7. 分类结果统计

#### 7.1 获取分类结果统计

- **URL**: `GET /category-stats/{task_id}`
- **响应示例**:

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "robot": {
      "count": 85,
      "confidence": 0.95,
      "percentage": 12.1,
      "samples": 100
    },
    "agriculture": {
      "count": 88,
      "confidence": 0.92,
      "percentage": 12.6,
      "samples": 100
    }
  }
}
```

#### 7.2 更新分类结果统计

- **URL**: `POST /category-stats/update`
- **请求体**:

```json
{
  "taskId": "task_12345",
  "sourceType": "paper",
  "categories": ["robot", "vision"]
}
```

### 8. 实时分析状态

#### 8.1 获取实时分析状态

- **URL**: `GET /status/realtime`
- **描述**: 获取当前分析任务的运行状态

#### 8.2 停止分析任务

- **URL**: `POST /tasks/{task_id}/stop`
- **描述**: 停止指定的分析任务

#### 8.3 重启分析任务

- **URL**: `POST /tasks/{task_id}/restart`
- **描述**: 重启指定的分析任务

### 9. 历史记录和报告

#### 9.1 获取分析历史

- **URL**: `GET /history`
- **参数**:
  - `page`: 页码（默认 1）
  - `pageSize`: 每页大小（默认 10）
  - `sourceType`: 数据源类型（可选）
  - `status`: 任务状态（可选）

#### 9.2 生成分析报告

- **URL**: `POST /reports/generate/{task_id}`
- **描述**: 为指定任务生成分析报告

#### 9.3 获取分析报告

- **URL**: `GET /reports/{report_id}`
- **描述**: 获取生成的分析报告

### 10. 导出功能

#### 10.1 导出分析结果

- **URL**: `POST /export`
- **请求体**:

```json
{
  "taskId": "task_12345",
  "format": "excel",
  "includeMetrics": true,
  "includeCategoryStats": true,
  "includeConfusionMatrix": true,
  "includeRawData": false
}
```

- **响应**: 文件下载

#### 10.2 获取导出任务状态

- **URL**: `GET /export/status/{task_id}`
- **描述**: 获取导出任务的状态

### 11. 配置管理

#### 11.1 获取分析配置

- **URL**: `GET /config`
- **描述**: 获取当前的分析配置

#### 11.2 更新分析配置

- **URL**: `PUT /config`
- **请求体**:

```json
{
  "defaultModel": "roberta-large-001",
  "batchSize": 64,
  "threshold": 0.9,
  "enableAutoPreprocessing": true,
  "maxConcurrentTasks": 5
}
```

### 12. 数据流动画

#### 12.1 获取数据流状态

- **URL**: `GET /data-flow/status`
- **描述**: 获取数据流动画的当前状态

#### 12.2 更新数据流状态

- **URL**: `POST /data-flow/update`
- **请求体**:

```json
{
  "step": "关键词提取"
}
```

### 13. 健康检查

#### 13.1 健康检查

- **URL**: `GET /health`
- **描述**: 检查 API 服务的健康状态

## 错误码说明

- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

## 使用示例

### 完整的数据分析流程

```javascript
// 1. 获取数据源映射
const mapping = await fetch("/api/analysis/source-category-mapping").then((r) =>
  r.json()
)

// 2. 开始关键词提取
const keywordTask = await fetch("/api/analysis/keyword-extraction/start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ sourceType: "paper", sampleSize: 1000 }),
}).then((r) => r.json())

// 3. 轮询关键词提取进度
const pollProgress = async (taskId) => {
  const progress = await fetch(
    `/api/analysis/keyword-extraction/progress/${taskId}`
  ).then((r) => r.json())
  if (progress.data.progress < 100) {
    setTimeout(() => pollProgress(taskId), 500)
  } else {
    // 继续下一步
    startPreprocessing()
  }
}

// 4. 开始预处理
const startPreprocessing = async () => {
  const preprocessTask = await fetch("/api/analysis/preprocessing/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sourceType: "paper",
      steps: ["数据清洗", "格式标准化", "特征提取"],
    }),
  }).then((r) => r.json())

  // 轮询预处理进度...
}

// 5. 开始分类
const startClassification = async () => {
  const classificationTask = await fetch("/api/analysis/classification/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sourceType: "paper",
      parameters: { batchSize: 32, threshold: 0.8 },
    }),
  }).then((r) => r.json())

  // 轮询分类进度...
}
```

## 数据集成说明

### 自动分析结果集成

数据分析模态框 API 已经集成了 `get_auto_analysis_result` 函数，实现了真实数据的动态获取：

#### 集成方式

1. **数据源接口** (`/data-sources`) 优先使用自动分析结果
2. **智能映射** 将资源名称自动映射到合适的数据源类型
3. **降级处理** 当自动分析数据不可用时，使用默认配置

#### 数据流程

```
get_auto_analysis_result()
    ↓
ResourceItem[] (资源列表)
    ↓
map_resource_to_source_type() (类型映射)
    ↓
DataSource[] (数据源格式)
    ↓
前端 DataAnalysisModal 组件
```

#### 映射逻辑

```python
def map_resource_to_source_type(resource_name: str) -> str:
    """将资源名称映射到数据源类型"""
    mapping_rules = {
        "文档": "paper", "论文": "paper", "学术": "paper", "研究": "paper",
        "法律": "law", "法规": "law", "条文": "law",
        "政策": "policy", "规定": "policy", "制度": "policy",
        "报告": "report", "分析": "report", "统计": "report",
        "图书": "book", "书籍": "book", "文献": "book"
    }
    # 检查资源名称包含的关键词，返回对应类型
    # 默认返回 "paper"
```

#### 数据一致性保证

- 自动映射的数据源类型与分类映射表保持一致
- 每个数据源都有对应的分类类别
- 支持实时数据更新和缓存机制

## 注意事项

1. 所有任务都是异步执行的，需要通过轮询获取进度
2. 任务 ID 在服务重启后会失效
3. 大文件导出可能需要较长时间
4. 建议在生产环境中添加认证和限流机制
5. **数据源会优先使用自动分析结果，确保数据的实时性和准确性**
6. **资源名称映射支持中文关键词识别，可根据需要扩展映射规则**
