from beanie import Document
from pydantic import Field
from typing import Optional

class Trash(Document):
    title: str
    timestamp: str
    reason: str
    type: str = Field(default="trash")

    class Settings:
        name = "trash" 