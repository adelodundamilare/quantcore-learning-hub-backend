from pydantic import BaseModel, ConfigDict
from typing import List

class StockCategoryItemExtendedSchema(BaseModel):
    id: int
    symbol: str
    current_price: float = 0.0
    percentage_change_today: float = 0.0
    current_market_cap: float = 0.0

    model_config = ConfigDict(from_attributes=True)

class StockCategoryItemSchema(BaseModel):
    id: int
    symbol: str

    model_config = ConfigDict(from_attributes=True)

class StockCategorySchema(BaseModel):
    id: int
    name: str
    items: List[StockCategoryItemSchema] = []

    model_config = ConfigDict(from_attributes=True)

class StockCategoryExtendedSchema(BaseModel):
    items: List[StockCategoryItemExtendedSchema] = []

    model_config = ConfigDict(from_attributes=True)
