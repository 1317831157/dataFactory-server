from beanie import Document
from pydantic import Field
from typing import List, Optional

class Paper(Document):
    title: str
    source: str
    authors: List[str] = Field(default_factory=list)
    timestamp: str
    wordCount: int
    imageCount: int
    formulaCount: int
    abstract: str
    file_path:Optional[str] = None
    topics: List[str]
    image: Optional[str]
    type: str = Field(default="valid")

    class Settings:
        name = "papers" 