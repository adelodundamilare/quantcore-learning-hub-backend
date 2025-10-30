from sqlalchemy.orm import Session
from typing import List
from app.crud.stock_options import stock_category as crud_stock_category
from app.schemas.stock_options import StockCategoryItemExtendedSchema, StockCategorySchema, StockCategoryItemSchema, StockCategoryExtendedSchema
from app.services.polygon import polygon_service

class StockOptionsService:
    async def get_all_categories(self, db: Session) -> List[StockCategorySchema]:
        categories = crud_stock_category.get_multi(db)
        return [StockCategorySchema.model_validate(category) for category in categories]

    async def get_category_by_id(self, db: Session, category_id: int) -> StockCategoryExtendedSchema:
        category = crud_stock_category.get(db, id=category_id)
        if not category:
            return None

        symbols = [item.symbol for item in category.items]
        stock_details_map = await polygon_service.get_multi_stock_details(symbols)

        enriched_items = []
        for item in category.items:
            detail = stock_details_map.get(item.symbol, {})
            enriched_items.append(
                StockCategoryItemExtendedSchema(
                    id=item.id,
                    symbol=item.symbol,
                    current_price=detail.get("price", 0.0),
                    percentage_change_today=detail.get("change_percent", 0.0),
                    current_market_cap=detail.get("market_cap", 0.0)
                )
            )

        category_schema = StockCategoryExtendedSchema.model_validate(category)
        category_schema.items = enriched_items
        return category_schema

stock_options_service = StockOptionsService()
