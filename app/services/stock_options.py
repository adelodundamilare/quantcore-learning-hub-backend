from sqlalchemy.orm import Session
from typing import List
from app.crud.stock_options import stock_category as crud_stock_category
from app.schemas.stock_options import StockCategorySchema

class StockOptionsService:
    def get_all_categories(self, db: Session) -> List[StockCategorySchema]:
        categories = crud_stock_category.get_multi(db)
        return [StockCategorySchema.model_validate(category) for category in categories]

    def get_category_by_id(self, db: Session, category_id: int) -> StockCategorySchema:
        category = crud_stock_category.get(db, id=category_id)
        return StockCategorySchema.model_validate(category)

stock_options_service = StockOptionsService()
