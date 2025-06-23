from pydantic import BaseModel
from typing import List, Optional

class ResourceItem(BaseModel):
    """资源项目模型"""
    id: int
    name: str
    count: int
    icon: str
    color: str

class ResourceResponse(BaseModel):
    """资源响应模型"""
    code: int = 200
    message: str = "success"
    data: List[ResourceItem]