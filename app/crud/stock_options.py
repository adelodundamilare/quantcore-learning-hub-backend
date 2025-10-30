from app.crud.base import CRUDBase
from app.models.stock_options import StockCategory, StockCategoryItem
from app.schemas.stock_options import StockCategorySchema, StockCategoryItemSchema
from pydantic import BaseModel

class CRUDStockCategory(CRUDBase[StockCategory, StockCategorySchema, BaseModel]):
    pass

class CRUDStockCategoryItem(CRUDBase[StockCategoryItem, StockCategoryItemSchema, BaseModel]):
    pass

stock_category = CRUDStockCategory(StockCategory)
stock_category_item = CRUDStockCategoryItem(StockCategoryItem)
