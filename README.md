# 数据工厂后端服务

## 概述

数据工厂后端服务是一个基于 FastAPI 的现代化数据处理和分析平台，提供完整的数据采集、处理、分析和展示功能。

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MongoDB 4.4+
- 8GB+ RAM (推荐)

### 安装依赖

```bash
cd server
pip install -r requirements.txt
```

### 配置环境

1. 复制环境配置文件：

```bash
cp .env
```

2. 编辑 `.env` 文件，配置必要参数：

```env
# 数据分析基础目录(根据实际情况修改)
BASE_PDF_DIR=D:\pdf

# 数据库配置
MONGO_USER=user
MONGO_PASSWORD=password
MONGO_HOST=localhost
MONGO_PORT=27017
DB_NAME=data_factory


# Ollama 本地大模型配置(根据实际修改)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b

# DeepSeek API配置(可选)(需配置密钥)
DEEPSEEK_API_KEY=your_api_key_here
```

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8001` 启动。

## 📁 项目结构

```
server/
├── main.py                 # 应用入口
├── config.py              # 配置管理
├── requirements.txt       # 依赖包
├── .env                   # 环境配置
├── .env.example          # 环境配置模板
├── clear/                # 数据库清理工具
│   ├── clear_database.py
│   └── clear_database_force.py
├── docs/                 # 文档
│   ├── stop_crawling_api.md
│   └── environment_configuration.md
├── examples/             # 示例代码
│   └── stop_crawling_demo.py
├── models/              # 数据模型
│   ├── paper.py
│   ├── resource.py
│   └── ...
├── routers/             # API路由
│   ├── data_factory_api.py
│   ├── data_analysis_modal.py
│   ├── analysis.py
│   └── ...
├── services/            # 业务服务
│   ├── resource_service.py
│   ├── database.py
│   ├── directory_monitor_service.py
│   └── ...
└── utils/               # 工具函数
    └── error_handlers.py
```

## 🔧 核心功能

### 1. 数据采集 (Data Collection)

- **自动目录扫描**: 监控指定目录的 PDF 文件变化
- **智能文件分类**: 使用 AI 模型自动分类文档
- **实时数据统计**: 提供数据源统计信息

**主要接口**:

- `GET /api/collection/statistics` - 获取数据源统计
- `POST /api/collection/crawl` - 开始数据分析
- `POST /api/collection/crawl/stop` - 停止数据爬取
- `GET /api/collection/results` - 获取分析结果

### 2. 数据处理 (Data Processing)

- **批量文档处理**: 支持 PDF、JSON 等多种格式
- **内容提取**: 提取文档元数据和内容
- **质量评估**: 自动评估文档质量

**主要接口**:

- `GET /api/processing/statistics` - 获取处理统计
- `GET /api/processing/papers/valid` - 获取有效论文
- `GET /api/processing/formulas` - 获取公式数据

### 3. 数据分析 (Data Analysis)

- **关键词提取**: 智能提取文档关键词
- **文本分类**: 多类别文档分类
- **性能指标**: 提供准确率、召回率等指标

**主要接口**:

- `POST /api/analysis/keyword-extraction/start` - 开始关键词提取
- `POST /api/analysis/classification/start` - 开始智能分类
- `GET /api/analysis/category-stats/{task_id}` - 获取分类统计

### 4. 任务管理 (Task Management)

- **异步任务**: 支持长时间运行的分析任务
- **进度跟踪**: 实时任务进度监控
- **状态管理**: 完整的任务生命周期管理

## 🗄️ 数据库设计

### 核心集合

- **tasks**: 任务管理
- **data_sources**: 数据源信息
- **analysis_results**: 分析结果
- **papers**: 论文数据

### 数据库操作

```python
# 初始化数据库
from services.database import init_db
await init_db()

# 清理数据库
python clear/clear_database.py
```

## 🔌 API 文档

### 认证

目前服务不需要认证，所有接口都是公开的。

### 响应格式

所有 API 响应都遵循统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

### 错误处理

- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

### 添加新的服务

1. 在 `services/` 目录下创建服务文件
2. 实现业务逻辑类
3. 在需要的地方导入使用

### 数据库模型

使用 Beanie ODM 定义数据模型：

```python
from beanie import Document
from pydantic import Field

class MyModel(Document):
    name: str = Field(..., description="名称")

    class Settings:
        name = "my_collection"
```

## 🔧 配置说明

### 环境变量

| 变量名           | 说明         | 默认值    |
| ---------------- | ------------ | --------- |
| BASE_PDF_DIR     | PDF 扫描目录 | -         |
| MONGO_HOST       | MongoDB 主机 | localhost |
| MONGO_PORT       | MongoDB 端口 | 27017     |
| DEEPSEEK_API_KEY | AI API 密钥  | -         |
| SERVER_PORT      | 服务端口     | 8001      |

### 日志配置

日志级别可通过 `LOG_LEVEL` 环境变量配置：

- DEBUG: 详细调试信息
- INFO: 一般信息 (默认)
- WARNING: 警告信息
- ERROR: 错误信息

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_stop_crawling.py -v
```

### 手动测试

```bash
# 测试API接口
curl -X GET http://localhost:8001/api/collection/statistics

# 停止爬取任务
curl -X POST http://localhost:8001/api/collection/crawl/stop

# 开始数据分析
curl -X POST http://localhost:8001/api/collection/crawl \
  -H "Content-Type: application/json" \
  -d '{"sourceType": "academic", "limit": 100}'
```

## 📊 监控和日志

### 日志文件

日志输出到控制台，包含：

- 请求日志
- 错误日志
- 业务操作日志

### 性能监控

- 任务执行时间
- 数据库查询性能
- 内存使用情况

## 🚨 故障排除

### 常见问题

1. **数据库连接失败**

   - 检查 MongoDB 是否运行
   - 验证连接配置

2. **目录访问权限**

   - 确保应用有读写权限
   - 检查目录路径是否正确

3. **API 调用失败**
   - 检查 DeepSeek API 密钥
   - 验证网络连接

### 调试模式

设置环境变量启用调试：

```bash
export LOG_LEVEL=DEBUG
python main.py
```

## 🚀 部署

### Docker 部署

1. 构建镜像：

```bash
docker build -t data-factory-server .
```

2. 运行容器：

```bash
docker run -d \
  --name data-factory-server \
  -p 8001:8001 \
  -e BASE_PDF_DIR=/data/pdf \
  -v /host/pdf:/data/pdf \
  data-factory-server
```

### 使用 Docker Compose

```bash
# 启动所有服务（包括MongoDB数据库连接）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```
