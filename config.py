"""
配置管理模块
从环境变量和.env文件中读取配置
"""
import os
from typing import List
from pathlib import Path


class Config:
    """配置类，管理所有环境变量和配置项"""
    
    def __init__(self):
        """初始化配置，加载.env文件"""
        self._load_env_file()
    
    def _load_env_file(self):
        """加载.env文件中的环境变量"""
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # 只有当环境变量不存在时才设置
                        if key not in os.environ:
                            os.environ[key] = value
    
    # 数据分析配置
    @property
    def BASE_PDF_DIR(self) -> str:
        """基础PDF目录（第一个目录）"""
        dirs = self.BASE_PDF_DIRS
        return dirs[0] if dirs else ''

    @property
    def BASE_PDF_DIRS(self) -> List[str]:
        """基础PDF目录列表（支持多个目录）"""
        dirs_str = os.environ.get('BASE_PDF_DIR', '')
        return [d.strip() for d in dirs_str.split(',') if d.strip()]

    @property
    def MONITOR_DIRS(self) -> List[str]:
        """监控目录列表（与BASE_PDF_DIRS相同）"""
        return self.BASE_PDF_DIRS
    
    # 数据库配置
    @property
    def MONGO_USER(self) -> str:
        """MongoDB用户名"""
        return os.environ.get('MONGO_USER', 'user')
    
    @property
    def MONGO_PASSWORD(self) -> str:
        """MongoDB密码"""
        return os.environ.get('MONGO_PASSWORD', 'password')
    
    @property
    def MONGO_HOST(self) -> str:
        """MongoDB主机"""
        return os.environ.get('MONGO_HOST', 'localhost')
    
    @property
    def MONGO_PORT(self) -> int:
        """MongoDB端口"""
        return int(os.environ.get('MONGO_PORT', '27017'))
    
    @property
    def DB_NAME(self) -> str:
        """数据库名称"""
        return os.environ.get('DB_NAME', 'data_factory')
    
    @property
    def DATABASE_URI(self) -> str:
        """数据库连接字符串"""
        return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@{self.MONGO_HOST}:{self.MONGO_PORT}"
    
    # API配置
    @property
    def DEEPSEEK_API_KEY(self) -> str:
        """DeepSeek API密钥"""
        return os.environ.get('DEEPSEEK_API_KEY', '')
    
    # 服务器配置
    @property
    def SERVER_HOST(self) -> str:
        """服务器主机"""
        return os.environ.get('SERVER_HOST', '0.0.0.0')
    
    @property
    def SERVER_PORT(self) -> int:
        """服务器端口"""
        return int(os.environ.get('SERVER_PORT', '8001'))
    
    # 日志配置
    @property
    def LOG_LEVEL(self) -> str:
        """日志级别"""
        return os.environ.get('LOG_LEVEL', 'INFO')
    
    # 扫描配置
    @property
    def MAX_SCAN_DEPTH(self) -> int:
        """最大扫描深度"""
        return int(os.environ.get('MAX_SCAN_DEPTH', '2'))
    
    @property
    def MAX_CONCURRENT_PROCESSES(self) -> int:
        """最大并发进程数"""
        return int(os.environ.get('MAX_CONCURRENT_PROCESSES', '16'))
    
    # 缓存配置
    @property
    def CACHE_DURATION_HOURS(self) -> int:
        """缓存持续时间（小时）"""
        return int(os.environ.get('CACHE_DURATION_HOURS', '1'))


# 创建全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config


# 为了向后兼容，提供一些常用的配置变量
BASE_PDF_DIR = config.BASE_PDF_DIR
BASE_PDF_DIRS = config.BASE_PDF_DIRS
MONITOR_DIRS = config.MONITOR_DIRS
DATABASE_URI = config.DATABASE_URI
DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY
