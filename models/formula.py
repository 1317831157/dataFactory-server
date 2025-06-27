from beanie import Document
from pydantic import Field
from typing import Optional

class Formula(Document):
    title: str
    paperTitle: str
    image: Optional[str]
    timestamp: str
    type: str = Field(default="formula")

    class Settings:
        name = "formulas" 