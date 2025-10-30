from pydantic import BaseModel, ConfigDict
from typing import List

class StockCategoryItemSchema(BaseModel):
    id: int
    symbol: str

    model_config = ConfigDict(from_attributes=True)

class StockCategorySchema(BaseModel):
    id: int
    name: str
    items: List[StockCategoryItemSchema] = []

    model_config = ConfigDict(from_attributes=True)
